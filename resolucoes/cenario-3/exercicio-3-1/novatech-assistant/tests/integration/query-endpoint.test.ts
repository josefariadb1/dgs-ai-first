import { describe, expect, it } from "vitest";

import { queryHandler } from "../../src/functions/query/handler";

interface MockRequest {
  json(): Promise<unknown>;
}

function createRequest(payload: unknown): MockRequest {
  return {
    json: async () => payload,
  };
}

describe("query endpoint", () => {
  it("returns an answer and a verified source document for a known query", async () => {
    const request = createRequest({
      question: "Qual o SLA do cliente Gold?",
      conversationHistory: [],
    });

    const response = await queryHandler(request);

    expect(response.status).toBe(200);
    const typedBody = response.jsonBody as {
      answer: string;
      source_document: string;
      is_suspicious: boolean;
      suspicion_reason: string | null;
    };

    expect(typedBody.source_document).toBe("SLA-2024");
    expect(typedBody.is_suspicious).toBe(false);
    expect(typedBody.suspicion_reason).toBeNull();
    expect(typedBody.answer).toContain("Gold");
    expect(typedBody.answer).toContain("24h úteis");
  });
});