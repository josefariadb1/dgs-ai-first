# Teste do SKILL.md `azure-functions-endpoint` com GitHub Copilot — Exercício 2.3 (Tech Lead), Tarefa 2 (rodada 1)

> Skill testada: [`skills/domain/azure-functions-endpoint.md`](../../../praticas/pratica-2/Prática%202%20-%20V2/novatech-assistant/skills/domain/azure-functions-endpoint.md) ([snapshot v1](./azure-functions-endpoint.md_v1)). Com o arquivo presente no repositório, o Copilot foi instruído a gerar o `query` endpoint (handler + validator + response-builder), os serviços que ele consome, e o teste de integração correspondente.

## Contexto

Antes deste teste, `src/functions/query/handler.ts` era um stub (`throw new Error("Not implemented")`) e `validator.ts`, `response-builder.ts`, `src/services/{search,completion,prompt-builder}.ts`, `src/shared/{errors,logger,types}.ts` estavam vazios (estado inicial do starter repo, Anexo C). O Copilot tocou nos 9 arquivos de código abaixo e criou 1 arquivo novo de teste. Não avaliei aqui as mudanças em `.mcp/mcp.json` e `AGENTS.md` que já estavam pendentes no working tree — são resultado de exercícios anteriores (2.1/2.2), não deste teste.

---

## Arquivos alterados pelo Copilot

### `src/functions/query/handler.ts` (stub → implementado)

```typescript
import { app, HttpRequest, HttpResponseInit, InvocationContext } from "@azure/functions";
import { getCompletion } from "../../services/completion";
import { buildPrompt } from "../../services/prompt-builder";
import { searchChunks } from "../../services/search";
import {
  NotFoundError,
  NotImplementedError,
  UpstreamServiceError,
  ValidationError,
} from "../../shared/errors";
import { logger } from "../../shared/logger";
import { buildQueryResponse } from "./response-builder";
import { parseQueryRequest } from "./validator";

export async function queryHandler(
  request: HttpRequest,
  context: InvocationContext,
): Promise<HttpResponseInit> {
  try {
    const body = await request.json().catch(() => {
      throw new ValidationError("Invalid JSON payload");
    });

    const parsed = parseQueryRequest(body);
    const chunks = await searchChunks(parsed.question);

    if (chunks.length === 0) {
      throw new NotFoundError("No relevant document found for this question");
    }

    const prompt = buildPrompt({
      question: parsed.question,
      chunks,
      history: parsed.conversationHistory,
    });
    const completion = await getCompletion(prompt);

    logger.info({ invocationId: context.invocationId }, "query handled successfully");
    return { status: 200, jsonBody: buildQueryResponse(completion, chunks) };
  } catch (err) {
    logger.error({ err, invocationId: context.invocationId }, "query handler failed");

    if (err instanceof ValidationError) return { status: 400, jsonBody: { error: err.message } };
    if (err instanceof NotFoundError) return { status: 404, jsonBody: { error: err.message } };
    if (err instanceof NotImplementedError) {
      return { status: 501, jsonBody: { error: "not implemented" } };
    }
    if (err instanceof UpstreamServiceError) return { status: 502, jsonBody: { error: err.message } };
    return { status: 500, jsonBody: { error: "internal error" } };
  }
}

app.http("query", {
  methods: ["POST"],
  authLevel: "function",
  route: "query",
  handler: queryHandler,
});
```

### `src/functions/query/validator.ts` (vazio → implementado)

Schemas Zod de request **e** de response (`queryRequestSchema`, `queryResponseSchema`), ambos com `safeParse` e erro traduzido para `ValidationError`.

### `src/functions/query/response-builder.ts` (vazio → implementado)

```typescript
import { NotFoundError } from "../../shared/errors";
import type { QueryCompletion, QueryResponseBody, RetrievedChunk } from "../../shared/types";
import { validateQueryResponse } from "./validator";

export function buildQueryResponse(
	completion: QueryCompletion,
	chunks: RetrievedChunk[],
): QueryResponseBody {
	const primaryChunk = chunks[0];

	if (!primaryChunk?.sourceDocument) {
		throw new NotFoundError("No source document available for response");
	}

	return validateQueryResponse({
		answer: completion.answer,
		source_document: primaryChunk.sourceDocument,
	});
}
```

### `src/services/search.ts`, `src/services/prompt-builder.ts`, `src/services/completion.ts` (vazios → stubs de erro explícito)

Os três serviços agora existem como arquivos, mas cada um lança `NotImplementedError` (em vez de conter lógica real de Azure AI Search / Azure OpenAI, que ainda não foi implementada):

```typescript
// src/services/search.ts
export async function searchChunks(_question: string): Promise<RetrievedChunk[]> {
	throw new NotImplementedError("search service not implemented");
}
```
(mesmo padrão em `prompt-builder.ts` e `completion.ts`, cada um com sua mensagem.)

### `src/shared/errors.ts` (vazio → implementado)

Classe base `AppError extends Error` com `statusCode`, e 4 subclasses: `ValidationError` (400), `NotFoundError` (404), `UpstreamServiceError` (502), `NotImplementedError` (501, adicionada além das 3 citadas nominalmente na skill — coerente com a regra 3, que já previa resposta 501 para serviço não implementado).

### `src/shared/logger.ts` (vazio → implementado)

```typescript
import pino from "pino";
export const logger = pino({ name: "novatech-assistant" });
```

### `src/shared/types.ts` (vazio → implementado)

Tipos `ConversationTurn`, `RetrievedChunk`, `QueryCompletion`, `QueryResponseBody`.

### `tests/integration/query-handler.integration.test.ts` (novo)

2 casos: request inválido → 400; serviços não implementados → 501. Usa `vi.fn()` para mockar `HttpRequest.json`, sem tocar rede real.

### `package.json` (parcial — apenas o bloco novo)

```diff
+  "dependencies": {
+    "@azure/functions": "^4.6.0",
+    "pino": "^9.3.2"
+  },
```
(`package-lock.json` foi gerado pelo `npm install` correspondente — não incluído aqui por ser gerado.)

---

## Avaliação regra a regra (contra `skills/domain/azure-functions-endpoint.md`)

| # | Regra da skill | Seguiu? | Evidência |
|---|---|---|---|
| 1 | Modelo `app.http(...)` (v4), nunca `function.json`/v3 | ✅ Sim | `app.http("query", { ... })` no final de `handler.ts`; nenhum `function.json` criado. |
| 2 | Validação via Zod `safeParse` em `validator.ts`, nunca `if` manual | ✅ Sim | `queryRequestSchema.safeParse(body)`; foi além e também validou a *response* (`queryResponseSchema`), não só o request. |
| 3 | Pipeline real (`search → prompt-builder → completion`), 501 se serviço não existe, nunca hardcode | ✅ Sim | Handler chama os 3 serviços em sequência; cada stub lança `NotImplementedError`, capturado e traduzido para `501`. Nenhum dado hardcoded. |
| 4 | Erros como classes em `errors.ts`, único `try/catch`, `catch` nunca descarta o erro | ✅ Sim | Um único `try/catch`; 5 ramos de `instanceof` mapeando para status; toda falha loga antes de responder. |
| 5 | `pino` em todo caminho, `console.log`/`context.log` proibidos | ✅ Sim | `logger.info` no sucesso, `logger.error` na falha; nenhuma ocorrência de `console.log` ou `context.log` em nenhum arquivo tocado. |
| 6 | Serviços Azure via `src/services/*`, retry em `src/shared/retry.ts`, handler não chama Azure direto | ⚠️ Não testável ainda | Handler não chama Azure diretamente (ok), mas os serviços ainda não fazem nenhuma chamada real — `retry.ts` não foi criado porque ainda não há chamada de rede para envolver. Não é violação, é escopo ainda não alcançado. |
| 7 | Handler não amplia contexto além do que o `prompt-builder` monta (budget ADR-0002) | ⚠️ Não testável ainda | `prompt-builder.ts` é stub; a regra só é verificável quando ele tiver lógica real de truncamento. |
| 8 | Resposta sempre via `response-builder.ts`, sempre com `source_document` | ✅ Sim | `buildQueryResponse` lança `NotFoundError` se não houver `sourceDocument`, e valida o shape final com Zod antes de retornar. |
| 9 | Todo endpoint tem teste de integração | ✅ Sim (parcial) | `tests/integration/query-handler.integration.test.ts` cobre 400 e 501. Não cobre 404 nem 200 — ver Gaps abaixo. |

**Resultado da rodada 1: 6/9 regras plenamente verificadas e seguidas, 2/9 ainda não testáveis (dependem de código que é tarefa futura do Dev, não desta skill), 0/9 violadas.**

---

## Validação real (execução, não só leitura de código)

```
npm run test
✓ tests/integration/query-handler.integration.test.ts (2 tests) 13ms
Test Files  1 passed (1)
     Tests  2 passed (2)

npm run build
> tsc -p .
(sem erros — build limpo sob strict: true)

npm run lint
> eslint .
'eslint' não é reconhecido como um comando interno ou externo...
```

O `lint` falha porque `eslint` nunca foi adicionado como dependência do projeto (gap do scaffold inicial, não introduzido por este teste — nenhum dos arquivos gerados pelo Copilot depende de lint para estar correto).

---

## Gaps e observações (o que não foi 100%, sem inflar como se fosse falha grave)

- **Indentação inconsistente:** os arquivos gerados usam tab (`\t`), enquanto o exemplo DO da skill usa 2 espaços. A skill não define isso (é assunto de `skills/foundation/typescript-conventions.md`, que ainda está vazio) — não é uma violação da skill testada, mas é um candidato natural para a Tarefa 3 (reforçar indentação na skill, ou apontar para a Foundation skill quando ela existir).
- **Cobertura de teste incompleta:** só 400 e 501 são cobertos; 404 (`NotFoundError`) está inalcançável no estado atual porque `searchChunks` sempre lança `NotImplementedError` antes de poder retornar lista vazia, e 200 depende dos 3 serviços estarem implementados. Não é um erro do Copilot — é uma limitação do estado atual do código — mas vale registrar como pendência para quando os serviços forem implementados de verdade.
- **`retry.ts` ainda não existe:** correto para o estado atual (nenhuma chamada de rede real ainda), mas a regra 6 só será validada de fato quando `completion.ts`/`search.ts` chamarem Azure OpenAI/AI Search de verdade.
- **`eslint` ausente do projeto:** não é uma responsabilidade desta skill, mas impede validar convenções de estilo automaticamente; considerar adicionar como dependência antes do próximo ciclo de geração de código.

---

## Resumo

**Arquivos alterados nesta rodada de teste:** `src/functions/query/handler.ts`, `src/functions/query/validator.ts`, `src/functions/query/response-builder.ts`, `src/services/search.ts`, `src/services/prompt-builder.ts`, `src/services/completion.ts`, `src/shared/errors.ts`, `src/shared/logger.ts`, `src/shared/types.ts`, `package.json` (bloco `dependencies`), `package-lock.json` (gerado); **arquivo novo:** `tests/integration/query-handler.integration.test.ts`.

O Copilot seguiu fielmente as 6 regras da skill que já eram testáveis no estado atual do repositório (modelo v4, validação Zod, pipeline sem hardcode com 501 explícito, erros tipados com try/catch único, logging via pino sem `console.log`/`context.log`, resposta sempre via `response-builder` com `source_document`). As 2 regras restantes (retry com backoff, respeito ao budget de contexto) ainda não puderam ser exercitadas porque dependem de lógica de integração real com Azure que é trabalho futuro do Dev — não indicam que a skill falhou, indicam que ela ainda não foi testada nesse ponto. Validação real (`npm run test` e `npm run build`) confirma que o código não só segue o padrão como também **funciona**: 2/2 testes passam e o build compila sob `strict: true`. Nenhuma violação das regras foi encontrada nesta rodada — os únicos pontos de atenção (indentação não especificada, cobertura de teste parcial, `eslint` ausente) são gaps de escopo, não desvios da skill. Isso sugere que, para a Tarefa 3, a iteração pode focar em **fechar as 2 regras não testáveis quando os serviços forem implementados** e em **fortalecer a skill com uma nota sobre indentação/estilo** assim que a Foundation skill de TypeScript existir, em vez de reescrever seções que falharam.
