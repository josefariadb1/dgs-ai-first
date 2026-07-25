# Skill (Domain) — Azure Functions Endpoint

> **Quando usar:** sempre que for criar ou alterar um endpoint HTTP do NovaTech Assistant em `src/functions/<nome>/` (ex.: `query`, `feedback`, `health`, e qualquer endpoint futuro). Frase de ativação: "crie/gere um endpoint Azure Function para X".

## Contexto

O NovaTech Assistant expõe sua API como **Azure Functions v4 com HTTP triggers** (modelo de programação atual, não o modelo v3 baseado em `function.json` + `index.js`). Cada endpoint vive em `src/functions/<nome>/` e segue sempre a mesma decomposição em 3 arquivos, definida no Anexo C e reforçada aqui porque é a parte que um agente mais tende a colapsar em um arquivo só:

- `handler.ts` — o HTTP trigger. Orquestra: valida input → chama serviços de negócio (`src/services/*`) → monta resposta → loga → retorna. **Não contém lógica de negócio nem lógica de validação.**
- `validator.ts` — os schemas Zod de request/response e as funções que os aplicam. **Não conhece Azure Functions** (não importa `HttpRequest`/`HttpResponseInit`) — recebe/retorna dados já desserializados.
- `response-builder.ts` — monta o corpo de resposta HTTP a partir do resultado dos serviços (garante, entre outras coisas, que `source_document` esteja sempre presente quando aplicável).

Este skill assume as convenções gerais do projeto (`skills/foundation/typescript-conventions.md`, `skills/foundation/error-handling.md`, `skills/foundation/project-structure.md`) e a arquitetura de contexto da AGENTS.md (ADR-0002: budget de ~4K system + ~8K chunks/5 chunks). Ele **não** repete essas regras — ele mostra como elas se aplicam especificamente à camada de endpoint.

## Regras prescritivas

1. **Modelo de programação:** usar sempre `app.http(...)` do pacote `@azure/functions` v4 (`import { app } from "@azure/functions"`). Nunca gerar `function.json` nem o padrão de export default de v3.
2. **Validação:** todo handler **DEVE** validar o body do request com um schema Zod definido em `validator.ts`, usando `schema.safeParse(...)` — nunca `schema.parse(...)` direto no handler sem capturar o erro de validação como um `ValidationError` (ver regra 4). Nenhuma validação de shape/tipo é feita manualmente com `if`.
3. **Pipeline real, nunca hardcode:** um handler de negócio (ex.: `query`) **NÃO DEVE** montar a resposta com dados estáticos (arrays, mapas pergunta→resposta, `switch` de perguntas conhecidas). Ele **DEVE** chamar a cadeia real de serviços (`search.ts` → `prompt-builder.ts` → `completion.ts`, conforme a arquitetura da AGENTS.md). Se um desses serviços ainda não existe, o handler retorna `501` com `{ error: "not implemented" }` e loga em `error` — nunca substitui a chamada por uma implementação alternativa "para funcionar".
4. **Erros:** toda falha de negócio dentro do handler (validação falhou, recurso não encontrado, serviço upstream indisponível) é lançada como instância de `src/shared/errors.ts` (`ValidationError`, `NotFoundError`, `UpstreamServiceError`, ...) e capturada em **um único** `try/catch` no handler, que mapeia o tipo do erro para o status HTTP (`ValidationError` → 400, `NotFoundError` → 404, `UpstreamServiceError` → 502, erro não mapeado → 500) e loga via `logger.error({ err }, "mensagem")` antes de responder. `catch {}` que descarta o erro é proibido.
5. **Logging:** `pino` (`src/shared/logger.ts`) em todo caminho do handler — sucesso loga `info`, falha loga `error`. `console.log`/`context.log` são proibidos. Cada log inclui um identificador de correlação do request quando disponível.
6. **Chamadas a serviços Azure:** o handler nunca chama Azure OpenAI/AI Search diretamente — sempre via `src/services/*`. **A partir do momento em que um serviço fizer uma chamada de rede real** (Azure OpenAI, Azure AI Search), ele **DEVE** usar o helper de retry com backoff (`src/shared/retry.ts`, criado nessa hora se ainda não existir). Enquanto o serviço for um stub que lança `NotImplementedError` (regra 3), não ter `retry.ts` não é uma violação — é só um estado esperado de "ainda não chegamos lá". O handler nunca implementa retry por conta própria.
7. **Contexto:** se o endpoint monta prompt (caso de `query`), ele delega a montagem a `prompt-builder.ts` e nunca ultrapassa o budget da ADR-0002 no próprio handler (isso é responsabilidade do `prompt-builder.ts`, mas o handler não deve "ajudar" concatenando texto extra antes de chamar o builder).
8. **Resposta:** o corpo de resposta é sempre montado por `response-builder.ts`, nunca por um objeto literal inline no handler. Toda resposta de um endpoint que retorna conteúdo derivado de busca **DEVE** incluir `source_document`, mesmo em respostas de baixa confiança (regra vem de Product Rules & Guardrails).
9. **Teste obrigatório:** todo endpoint novo ou alterado vem acompanhado de um teste em `tests/integration/` seguindo `skills/domain/testing-patterns.md` — este skill não cobre teste, só o endpoint em si. O teste **DEVE** cobrir todo status HTTP **atualmente alcançável** pela implementação (ex.: enquanto `search.ts` for um stub que sempre lança `NotImplementedError`, cobrir 501 é suficiente e 404 não é alcançável — mas o teste **DEVE** ser revisitado e ganhar o caso de 404 assim que `search.ts` passar a poder retornar lista vazia de verdade). "Não dá para testar ainda" nunca é motivo para pular a cobertura do que já é alcançável hoje.
10. **Indentação:** 2 espaços, sem tabs, em todo arquivo TypeScript gerado por esta skill — até que `skills/foundation/typescript-conventions.md` seja escrita e vier a ser a fonte de verdade sobre estilo, esta é a regra que vale para o escopo desta skill.

## Exemplos de código

### DO — handler correto (pipeline real, validação, erros, logging)

```typescript
// src/functions/query/handler.ts
import { app, HttpRequest, HttpResponseInit, InvocationContext } from "@azure/functions";
import { logger } from "../../shared/logger";
import { ValidationError, NotFoundError, UpstreamServiceError } from "../../shared/errors";
import { parseQueryRequest } from "./validator";
import { buildQueryResponse } from "./response-builder";
import { searchChunks } from "../../services/search";
import { buildPrompt } from "../../services/prompt-builder";
import { getCompletion } from "../../services/completion";

export async function queryHandler(
  request: HttpRequest,
  context: InvocationContext,
): Promise<HttpResponseInit> {
  try {
    const body = await request.json();
    const parsed = parseQueryRequest(body); // throws ValidationError on bad input

    const chunks = await searchChunks(parsed.question); // max 5, enforced inside search.ts
    if (chunks.length === 0) {
      throw new NotFoundError("No relevant document found for this question");
    }

    const prompt = buildPrompt({ question: parsed.question, chunks, history: parsed.conversationHistory });
    const completion = await getCompletion(prompt); // retry/backoff lives inside completion.ts

    logger.info({ invocationId: context.invocationId }, "query handled successfully");
    return { status: 200, jsonBody: buildQueryResponse(completion, chunks) };
  } catch (err) {
    logger.error({ err, invocationId: context.invocationId }, "query handler failed");

    if (err instanceof ValidationError) return { status: 400, jsonBody: { error: err.message } };
    if (err instanceof NotFoundError) return { status: 404, jsonBody: { error: err.message } };
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

```typescript
// src/functions/query/validator.ts
import { z } from "zod";
import { ValidationError } from "../../shared/errors";

const queryRequestSchema = z.object({
  question: z.string().min(1).max(2000),
  conversationHistory: z
    .array(z.object({ role: z.enum(["user", "assistant"]), content: z.string() }))
    .max(3)
    .optional(),
});

export type QueryRequest = z.infer<typeof queryRequestSchema>;

export function parseQueryRequest(body: unknown): QueryRequest {
  const result = queryRequestSchema.safeParse(body);
  if (!result.success) {
    throw new ValidationError(result.error.issues.map((issue) => issue.message).join("; "));
  }
  return result.data;
}
```

### DON'T — o que um agente sem esta skill costuma gerar

```typescript
// ❌ src/functions/query/handler.ts — NÃO fazer isto
import { app } from "@azure/functions";

// ❌ hardcode: nenhuma chamada real a search/prompt-builder/completion
const ANSWERS: Record<string, string> = {
  "qual o prazo de devolução": "7 dias",
  "o que é frete especial": "acima de 500kg",
};

app.http("query", {
  methods: ["POST"],
  handler: async (request) => {
    const body = await request.json() as any; // ❌ sem Zod, `any` sem justificativa

    console.log("received query", body); // ❌ console.log proibido em src/

    try {
      const question = body.question.toLowerCase(); // ❌ sem validação de shape/tamanho
      const answer = ANSWERS[question] ?? "Não sei"; // ❌ hardcode + sem source_document
      return { status: 200, jsonBody: { answer } };
    } catch (e) {
      return { status: 500, jsonBody: { error: "erro" } }; // ❌ catch descarta o erro, não loga, não usa classes de erro
    }
  },
});
```

Por que isso é errado, ponto a ponto: sem Zod (regra 2) → sem pipeline real (regra 3) → `any` sem justificativa e `console.log` (Coding Standards do AGENTS.md) → resposta sem `source_document` (regra 8) → `catch` que descarta a exceção original (regra 4).

## Anti-padrões comuns (o que o Copilot realmente gera sem esta skill)

- **Modelo v3 misturado com v4:** gerar `function.json` ao lado de `app.http(...)`, ou usar `context.bindings` — resíduo de treinamento em exemplos antigos de Azure Functions.
- **`context.log(...)` em vez de `pino`:** o SDK do Azure Functions tem seu próprio logger (`context.log`); é o primeiro reflexo de um agente que não conhece a convenção do projeto.
- **Validação e lógica de negócio dentro do handler:** Copilot tende a gerar um único arquivo grande em vez dos 3 (`handler.ts` / `validator.ts` / `response-builder.ts`) — precisa ser instruído explicitamente a separar.
- **"Fazer funcionar" com mock:** quando um serviço dependido (`search.ts`, `completion.ts`) ainda não existe, a tendência é o agente inventar um retorno fixo em vez de responder `501` — isso esconde que a feature não está pronta.
- **`try/catch` genérico com `return { error: String(e) }`:** perde a distinção entre erro de validação, erro de negócio e erro de infraestrutura, e normalmente esquece de logar.
- **Ignorar o limite de 5 chunks / 3 turnos:** ao gerar o handler de `query`, é comum o agente passar `chunks` e `conversationHistory` inteiros para o `prompt-builder` sem truncar — a checagem deve estar em `search.ts`/`prompt-builder.ts`, mas o handler não deve concatenar dado extra "pra ajudar".
- **Esquecer `source_document`:** ao montar a resposta rapidamente, é comum omitir o campo mesmo com o dado disponível no resultado da busca.

## Dependências

- **Foundation (ler antes):** `skills/foundation/typescript-conventions.md`, `skills/foundation/error-handling.md`, `skills/foundation/project-structure.md`.
- **Domain relacionada:** `skills/domain/azure-ai-search-integration.md` (para endpoints que fazem retrieval, como `query`) e `skills/domain/testing-patterns.md` (teste obrigatório, ver regra 9).
- **Consumida por (Artifact):** `skills/artifact/create-rag-endpoint.md`, que usa esta skill como base e adiciona a receita específica de wiring de retrieval + completion.
- **Fonte de verdade normativa:** `AGENTS.md` (seções "Tech Stack & Architecture" e "Coding Standards") — em caso de conflito entre este skill e o AGENTS.md, o AGENTS.md prevalece; este skill deve ser corrigido.

## Histórico de iteração

- **v1:** versão inicial (regras 1-9, exemplos DO/DON'T, anti-padrões, dependências).
- **v2:** testada com Copilot na geração do `query` endpoint completo (handler, validator, response-builder, services stub, teste de integração). Nenhuma das 9 regras então existentes foi violada; a iteração endereça 3 gaps que o teste expôs, não correções de erro:
  - Regra 6 reescrita para deixar explícito que a ausência de `retry.ts` não é violação enquanto o serviço for stub (evita marcar como "não seguiu" algo que ainda não é aplicável).
  - Regra 9 estendida para exigir cobertura de todo status HTTP já alcançável no estado atual do código, e para forçar a revisão do teste quando novos status passarem a ser alcançáveis (evita que a suíte de testes fique "congelada" no nível de maturidade do dia em que foi escrita).
  - Regra 10 (nova): indentação de 2 espaços — o Copilot gerou os arquivos com tab, e a skill não tinha opinião sobre isso porque a Foundation skill de TypeScript ainda não existe.
  Evidência completa da rodada 1: `resolucoes/cenario-2/exercicio-2-3/teste-copilot-skill-azure-functions-endpoint-v1.md`.
