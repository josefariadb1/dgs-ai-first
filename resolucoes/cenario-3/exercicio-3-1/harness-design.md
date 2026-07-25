# Design do Harness — NovaTech Assistant

> Exercício 3.1 (Tech Lead), Tarefa 1. Projeto do harness do assistente pelas 5 camadas, com o que já está implementado, o que falta, e como fechar o gap.

## Contexto

O harness é o que diferencia o protótipo validado no Cenário 1 e estruturado no
Cenário 2 de um sistema de produção. Ele existe porque, mesmo com AGENTS.md,
specs SDD, skills e guardrails formalizados, o time chegou ao Cenário 3 com
**12% de respostas incorretas em staging** e um módulo de código gerado por IA
que **ignorou o próprio AGENTS.md** sem que nada tivesse barrado isso antes do
review. Ou seja: as regras existiam — o que faltava era o mecanismo que as
faz valer, com ou sem atenção humana constante.

Estado herdado (dado no enunciado do cenário):
- Pipeline de ingestão processa 847 documentos, indexados no Azure AI Search.
- Query endpoint recebe pergunta via POST, busca chunks, retorna resposta com
  citação de fonte — mas em **texto livre**: nada garante que a fonte esteja
  sempre presente.
- Bot do Teams em staging, 5 atendentes-piloto.
- AGENTS.md, specs e skills no repositório e em uso pelo Copilot (Cenário 2).
- Guardrails de produto formalizados em DEVE / NÃO DEVE / QUANDO EM DÚVIDA
  (Product Specialist, Cenário 2), mas hoje só existem como **texto no prompt**
  — enforcement puramente probabilístico.
- Testes de integração cobrem ~75% do código.
- Estratégia de contexto definida na [ADR-0002](../../cenario-1/exercicio-1-1/ADR-0002-gerenciamento-contexto.md)
  (Cenário 1): orçamento ~16K tokens/query, retrieval em duas fases, tratamento
  stateless de sessões longas — mas ainda **não instrumentada** (não há medição
  real de tokens nem sinal de quando o orçamento estoura).

---

## As 5 camadas

### 1. Tool orchestration

| | |
|---|---|
| **Já implementado** | Pipeline de ingestão (extração → chunking → embedding → indexação no Azure AI Search) rodando ponta a ponta; query endpoint que encadeia busca de chunks → montagem de prompt → chamada ao Azure OpenAI → retorno com fonte; bot do Teams consumindo o endpoint em staging. |
| **Falta** | Decomposição de perguntas multi-domínio (multi-query) e rerank de candidatos — a ADR-0002 já previu isso como *ponto de extensão*, não como MVP, e o MVP segue com top-K simples. Não há orquestração explícita para o caso de **falha parcial** (ex.: Azure AI Search responde mas Azure OpenAI está degradado — hoje isso provavelmente propaga como erro genérico até o atendente). |
| **Como fechar o gap** | Multi-query/rerank só entram quando os testes de retrieval do QA (Cenário 2) mostrarem perguntas multi-domínio falhando de fato — não antecipar. O que **é** bloqueante agora: um tratamento explícito de falha por etapa (busca falhou vs. geração falhou vs. validação falhou) para que a camada de Observability (§5) consiga distinguir os três casos em vez de logar "erro 500" genérico. |

### 2. Verification loops

| | |
|---|---|
| **Já implementado** | Testes de integração com ~75% de cobertura — mas cobrem **corretude de código** (o endpoint responde, o schema HTTP está certo), não a **qualidade do conteúdo** da resposta gerada. Nenhuma verificação hoje confirma que a fonte citada pelo modelo (`source_document`) é uma fonte que realmente existe. |
| **Falta** | Exatamente o que os 12% de respostas incorretas em staging expõem: nada detecta programaticamente alucinação, documento desatualizado citado como se fosse vigente, ou chunk errado recuperado. A resposta é texto livre — um campo de fonte que o modelo "esquece" de preencher não gera nenhum erro. |
| **Como fechar o gap** | Duas frentes complementares, ambas em andamento no Cenário 3: (a) o Dev está adotando **structured output** (JSON `{ answer, source_document, confidence_score }` validado com Zod) e dois guardrails determinísticos em `response-validator.ts` — presença obrigatória de `source_document` e bloqueio de "carga perigosa pode ser devolvida" (Exercício 3.1 do Desenvolvedor); (b) esta tarefa (Tarefa 2 deste exercício) adiciona uma segunda verificação, independente da anterior: confirmar que o `source_document` citado **existe** na lista de documentos válidos da NovaTech (`POL-001`, `PROC-042`, `PROC-042-v2`, `SLA-2024`, `FAQ-Atendimento`) — isso pega o caso em que o modelo preenche o campo, mas com uma fonte inventada ou mal formatada, que passaria pelo guardrail (a) por estar "presente" mesmo sendo inválida. Detalhe de implementação: ver seção "Tarefa 2" abaixo. |

### 3. Context & memory

| | |
|---|---|
| **Já implementado** | Orçamento de contexto **definido** na ADR-0002 (~4K system prompt + ~8K chunks + histórico controlado), com o princípio de re-retrieval stateless por pergunta para evitar context rot em sessões longas do Teams. |
| **Falta** | A ADR-0002 é uma decisão de arquitetura, não um mecanismo em execução: hoje nada **mede** os tokens de um contexto montado nem corta histórico antes de estourar o orçamento (item 6 da própria ADR). Também não há evidência de que a janela curta de histórico (em vez de acúmulo total da sessão) esteja de fato implementada no bot do Teams. |
| **Como fechar o gap** | Instrumentar a montagem do prompt (`prompt-builder.ts`, por Anexo C) para emitir a contagem de tokens de cada parte (system, chunks, pergunta, histórico) antes de cada chamada ao LLM, e aplicar a regra de corte definida na ADR-0002 (cortar histórico primeiro, depois reduzir chunks) quando o total ultrapassar o orçamento — nunca truncar sem log. Esse número de tokens por parte é, também, o dado que faltava para calibrar o orçamento de 16K citado como "hipótese inicial" na própria ADR. |

### 4. Guardrails

| | |
|---|---|
| **Já implementado** | Guardrails de produto formalizados (DEVE / NÃO DEVE / QUANDO EM DÚVIDA) e incorporados ao system prompt; AGENTS.md prescrevendo padrões de código (TypeScript strict, Zod, pino, nunca `console.log`, nunca logar dados pessoais); gate de code review humano antes de merge, já definido pelo Delivery Manager no Cenário 2. |
| **Falta** | Todo o enforcement de guardrail de **produto** hoje é via prompt — probabilístico. E o enforcement de guardrail de **código** (AGENTS.md) depende inteiramente do humano lembrar de aplicá-lo no code review: o módulo de feedback gerado pelo Copilot ignorou 4 regras do AGENTS.md (`as any` sem Zod, `console.log`, `require` dinâmico, e-mail do atendente logado) e isso só foi descoberto depois, não impedido antes. Não há, hoje, nenhum ponto de **human-in-the-loop** explícito para respostas de baixa confiança sobre temas sensíveis (ex.: carga perigosa) — a resposta, correta ou não, vai direto ao atendente. |
| **Como fechar o gap** | Guardrail de produto passa a ter uma camada determinística: os dois checks do `response-validator.ts` (§2a) mais a verificação de fonte válida (§2b, Tarefa 2) rodam **depois** da geração e **antes** de a resposta chegar ao atendente — se qualquer check falhar, a resposta é substituída por uma mensagem padrão seguem, nunca a resposta suspeita original. Guardrail de código ganha uma verificação automática (lint/CI local rodando as regras que o AGENTS.md já prescreve — ex.: proibir `console.log` e `require` dinâmico via regra de lint, não só via revisão humana), reduzindo o quanto depende só da atenção do revisor. E se define um ponto de HITL novo e explícito: toda resposta cujo `confidence_score` vier abaixo de um limiar **e** que mencione um dos temas sensíveis do domínio (carga perigosa, valores de frete, exceções de SLA) é retida para revisão humana antes de ir ao atendente, em vez de ser entregue automaticamente — o mesmo princípio que o Delivery Manager está formalizando como critério de go-live (Exercício 3.1 do DM). |

### 5. Observability

| | |
|---|---|
| **Já implementado** | Nada explícito ainda além dos logs que o `pino` já produziria se o AGENTS.md fosse seguido à risca — que é justamente o que o módulo de feedback mostrou não acontecer sempre. |
| **Falta** | Não há, hoje, nenhum mecanismo que distinga, de forma agregada, os três tipos de falha descobertos em staging (alucinação, documento desatualizado, chunk errado) nem que avise o time quando a taxa de respostas suspeitas (detectadas pela camada de Verification loops) sobe. |
| **Como fechar o gap** | Cada verificação da camada 2 (`response-validator.ts` e a checagem de fonte válida da Tarefa 2) deve **logar estruturadamente** (via `pino`, nunca `console.log`) o motivo específico de qualquer rejeição — não só "resposta rejeitada", mas `motivo: fonte_invalida | fonte_ausente | guardrail_carga_perigosa`, com um `correlationId` por query para permitir juntar isso ao histórico de conversa no Teams. Esses logs estruturados são a matéria-prima que o Delivery Manager usa no plano de observabilidade (Exercício 3.2 do DM) para calcular a métrica "% de respostas com problema de fundamentação" — esta camada do harness produz o dado; a camada de produto decide o threshold de alerta. |

---

## Tarefa 2 — Verificação de fonte citada (Verification loops)

Esta parte do exercício pede uma função **implementada com GitHub Copilot**. Como
combinado, aviso antes de qualquer tarefa que dependa do Copilot: **esta é uma
delas** — a implementação deve rodar na sua sessão separada de Copilot, e o
resultado (código + evidência de teste) volta como artefato para eu incorporar
aqui e avaliarmos juntos.

### O que pedir ao Copilot

Especificação da função (dê isso como prompt/contexto ao Copilot, na cópia de
trabalho do `novatech-assistant`, ver [AGENTS.md](../../../AGENTS.md) da raiz
deste repositório para onde ela vive):

- **Nome sugerido do arquivo:** `src/services/source-verifier.ts` (nova
  verificação, separada do `response-validator.ts` do Dev — ambas compõem a
  mesma camada de harness, mas são checks independentes).
- **Entrada:** a resposta do modelo já parseada (objeto com, no mínimo, o campo
  `source_document: string`).
- **Lista de documentos válidos** (identificadores curtos, não o título
  completo): `POL-001`, `PROC-042`, `PROC-042-v2`, `SLA-2024`,
  `FAQ-Atendimento`.
- **Comportamento:** se `source_document` não estiver nessa lista (vazio,
  inventado, ou com formatação diferente do identificador curto), marcar a
  resposta como **suspeita** — não decidir sozinha se bloqueia ou não; apenas
  sinalizar (ex.: retornar `{ valid: boolean, reason?: string }`), para que quem
  chama a função decida o que fazer (consistente com o padrão determinístico
  vs. probabilístico do AGENTS.md do projeto).
- **Seguir as convenções do AGENTS.md do `novatech-assistant`:** TypeScript
  strict, sem `any`, sem `console.log` (usar o logger do projeto se for logar
  algo), função pura e testável isoladamente.

### O que trazer de volta

1. O arquivo `source-verifier.ts` gerado.
2. Evidência real do teste com o Copilot (prompt usado + saída), no mesmo
   formato já usado em `resolucoes/cenario-2/exercicio-2-1/` e
   `.../exercicio-2-3/` (`teste-copilot-*.md`).
3. Se o Copilot errar algo na primeira tentativa (ex.: comparar título completo
   em vez do identificador curto, ou não cobrir case-sensitivity), documentar
   e iterar — isso também é avaliado.

### Resultado

Implementado e validado — ver [`teste-copilot-source-verifier.md`](./teste-copilot-source-verifier.md)
para a evidência completa. Resumo: `verifySourceDocument()` em
[`novatech-assistant/src/services/source-verifier.ts`](./novatech-assistant/src/services/source-verifier.ts),
integrada ao `response-builder.ts` do query endpoint, sinalizando
`is_suspicious` / `suspicion_reason` sem decidir bloqueio sozinha. 5 testes
(4 unitários + 1 de integração) passando, reexecutados de forma independente
nesta sessão, e sem erros de tipo (`tsc --noEmit`). Nenhum erro do Copilot
precisou de correção nesta rodada. O caso de borda de normalização
(case-insensitive + espaços) que estava sem teste dedicado foi coberto depois
(ver seção "Iteração" do arquivo de evidência); permanece em aberto, fora do
escopo desta verificação simples, o reconhecimento de fonte citada pelo título
completo do documento em vez do identificador curto.

---

## Resumo executivo

| Camada | Status | Gap principal | Fechamento |
|---|---|---|---|
| Tool orchestration | Implementada (MVP) | Sem tratamento diferenciado de falha por etapa | Distinguir falha de busca / geração / validação antes de expandir para multi-query |
| Verification loops | Parcial | Nenhuma verificação de conteúdo, só de código | Structured output + 2 guardrails determinísticos (Dev 3.1, ainda não implementados neste clone) + verificação de fonte válida — **implementada e testada** ([evidência](./teste-copilot-source-verifier.md)) |
| Context & memory | Decidida, não instrumentada | Sem medição real de tokens nem corte automático | Instrumentar `prompt-builder.ts` para medir e aplicar a regra de corte da ADR-0002 |
| Guardrails | Formalizados, enforcement só probabilístico | Nenhum HITL para respostas sensíveis de baixa confiança; código pode ignorar AGENTS.md sem ser barrado antes do review | Checks determinísticos bloqueiam antes da entrega; HITL para baixa confiança + tema sensível; lint automatizado das regras do AGENTS.md |
| Observability | Inexistente | Nenhum log estruturado por motivo de rejeição | Log estruturado (pino) por tipo de falha + `correlationId`, consumido pelo plano de observabilidade do Delivery Manager |
