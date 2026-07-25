# Teste do SKILL.md `azure-functions-endpoint` com GitHub Copilot — Exercício 2.3 (Tech Lead), Tarefa 3 (rodada 2)

> Com a skill **v2** ([`azure-functions-endpoint.md_v2`](./azure-functions-endpoint.md_v2)) no repositório, o Copilot foi instruído a gerar um endpoint **diferente** do testado na rodada 1 — `feedback` (handler + validator + response-builder + serviço `saveFeedback`) — em vez de regenerar `query`. Objetivo: fechar o critério 2 dos critérios de maturidade ("≥ 2 artefatos-alvo diferentes") e verificar se as 3 mudanças da v2 (regra 6 reescrita, regra 9 estendida, regra 10 nova) se sustentam num artefato novo.

## Arquivos alterados pelo Copilot nesta rodada

- `src/functions/feedback/handler.ts` (stub → implementado)
- `src/functions/feedback/validator.ts` (stub → implementado)
- `src/functions/feedback/response-builder.ts` (novo)
- `src/services/feedback.ts` (novo)
- `tests/integration/feedback-handler.integration.test.ts` (novo)

`query` (handler, validator, response-builder) e os arquivos compartilhados (`errors.ts`, `logger.ts`, `types.ts`, `search.ts`, `completion.ts`, `prompt-builder.ts`) **não foram tocados nesta rodada** — permanecem exatamente como na rodada 1.

### `src/functions/feedback/handler.ts`

```typescript
import { app, HttpRequest, HttpResponseInit, InvocationContext } from "@azure/functions";
import { saveFeedback } from "../../services/feedback";
import {
	NotImplementedError,
	NotFoundError,
	UpstreamServiceError,
	ValidationError,
} from "../../shared/errors";
import { logger } from "../../shared/logger";
import { buildFeedbackResponse } from "./response-builder";
import { parseFeedbackRequest } from "./validator";

export async function feedbackHandler(
	request: HttpRequest,
	context: InvocationContext,
): Promise<HttpResponseInit> {
	try {
		const body = await request.json().catch(() => {
			throw new ValidationError("Invalid JSON payload");
		});

		const parsed = parseFeedbackRequest(body);
		const savedFeedback = await saveFeedback(parsed);
		const responseBody = buildFeedbackResponse(savedFeedback);

		logger.info({ invocationId: context.invocationId }, "feedback handled successfully");
		return { status: 202, jsonBody: responseBody };
	} catch (err) {
		logger.error({ err, invocationId: context.invocationId }, "feedback handler failed");

		if (err instanceof ValidationError) return { status: 400, jsonBody: { error: err.message } };
		if (err instanceof NotFoundError) return { status: 404, jsonBody: { error: err.message } };
		if (err instanceof NotImplementedError) {
			return { status: 501, jsonBody: { error: "not implemented" } };
		}
		if (err instanceof UpstreamServiceError) return { status: 502, jsonBody: { error: err.message } };
		return { status: 500, jsonBody: { error: "internal error" } };
	}
}

app.http("feedback", {
	methods: ["POST"],
	authLevel: "function",
	route: "feedback",
	handler: feedbackHandler,
});
```

### `src/functions/feedback/validator.ts`

Schemas Zod de request (`queryId`, `rating: "helpful" | "not_helpful"`, `comment` opcional) e de response (`feedback_id`, `status: "accepted"`), ambos com `safeParse` — mesmo padrão de `query/validator.ts`.

### `src/functions/feedback/response-builder.ts` e `src/services/feedback.ts`

```typescript
// src/services/feedback.ts
import { NotImplementedError } from "../shared/errors";
import type { FeedbackRequest } from "../functions/feedback/validator";

export type SavedFeedback = {
  id: string;
};

export async function saveFeedback(_feedback: FeedbackRequest): Promise<SavedFeedback> {
  throw new NotImplementedError("feedback service not implemented");
}
```

```typescript
// src/functions/feedback/response-builder.ts
import type { SavedFeedback } from "../../services/feedback";
import { validateFeedbackResponse } from "./validator";

export function buildFeedbackResponse(savedFeedback: SavedFeedback) {
  return validateFeedbackResponse({
    feedback_id: savedFeedback.id,
    status: "accepted",
  });
}
```

### `tests/integration/feedback-handler.integration.test.ts` (novo)

2 casos, mesmo padrão do teste de `query`: request inválido → 400; serviço não implementado → 501.

---

## Avaliação regra a regra (skill v2, 10 regras)

| # | Regra | Seguiu? | Evidência |
|---|---|---|---|
| 1 | Modelo `app.http(...)` v4 | ✅ Sim | `app.http("feedback", { ... })`, sem `function.json`. |
| 2 | Validação Zod `safeParse` em `validator.ts` | ✅ Sim | `feedbackRequestSchema.safeParse(body)`; validou também a response. |
| 3 | Pipeline real, 501 se serviço não existe, nunca hardcode | ✅ Sim | Handler chama `saveFeedback` (serviço real, ainda stub); nenhum dado hardcoded; `NotImplementedError` → 501. |
| 4 | Erros como classes, único `try/catch`, nunca descarta erro | ✅ Sim | Mesmo padrão de 5 ramos `instanceof` da rodada 1, reaplicado corretamente a um endpoint novo (não copiado/colado sem adaptar — os status fazem sentido para o domínio de feedback). |
| 5 | `pino`, nunca `console.log`/`context.log` | ✅ Sim | `logger.info`/`logger.error` com `invocationId`; nenhuma ocorrência de `console.log`/`context.log`. |
| 6 (v2) | `retry.ts` só obrigatório quando houver chamada de rede real | ✅ Sim (não se aplica ainda) | `saveFeedback` é stub; nenhuma tentativa de implementar retry prematuramente. |
| 7 | Budget de contexto (ADR-0002) | N/A | `feedback` não monta prompt; regra não se aplica a este endpoint. |
| 8 | Resposta sempre via `response-builder.ts` | ✅ Sim | `buildFeedbackResponse` centraliza a montagem e valida o shape via Zod antes de retornar — adaptação correta de "sempre incluir `source_document`" para o campo relevante deste endpoint (`feedback_id`/`status`), já que feedback não é conteúdo derivado de busca. |
| 9 (v2) | Teste cobre todo status HTTP atualmente alcançável | ✅ Sim | 400 e 501 são os únicos status alcançáveis hoje (não há caminho para 404 em feedback — não é regra quebrada, é ausência de aplicabilidade); ambos cobertos. |
| 10 (v2, nova) | Indentação de 2 espaços, sem tabs | ❌ **Não** | `feedback/handler.ts` e `feedback/validator.ts` usam **tab**; `feedback/response-builder.ts` e `services/feedback.ts` usam **2 espaços**. Inconsistente mesmo dentro da mesma rodada, para o mesmo endpoint. Verificado com `grep -P '^\t'` nos 4 arquivos. |

**Resultado da rodada 2: 8/10 regras seguidas, 1/10 não aplicável ao domínio deste endpoint (regra 7), 1/10 violada (regra 10, a única regra nova desta versão).**

---

## Validação real (execução)

```
npm run test
✓ tests/integration/feedback-handler.integration.test.ts (2 tests) 21ms
✓ tests/integration/query-handler.integration.test.ts (2 tests) 18ms
Test Files  2 passed (2)
     Tests  4 passed (4)

npm run build
> tsc -p .
(sem erros — build limpo sob strict: true, incluindo o novo endpoint)
```

`query` continua passando (2/2) sem ter sido tocado — a mudança na skill não causou regressão no artefato da rodada 1.

---

## Achado principal: regra 10 é a primeira regra realmente violada em 2 rodadas de teste

Diferente da rodada 1 (0 violações), esta rodada expõe uma violação real, e ela é instrutiva: a regra 10 pede indentação consistente **via texto prescritivo na skill** (nível de prompt), e o próprio teste mostra que isso não é confiável — o Copilot obedeceu em 2 dos 4 arquivos gerados na mesma leva e ignorou nos outros 2, sem nenhum padrão aparente (não é "os arquivos maiores" nem "os primeiros gerados").

Isso é o mesmo raciocínio que o Product Specialist aplicou aos guardrails de produto no Exercício 2.2 (classificar cada regra como **enforcement via prompt** [probabilístico] ou **enforcement via código** [determinístico]): a regra 10, do jeito que está, é só prompt — e a evidência empírica agora mostra exatamente o resultado esperado de uma regra de estilo dependente só de instrução textual. As outras 9 regras desta skill são, em grande parte, também "só prompt" — mas até agora sobreviveram a 2 rodadas sem violação; a de indentação é a primeira a falhar, plausivelmente por ser puramente estética (sem uma consequência funcional visível para o modelo, como um teste que quebra).

**Recomendação (fica para decisão do Tech Lead, não apliquei sem confirmar):** mover a regra 10 de enforcement-por-prompt para enforcement-por-código, adicionando um formatter (`prettier` + `.editorconfig`, ou configuração equivalente de `eslint`) ao projeto e um script (`npm run format`/`format:check`) que o CI ou o próprio Copilot possam rodar — nesse caso a regra deixa de depender de o modelo "lembrar" e passa a ser corrigida automaticamente. Isso não é uma reescrita da skill em si, é uma mudança de infraestrutura do projeto (`package.json`, possivelmente `.github/workflows/ci.yml`) — por isso não apliquei nesta rodada sem confirmar com você.

---

## Resumo

**Arquivos desta rodada:** `src/functions/feedback/handler.ts`, `src/functions/feedback/validator.ts`, `src/functions/feedback/response-builder.ts` (novo), `src/services/feedback.ts` (novo), `tests/integration/feedback-handler.integration.test.ts` (novo). `query` e os arquivos compartilhados não mudaram.

A skill v2 generalizou bem para um artefato diferente do exemplo canônico do próprio SKILL.md: as 9 regras herdadas da v1 continuam sendo seguidas (ou corretamente não-aplicáveis, caso da regra 7), incluindo a reescrita da regra 6 (nenhuma tentativa prematura de retry num serviço ainda-stub). A única regra violada é a única regra **nova** desta versão (10 — indentação), e a violação é útil: prova que uma regra de estilo puramente textual não é suficiente sozinha, then aponta o próximo passo concreto (mover para enforcement de código) em vez de só reescrever o texto da regra de novo. Com esta rodada, o critério 2 dos critérios de maturidade (≥ 2 artefatos-alvo diferentes) está atendido; o critério 3 (0 violações em 2 rodadas consecutivas) **não** está — reinicia a contagem a partir da próxima rodada limpa.
