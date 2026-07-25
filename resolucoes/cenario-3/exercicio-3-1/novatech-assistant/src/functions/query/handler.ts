import { ZodError } from "zod";

import { buildPrompt } from "../../services/prompt-builder";
import { searchRelevantChunks } from "../../services/search";
import { generateCompletion } from "../../services/completion";
import { logger } from "../../shared/logger";
import { NotFoundError, NotImplementedError, ValidationError } from "../../shared/errors";

import { buildQueryResponse } from "./response-builder";
import { queryRequestSchema } from "./validator";

interface HttpRequestLike {
  json(): Promise<unknown>;
}

interface HttpResponseLike {
  status: number;
  jsonBody: unknown;
}

function mapErrorToStatus(err: unknown): number {
  if (err instanceof ZodError || err instanceof ValidationError) {
    return 400;
  }
  if (err instanceof NotFoundError) {
    return 404;
  }
  if (err instanceof NotImplementedError) {
    return 501;
  }
  return 500;
}

function getErrorMessage(err: unknown): string {
  if (err instanceof Error) {
    return err.message;
  }
  return "Unexpected error";
}

export async function queryHandler(request: HttpRequestLike): Promise<HttpResponseLike> {
  try {
    const body = await request.json();
    const input = queryRequestSchema.parse(body);

    const chunks = await searchRelevantChunks(input.question);
    if (chunks.length === 0) {
      throw new NotFoundError("No relevant documents found for this question.");
    }

    const prompt = buildPrompt({
      question: input.question,
      chunks,
      history: input.conversationHistory ?? [],
    });

    const modelOutput = await generateCompletion(prompt);
    const response = buildQueryResponse(modelOutput);

    if (response.is_suspicious) {
      logger.warn(
        {
          question: input.question,
          sourceDocument: response.source_document,
          suspicionReason: response.suspicion_reason,
        },
        "Query response flagged by source verification.",
      );
    }

    logger.info(
      {
        question: input.question,
        sourceDocument: response.source_document,
        isSuspicious: response.is_suspicious,
      },
      "Query processed successfully.",
    );

    return {
      status: 200,
      jsonBody: response,
    };
  } catch (err) {
    logger.error({ err }, "Query request failed.");
    const status = mapErrorToStatus(err);

    return {
      status,
      jsonBody: {
        error: getErrorMessage(err),
      },
    };
  }
}
