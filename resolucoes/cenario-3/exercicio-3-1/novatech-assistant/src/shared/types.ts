export type ConversationRole = "user" | "assistant";

export interface ConversationTurn {
	role: ConversationRole;
	content: string;
}

export interface QueryRequestPayload {
	question: string;
	conversationHistory?: ConversationTurn[];
}

export interface QueryResponsePayload {
	answer: string;
	source_document: string;
}

export interface RetrievedChunk {
	chunkId: string;
	sourceDocument: string;
	content: string;
	updatedAt: string;
}

export interface BuiltPrompt {
	systemPrompt: string;
	userPrompt: string;
	usedChunks: RetrievedChunk[];
	usedHistory: ConversationTurn[];
}
