import { z } from "zod";

export const queryRequestSchema = z.object({
	question: z.string().trim().min(1).max(500),
	conversationHistory: z
		.array(
			z.object({
				role: z.enum(["user", "assistant"]),
				content: z.string().trim().min(1).max(2_000),
			}),
		)
		.max(3)
		.optional(),
});

export const queryResponseSchema = z.object({
	answer: z.string().trim().min(1),
	source_document: z.string().trim().min(1),
});

export type QueryRequestInput = z.infer<typeof queryRequestSchema>;
export type QueryResponseOutput = z.infer<typeof queryResponseSchema>;
