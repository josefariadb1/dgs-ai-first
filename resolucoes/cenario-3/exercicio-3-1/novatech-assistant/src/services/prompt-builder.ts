import { ValidationError } from "../shared/errors";
import { logger } from "../shared/logger";
import type { BuiltPrompt, ConversationTurn, RetrievedChunk } from "../shared/types";

const MAX_CHUNKS = 5;
const MAX_CHUNK_TOKENS = 1_500;
const MAX_HISTORY_TURNS = 3;

const SYSTEM_PROMPT = [
	"You are NovaTech Assistant.",
	"Use only information from retrieved chunks.",
	"Never invent policy details.",
	"Always cite source documents.",
].join(" ");

function estimateTokens(text: string): number {
	return Math.ceil(text.length / 4);
}

interface BuildPromptInput {
	question: string;
	chunks: RetrievedChunk[];
	history: ConversationTurn[];
}

export function buildPrompt(input: BuildPromptInput): BuiltPrompt {
	const chunks = input.chunks.slice(0, MAX_CHUNKS);
	if (input.chunks.length > MAX_CHUNKS) {
		logger.warn(
			{ requestedChunks: input.chunks.length, maxChunks: MAX_CHUNKS },
			"Chunk count exceeded budget; truncating to project limit.",
		);
	}

	for (const chunk of chunks) {
		const estimatedTokens = estimateTokens(chunk.content);
		if (estimatedTokens > MAX_CHUNK_TOKENS) {
			throw new ValidationError(
				`Chunk ${chunk.chunkId} exceeds max token budget (${MAX_CHUNK_TOKENS}).`,
			);
		}
	}

	const history = input.history.slice(-MAX_HISTORY_TURNS);
	if (input.history.length > MAX_HISTORY_TURNS) {
		logger.warn(
			{ historyTurns: input.history.length, maxHistoryTurns: MAX_HISTORY_TURNS },
			"Conversation history exceeded budget; truncating to project limit.",
		);
	}

	const chunksSection = chunks
		.map((chunk) => `[${chunk.chunkId}] (${chunk.sourceDocument}) ${chunk.content}`)
		.join("\n\n");
	const historySection = history
		.map((turn) => `${turn.role.toUpperCase()}: ${turn.content}`)
		.join("\n");

	const userPrompt = [
		"Retrieved context:",
		chunksSection,
		"Conversation history:",
		historySection || "(empty)",
		`User question: ${input.question}`,
		"Respond in Portuguese and include source names.",
	].join("\n\n");

	return {
		systemPrompt: SYSTEM_PROMPT,
		userPrompt,
		usedChunks: chunks,
		usedHistory: history,
	};
}
