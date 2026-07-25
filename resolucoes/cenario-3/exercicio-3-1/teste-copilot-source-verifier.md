# Teste do Copilot — `source-verifier.ts` (Exercício 3.1, Tech Lead, Tarefa 2)

> Execução via GitHub Copilot em sessão separada, conforme combinado. Evidência trazida de volta e verificada de forma independente nesta sessão (re-execução dos testes e checagem de tipos).

## Contexto entregue ao Copilot

Especificação usada (seção "Tarefa 2" de [`harness-design.md`](./harness-design.md)):
arquivo `src/services/source-verifier.ts`, recebendo a resposta já parseada do
modelo (`source_document: string`), comparando contra a allowlist de
identificadores curtos (`POL-001`, `PROC-042`, `PROC-042-v2`, `SLA-2024`,
`FAQ-Atendimento`), sinalizando suspeita sem decidir bloqueio sozinha, seguindo
o AGENTS.md do projeto (TypeScript strict, sem `any`, sem `console.log`).

## O que foi gerado

Trabalho executado na cópia de trabalho do starter repo, agora versionada em
[`novatech-assistant/`](./novatech-assistant/):

- [`src/services/source-verifier.ts`](./novatech-assistant/src/services/source-verifier.ts)
  — `verifySourceDocument()`: normaliza o `source_document` recebido
  (case-insensitive), resolve contra a allowlist via `Map`, e retorna
  `{ isSuspicious, suspicionReason, normalizedSourceDocument }` sem lançar
  exceção — a decisão de bloquear fica em quem chama a função, como pedido.
- Integração em [`src/functions/query/response-builder.ts`](./novatech-assistant/src/functions/query/response-builder.ts):
  valida o output do modelo contra o schema Zod (`queryResponseSchema`) e então
  chama `verifySourceDocument`, propagando `is_suspicious` /
  `suspicion_reason` na resposta final do endpoint.
- [`src/functions/query/handler.ts`](./novatech-assistant/src/functions/query/handler.ts)
  loga (via `pino`, nunca `console.log`) quando uma resposta é sinalizada como
  suspeita, com `question` e `sourceDocument` — sem dado pessoal do atendente.
- Suporte reconstruído para o endpoint funcionar ponta a ponta no clone:
  `search.ts` (retrieval simples por sobreposição de tokens sobre uma base de
  conhecimento fixa dos 5 documentos da NovaTech), `completion.ts` (stub
  determinístico que devolve o melhor chunk), `prompt-builder.ts` (aplica o
  orçamento da ADR-0002: até 5 chunks, até 3 turnos de histórico, log quando
  algo é cortado), e `validator.ts` (schemas Zod de request/response).

## Validação (reexecutada de forma independente)

```
$ npx vitest run tests/unit/source-verifier.test.ts tests/integration/query-endpoint.test.ts

 ✓ tests/unit/source-verifier.test.ts (3 tests) 2ms
 ✓ tests/integration/query-endpoint.test.ts (1 test) 10ms

 Test Files  2 passed (2)
      Tests  4 passed (4)
```

```
$ npx tsc -p . --noEmit
(sem saída — nenhum erro de tipo)
```

Os 3 testes unitários cobrem os 3 casos relevantes da função: fonte válida
(`POL-001` → não suspeita), fonte ausente (`missing_source_document`), e
fonte fora da allowlist (`invalid_source_document`, usando `POL-999` como
exemplo de fonte inventada). O teste de integração confere que o endpoint
completo (pergunta → busca → prompt → geração → verificação) devolve
`source_document: "SLA-2024"` e `is_suspicious: false` para uma pergunta real
do domínio ("Qual o SLA do cliente Gold?").

## Iteração

Nenhum erro do Copilot foi reportado nesta rodada — a primeira versão gerada
já cobriu os 3 casos da allowlist e passou nos testes escritos para
confirmá-los.

**Pendência resolvida (2026-07-25):** o caso de borda de fonte citada em
formatação diferente do identificador curto (case diferente, espaços extras)
não tinha teste dedicado, apesar de o código já normalizar para esses casos.
Adicionado o teste `normalizes a source citation with different casing and
surrounding whitespace` (`source_document: "  pol-001  "` → normaliza para
`"POL-001"`, `isSuspicious: false`) em
[`source-verifier.test.ts`](./novatech-assistant/tests/unit/source-verifier.test.ts).
Suíte completa reexecutada: 5/5 testes passando (`tests/unit/source-verifier.test.ts`
com 4 testes, `tests/integration/query-endpoint.test.ts` com 1).

Ainda em aberto, fora do escopo desta verificação simples: fonte citada pelo
**título completo** do documento (ex.: "Política de Devolução de Mercadorias"
em vez de `POL-001`) não é reconhecida — a normalização cobre apenas
case/espaços, não um mapeamento título → identificador curto. Se isso se
mostrar um padrão real de erro do modelo, precisaria de uma tabela de aliases
adicional, não coberta por este exercício.
