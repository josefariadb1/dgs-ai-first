import { ValidationError } from "../../shared/errors";
import { verifySourceDocument } from "../../services/source-verifier";

import { queryResponseSchema, type QueryResponseOutput } from "./validator";

export interface QueryResponseBody extends QueryResponseOutput {
	is_suspicious: boolean;
	suspicion_reason: "missing_source_document" | "invalid_source_document" | null;
}

export function buildQueryResponse(modelOutput: unknown): QueryResponseBody {
	const parsedResponse = queryResponseSchema.safeParse(modelOutput);
	if (!parsedResponse.success) {
		throw new ValidationError(parsedResponse.error.issues.map((issue) => issue.message).join("; "));
	}

	const verification = verifySourceDocument(parsedResponse.data);

	return {
		answer: parsedResponse.data.answer,
		source_document: verification.normalizedSourceDocument ?? parsedResponse.data.source_document,
		is_suspicious: verification.isSuspicious,
		suspicion_reason: verification.suspicionReason,
	};
}
