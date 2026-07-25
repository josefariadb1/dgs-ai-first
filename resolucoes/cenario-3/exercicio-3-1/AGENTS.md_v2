# AGENTS.md — NovaTech Assistant

> Constitution do projeto. Todo agente de IA (Copilot, Claude Code) lê este arquivo antes de gerar qualquer artefato.
> As seções abaixo são preenchidas por papéis diferentes nos exercícios do Cenário 2.

## Project Overview

O **NovaTech Assistant** é um assistente de IA que responde perguntas de atendentes sobre **SLAs, frete e devoluções**, com base na documentação interna da NovaTech (antigo SharePoint/Confluence, ~847 documentos válidos consolidados). É consumido via **bot do Microsoft Teams** e por um **painel web interno** (dashboard de métricas e histórico de queries/feedback).

O sistema tem 4 componentes:

1. **Pipeline de ingestão** (`src/pipeline/`) — extrai, faz chunking, gera embeddings e indexa os documentos.
2. **API do assistente** (`src/functions/`) — Azure Functions que expõem `query`, `feedback` e `health`.
3. **Bot do Teams** (`src/bot/`) — interface conversacional via Bot Framework.
4. **Painel web** (`src/web/`) — React, métricas e histórico.

Regra de negócio não-negociável: o assistente **nunca inventa informação**. Toda resposta cita a fonte (`source_document`). Quando não há resposta na base indexada, isso deve ser dito explicitamente — nunca inferido. Documentos contraditórios são resolvidos priorizando o metadado de vigência mais recente (ver ADR-0003); documentos obsoletos são marcados, não excluídos.

Regras completas de comportamento do assistente e glossário de domínio: seção **Product Rules & Guardrails** (abaixo, a ser preenchida pelo Product Specialist).

## Tech Stack & Architecture

**Stack:**
- **Linguagem:** TypeScript, `strict: true` em todo o repositório (backend, bot e web). Ver `skills/foundation/typescript-conventions.md`.
- **Runtime de API:** Azure Functions v4, HTTP triggers.
- **Validação de I/O:** Zod — todo input e output de função pública deve ser validado com um schema Zod, sem exceção.
- **Busca:** Azure AI Search (retrieval) + Azure OpenAI GPT-4o (embeddings e completions).
- **Frontend:** React (painel web).
- **IaC:** Bicep.
- **Testes:** Vitest.
- **Logging:** pino.

**Arquitetura de dados:** pipeline de ingestão → índice Azure AI Search → query endpoint monta o prompt (chunks recuperados + system prompt + pergunta) → Azure OpenAI GPT-4o → resposta com fonte.

### Gerenciamento de contexto (ADR-0002) — regras obrigatórias

O modelo usado tem janela de 128K tokens, mas o **context budget do projeto é fixo e menor**, para manter custo e latência previsíveis. Todo código que monta prompt para o Azure OpenAI (`src/services/prompt-builder.ts` e qualquer código gerado a partir dele) **DEVE** respeitar:

| Componente | Budget |
|---|---|
| System prompt (`/prompts/system-prompt.md`) | ~4.000 tokens |
| Chunks recuperados | ~8.000 tokens, no máximo **5 chunks** de ~1.500 tokens cada |
| Histórico de conversa | no máximo **3 turnos** anteriores |
| Pergunta do usuário | sem budget fixo, mas contabilizada no total |

Regras derivadas, prescritivas para geração de código:
- `search.ts` **NÃO DEVE** retornar mais de 5 chunks para o `prompt-builder.ts`.
- `prompt-builder.ts` **DEVE** truncar ou rejeitar (com erro explícito, nunca silenciosamente) qualquer chunk que ultrapasse ~1.500 tokens.
- Qualquer código que monte histórico de conversa **DEVE** limitar a 3 turnos — turnos mais antigos são descartados, não resumidos automaticamente sem uma decisão explícita registrada em ADR.
- O `system-prompt.md` é versionado em `/prompts/system-prompt.md`; mudanças que alterem seu tamanho de forma relevante devem ser registradas em `/prompts/prompt-changelog.md`.
- Estourar o budget é bug, não trade-off silencioso: o código deve logar (`pino`, nível `warn`) quando o budget é excedido, nunca truncar sem log.

### Pipeline de resposta — obrigatório, sem atalhos

- Toda resposta a uma pergunta do usuário **DEVE** passar pelas três etapas reais do pipeline: `src/services/search.ts` (retrieval no índice) → `src/services/prompt-builder.ts` (montagem respeitando o budget acima) → `src/services/completion.ts` (chamada ao Azure OpenAI). Um `handler.ts` de query **NÃO DEVE**, em nenhuma hipótese, montar a resposta com dados hardcoded no próprio código-fonte (arrays estáticos, mapa palavra-chave → resposta, `switch`/`if` de perguntas conhecidas) — isso viola a arquitetura definida acima mesmo que o formato de saída (`answer` + `source_document`) esteja correto.
- Se `search.ts`, `prompt-builder.ts` ou `completion.ts` ainda não estiverem implementados no momento em que um endpoint é gerado, o handler **DEVE** falhar de forma explícita (retornar `501` com `error: "not implemented"` e logar em nível `error` via pino) — nunca substituir a chamada real por uma implementação alternativa dentro do handler para "fazer funcionar".

## Coding Standards (Tech Lead)

- **TypeScript:** `strict: true` obrigatório (`tsconfig.json`). Nenhum `any` sem justificativa em comentário. Ver `skills/foundation/typescript-conventions.md`.
- **Validação:** todo endpoint (`src/functions/**/handler.ts`) valida input e output com Zod antes de processar ou retornar. Nunca confiar em tipos do TypeScript como validação em runtime — eles somem no build.
- **Logging:** `pino` (`src/shared/logger.ts`) em todo o backend. `console.log` é **proibido** em código de produção (`src/**`); é aceitável apenas em scripts de desenvolvimento fora de `src/`. Regras obrigatórias, sem exceção:
  - Todo `try/catch` **DEVE** capturar a exceção pelo nome (`catch (err)`) e logar com `logger.error({ err }, "mensagem")` antes de responder ao cliente. `catch {}` ou `catch (_)` que descarta o erro sem logar é proibido.
  - Todo handler **DEVE** logar (`info` para sucesso/not-found, `error` para falha) o resultado de cada request. Um handler sem nenhum log em nenhum dos seus caminhos está fora de conformidade, mesmo que a resposta HTTP esteja correta.
  - Ver `skills/foundation/error-handling.md`.
- **Erros:** erros de negócio (validação falhou, documento não encontrado, serviço upstream indisponível) **DEVEM** ser instâncias de classes definidas em `src/shared/errors.ts` (ex.: `ValidationError`, `NotFoundError`, `UpstreamServiceError`), lançadas com `throw` e capturadas no handler, que traduz para o status HTTP correspondente e loga. Retornar um objeto literal `{ error: string }` direto de dentro de um `catch` genérico, sem passar por uma classe de erro, é proibido.
- **Retry:** toda chamada a um serviço Azure (dentro de `search.ts`, `completion.ts`) **DEVE** usar o helper de retry com exponential backoff em `src/shared/retry.ts` (criar este arquivo na primeira service que fizer uma chamada de rede real, caso ainda não exista). Nenhum código deve chamar `fetch`/SDK do Azure diretamente sem passar por esse helper.
- **Commits:** [Conventional Commits](https://www.conventionalcommits.org/) obrigatório (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`). Mensagens de commit em inglês.
- **Idioma:** código, identificadores e comentários em inglês. Documentos de status, specs (`requirements.md`, `plan.md`) e ADRs em português — ver seção **Project Management Rules** (Delivery Manager) para detalhes de nomenclatura e rastreamento.
- **Branches:** feature branches locais (`feature/<slug>`). Nesta fase não há remoto — "abrir PR" significa criar a branch e escrever a descrição em `docs/pull-requests/PR-NNNN.md` (objetivo, mudanças, checklist de validation gates); a revisão é simulada localmente pelo Tech Lead.

## Product Rules & Guardrails (Product Specialist)
<!-- TODO (Product Specialist — Ex. 2.3) -->

## Testing Standards (QA)
<!-- TODO (QA — Ex. 2.1) -->

## Project Management Rules (Delivery Manager)
<!-- TODO (Delivery Manager — Ex. 2.3) -->

## Build & Deploy

- **Build:** `npm run build` (`tsc -p .`). Falha de tipo = falha de build, sem exceção.
- **Lint:** `npm run lint` (`eslint .`) deve passar sem erros antes de qualquer merge.
- **Testes:** `npm run test` (`vitest run`). Ver seção **Testing Standards** (QA) para padrões de cobertura e estrutura.
- **CI:** `.github/workflows/ci.yml` executa lint, test e build a cada push/PR. Nenhuma etapa pode ser pulada ou marcada `continue-on-error`.
- **CD:** `.github/workflows/cd.yml` cobre deploy para staging/produção. Nesta fase de estruturação, o deploy é **estado narrativo** — não há recursos Azure reais provisionados; os arquivos Bicep em `infra/` documentam a infraestrutura pretendida, mas não são aplicados.
- **Infra como código:** qualquer mudança de infraestrutura é feita via Bicep (`infra/`), nunca manualmente no portal Azure (regra vale mesmo quando a infraestrutura é simulada nesta fase).
