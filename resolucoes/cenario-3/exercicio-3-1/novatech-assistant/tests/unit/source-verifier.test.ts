import { describe, expect, it } from "vitest";

import { verifySourceDocument } from "../../src/services/source-verifier";

describe("verifySourceDocument", () => {
  it("accepts a valid NovaTech source identifier", () => {
    const result = verifySourceDocument({
      answer: "Prazo de devolução em até 7 dias úteis.",
      source_document: "POL-001",
    });

    expect(result.isSuspicious).toBe(false);
    expect(result.suspicionReason).toBeNull();
    expect(result.normalizedSourceDocument).toBe("POL-001");
  });

  it("marks the response as suspicious when the source is missing", () => {
    const result = verifySourceDocument({
      answer: "Resposta sem fonte.",
    });

    expect(result.isSuspicious).toBe(true);
    expect(result.suspicionReason).toBe("missing_source_document");
    expect(result.normalizedSourceDocument).toBeNull();
  });

  it("marks the response as suspicious when the source is not in the allowlist", () => {
    const result = verifySourceDocument({
      answer: "Resposta com fonte inválida.",
      source_document: "POL-999",
    });

    expect(result.isSuspicious).toBe(true);
    expect(result.suspicionReason).toBe("invalid_source_document");
    expect(result.normalizedSourceDocument).toBeNull();
  });

  it("normalizes a source citation with different casing and surrounding whitespace", () => {
    const result = verifySourceDocument({
      answer: "Resposta com fonte em formato diferente do identificador curto.",
      source_document: "  pol-001  ",
    });

    expect(result.isSuspicious).toBe(false);
    expect(result.suspicionReason).toBeNull();
    expect(result.normalizedSourceDocument).toBe("POL-001");
    expect(result.source_document).toBe("POL-001");
  });
});