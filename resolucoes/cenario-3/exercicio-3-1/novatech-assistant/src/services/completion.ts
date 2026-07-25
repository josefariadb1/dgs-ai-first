import type { BuiltPrompt, QueryResponsePayload } from "../shared/types";

export async function generateCompletion(prompt: BuiltPrompt): Promise<QueryResponsePayload> {
	const bestChunk = prompt.usedChunks[0];

	return Promise.resolve({
		answer: bestChunk.content,
		source_document: bestChunk.sourceDocument,
	});
}
