const validSourceDocuments = [
  "POL-001",
  "PROC-042",
  "PROC-042-v2",
  "SLA-2024",
  "FAQ-Atendimento",
] as const;

const sourceDocumentLookup = new Map(
  validSourceDocuments.map((documentId) => [documentId.toLowerCase(), documentId]),
);

export type ValidSourceDocument = (typeof validSourceDocuments)[number];

export interface ModelResponseWithSource {
  source_document?: string | null;
  [key: string]: unknown;
}

export interface SourceVerificationResult extends ModelResponseWithSource {
  isSuspicious: boolean;
  suspicionReason: "missing_source_document" | "invalid_source_document" | null;
  normalizedSourceDocument: ValidSourceDocument | null;
}

export function verifySourceDocument(
  response: ModelResponseWithSource,
): SourceVerificationResult {
  const rawSourceDocument =
    typeof response.source_document === "string"
      ? response.source_document.trim()
      : "";

  if (!rawSourceDocument) {
    return {
      ...response,
      isSuspicious: true,
      suspicionReason: "missing_source_document",
      normalizedSourceDocument: null,
    };
  }

  const normalizedSourceDocument =
    sourceDocumentLookup.get(rawSourceDocument.toLowerCase()) ?? null;

  if (!normalizedSourceDocument) {
    return {
      ...response,
      isSuspicious: true,
      suspicionReason: "invalid_source_document",
      normalizedSourceDocument: null,
    };
  }

  return {
    ...response,
    source_document: normalizedSourceDocument,
    isSuspicious: false,
    suspicionReason: null,
    normalizedSourceDocument,
  };
}

export { validSourceDocuments };