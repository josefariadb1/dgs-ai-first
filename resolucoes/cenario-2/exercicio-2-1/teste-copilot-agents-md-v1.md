# Teste do AGENTS.md v1 com GitHub Copilot — Exercício 2.1 (Tech Lead), Tarefa 2

## Contexto

O `AGENTS.md_v1` (seções **Project Overview**, **Tech Stack & Architecture** — incluindo as regras de contexto da ADR-0002 —, **Coding Standards** e **Build & Deploy**) foi colocado no repositório `novatech-assistant`. Em outra sessão, o Copilot foi instruído a gerar:

1. Um endpoint Azure Function (`src/functions/query/`) — arquivos `handler.ts`, `validator.ts`, `response-builder.ts`.
2. Um teste de integração para esse endpoint — `tests/integration/query-endpoint.test.ts`.

Nesse ponto do repositório, `specs/query-endpoint/plan.md`, `skills/domain/*.md` e `skills/foundation/*.md` ainda estavam vazios (stubs) — ou seja, o **AGENTS.md era a única fonte de convenções** disponível ao Copilot. Isso é o próprio objeto do exercício: testar se o AGENTS.md, isolado, é prescritivo o suficiente.

Abaixo está o código gerado, sem nenhuma alteração, seguido da análise de aderência.

---

## Código gerado pelo Copilot (sem alterações)

### `src/functions/query/validator.ts`

```typescript
import { z } from "zod";

export const conversationTurnSchema = z.object({
	role: z.enum(["user", "assistant"]),
	content: z.string().min(1),
});

export const queryRequestSchema = z.object({
	question: z.string().trim().min(1).max(1000),
	conversationHistory: z.array(conversationTurnSchema).max(3).optional(),
});

export const queryResponseSchema = z.object({
	answer: z.string().min(1),
	source_document: z.string().nullable(),
});

export type QueryRequest = z.infer<typeof queryRequestSchema>;
export type QueryResponse = z.infer<typeof queryResponseSchema>;
```

### `src/functions/query/response-builder.ts`

```typescript
import type { QueryResponse } from "./validator";

export function buildQueryResponse(answer: string, sourceDocument: string | null): QueryResponse {
	return {
		answer,
		source_document: sourceDocument,
	};
}
```

### `src/functions/query/handler.ts`

```typescript
import { buildQueryResponse } from "./response-builder";
import { queryRequestSchema, queryResponseSchema } from "./validator";

type HttpRequestLike = {
  json: () => Promise<unknown>;
};

type HttpResponseLike = {
  status: number;
  jsonBody: unknown;
};

type KnowledgeEntry = {
  keywords: string[];
  answer: string;
  sourceDocument: string;
};

const knowledgeBase: KnowledgeEntry[] = [
  {
    keywords: ["prazo", "devol"],
    answer:
      "O prazo geral para solicitar devolucao e de ate 7 dias uteis apos o recebimento confirmado no tracking.",
    sourceDocument: "POL-001-politica-devolucao.md",
  },
  {
    keywords: ["carga perigosa", "devol"],
    answer:
      "Carga perigosa (classes 1 a 6 da ANTT) nao e elegivel para devolucao pelo processo padrao; o cliente deve ser orientado ao setor de Gestao de Riscos (ramal 4500).",
    sourceDocument: "POL-001-politica-devolucao.md",
  },
  {
    keywords: ["sla", "gold"],
    answer:
      "Para chamados gerais de cliente Gold, o SLA e resposta em ate 2h uteis e resolucao em ate 24h uteis.",
    sourceDocument: "SLA-2024-tabela-sla-clientes.md",
  },
  {
    keywords: ["platinum", "sla"],
    answer:
      "Nao existe tier Platinum na NovaTech. Os tiers validos sao Gold, Silver e Standard.",
    sourceDocument: "SLA-2024-tabela-sla-clientes.md",
  },
];

function createJsonResponse(status: number, jsonBody: unknown): HttpResponseLike {
  return {
    status,
    jsonBody,
  };
}

function normalizeText(value: string): string {
  return value.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
}

function findKnowledgeEntry(question: string): KnowledgeEntry | null {
  const normalizedQuestion = normalizeText(question);

  const exactMatch = knowledgeBase.find((entry) =>
    entry.keywords.every((keyword) => normalizedQuestion.includes(normalizeText(keyword))),
  );

  if (exactMatch) {
    return exactMatch;
  }

  const partialMatch = knowledgeBase.find((entry) =>
    entry.keywords.some((keyword) => normalizedQuestion.includes(normalizeText(keyword))),
  );

  return partialMatch ?? null;
}

export async function queryHandler(request: HttpRequestLike): Promise<HttpResponseLike> {
  try {
    const requestBody = await request.json();
    const parsedRequest = queryRequestSchema.safeParse(requestBody);

    if (!parsedRequest.success) {
      return createJsonResponse(400, {
        error: "Invalid query request",
        details: parsedRequest.error.flatten(),
      });
    }

    const knowledgeEntry = findKnowledgeEntry(parsedRequest.data.question);

    const response = knowledgeEntry
      ? buildQueryResponse(knowledgeEntry.answer, knowledgeEntry.sourceDocument)
      : buildQueryResponse(
          "Nao encontrei informacao suficiente na base indexada para responder com seguranca.",
          null,
        );

    const parsedResponse = queryResponseSchema.safeParse(response);

    if (!parsedResponse.success) {
      return createJsonResponse(500, {
        error: "Invalid query response",
      });
    }

    return createJsonResponse(200, parsedResponse.data);
  } catch {
    return createJsonResponse(500, {
      error: "Unexpected error while handling query",
    });
  }
}
```

### `tests/integration/query-endpoint.test.ts`

```typescript
import { describe, expect, it } from "vitest";

import { queryHandler } from "../../src/functions/query/handler";

describe("query endpoint", () => {
  it("returns answer and source_document for known query", async () => {
    const response = await queryHandler({
      json: async () => ({
        question: "Qual o prazo de devolucao?",
      }),
    });

    expect(response.status).toBe(200);
    expect(response.jsonBody).toMatchObject({
      source_document: "POL-001-politica-devolucao.md",
    });

    const body = response.jsonBody as { answer: string; source_document: string | null };
    expect(body.answer.toLowerCase()).toContain("7 dias uteis");
  });
});
```

---

## Análise de aderência ao AGENTS.md v1

### O que o Copilot seguiu

| Regra do AGENTS.md | Onde aparece no código gerado |
|---|---|
| TypeScript `strict: true`, sem `any` | Todos os tipos são explícitos (`HttpRequestLike`, `HttpResponseLike`, `KnowledgeEntry`, `QueryRequest`, `QueryResponse`); nenhum `any`. |
| "Todo endpoint valida input e output com Zod antes de processar ou retornar" | `handler.ts` chama `queryRequestSchema.safeParse` no input **e** `queryResponseSchema.safeParse` na resposta antes de devolver o 200 — os dois lados do contrato são validados, como exigido. |
| ADR-0002 — "histórico de conversa DEVE limitar a 3 turnos" | `validator.ts`: `conversationHistory: z.array(conversationTurnSchema).max(3).optional()`. Regra numérica exata do budget foi respeitada no schema. |
| "console.log é proibido em código de produção" | Nenhuma chamada a `console.log` em nenhum arquivo. |
| Nomenclatura/estrutura de arquivos (Anexo C) | `handler.ts` / `validator.ts` / `response-builder.ts` dentro de `src/functions/query/`, exatamente como especificado. |
| Idioma: código e identificadores em inglês | `queryHandler`, `findKnowledgeEntry`, `normalizeText`, `createJsonResponse` — nomes em inglês; só o conteúdo de negócio (strings de resposta) está em português, o que é dado, não código. |

### O que o Copilot NÃO seguiu

| Regra do AGENTS.md | Violação observada |
|---|---|
| "Logging: pino em todo o backend (...) o código deve logar quando o budget é excedido" | **Nenhum log é emitido em lugar nenhum.** Não há import de `pino`, nem log no catch genérico, nem no caminho de "não encontrei informação". Não é uso de `console.log` (que é proibido) — é a ausência total do logging exigido. |
| "Erros de negócio usam custom errors (`src/shared/errors.ts`), nunca throw de string ou objeto genérico" | O `catch` é genérico (`catch { ... }`) e devolve um objeto literal `{ error: "Unexpected error..." }`. `src/shared/errors.ts` nunca é importado — nenhuma classe de erro customizada é usada. |
| "Chamadas a serviços Azure (...) usam retry com exponential backoff" | Não há chamada real a Azure AI Search nem a Azure OpenAI — logo a regra de retry não tem onde ser aplicada (consequência do ponto abaixo). |
| **Arquitetura descrita em "Tech Stack & Architecture"**: pipeline de ingestão → Azure AI Search → prompt-builder (budget de chunks) → Azure OpenAI GPT-4o | O Copilot **substituiu toda a arquitetura de RAG por uma base de conhecimento estática hardcoded** (`knowledgeBase`) com match por palavra-chave. `src/services/search.ts`, `src/services/completion.ts` e `src/services/prompt-builder.ts` — os módulos que a própria arquitetura define para essa função — nunca são importados nem chamados. |
| ADR-0002 — budget de chunks (~8K tokens / máx. 5 chunks / ~1.500 tokens cada) | Como não há retrieval de chunks (ponto anterior), essa regra não chega a ser testada — ela foi **contornada por completo**, não apenas violada pontualmente, porque a etapa a que ela se aplica não existe no código gerado. |

### Observações adicionais (fora do escopo direto do AGENTS.md v1, mas relevantes)

- `pino` não consta em `package.json` (`devDependencies`/`dependencies`) — a regra de logging do AGENTS.md pede uma biblioteca que nem está instalada no projeto. Isso não justifica a ausência de log, mas explica por que o Copilot não tinha um padrão de import para seguir.
- O teste único cobre apenas o caminho feliz de "prazo de devolução". A própria `knowledgeBase` gerada contém casos de "carga perigosa + devolução" (que deveria ser negativa) e "tier Platinum" (inexistente) que não foram exercitados — lacunas de cobertura relevantes para o guardrail de produto "cargas perigosas nunca recebem informação de devolução", mas isso pertence à seção **Testing Standards**, ainda não escrita nesta versão do AGENTS.md.
- `tests/fixtures/queries.ts`, `chunks.ts` e `expected-responses.ts` existem como arquivos vazios; o teste gerado hardcoda a pergunta e a resposta esperada em vez de usá-los — coerente com o fato de os fixtures ainda não terem conteúdo, mas indica que a convenção de fixtures do Anexo C não foi reforçada em nenhum lugar do AGENTS.md v1.

---

## Resumo final — o que o Copilot NÃO seguiu

1. **Logging obrigatório via `pino`** — nenhum log foi emitido (nem no erro genérico, nem no caso "não encontrado"); o AGENTS.md exige pino em todo o backend e log explícito quando regras de contexto são violadas.
2. **Custom errors (`src/shared/errors.ts`)** — o handler usa um `catch` genérico com objeto literal, ignorando a taxonomia de erros exigida pelo Coding Standards.
3. **Retry com exponential backoff para chamadas Azure** — inexistente, porque nenhuma chamada real a Azure AI Search/OpenAI foi feita.
4. **A arquitetura de RAG definida em "Tech Stack & Architecture"** — o Copilot ignorou os serviços `search.ts`, `completion.ts` e `prompt-builder.ts` e implementou uma base de conhecimento estática com match por palavra-chave, um desenho completamente diferente do especificado.
5. **A regra de budget de chunks da ADR-0002** (máx. 5 chunks de ~1.500 tokens, ~8K tokens totais) — não pôde nem ser aplicada, pois a etapa de recuperação de chunks simplesmente não existe no código gerado.

Ponto positivo a destacar: a regra mais **numérica e local** (limite de 3 turnos de histórico, direto no schema Zod) foi seguida com exatidão — sugerindo que o AGENTS.md v1 é eficaz para regras pontuais e verificáveis em um único arquivo, mas insuficiente para garantir que o Copilot respeite a **arquitetura macro** do sistema (uso dos serviços corretos) e os **comportamentos transversais** (logging, tratamento de erro), que precisam ser reforçados na iteração v2 e/ou por skills dedicadas (`skills/domain/azure-functions-endpoint.md`, `skills/foundation/error-handling.md`).
