import type { RetrievedChunk } from "../shared/types";

const STOPWORDS = new Set([
	"a",
	"ao",
	"aos",
	"as",
	"com",
	"como",
	"da",
	"das",
	"de",
	"do",
	"dos",
	"e",
	"em",
	"na",
	"nas",
	"no",
	"nos",
	"o",
	"os",
	"para",
	"por",
	"qual",
	"que",
	"se",
	"um",
	"uma",
	"cliente",
	"clientes",
]);

const KNOWLEDGE_BASE: RetrievedChunk[] = [
	{
		chunkId: "SLA-2024-B",
		sourceDocument: "SLA-2024",
		content:
			"SLAs para chamados gerais: Gold resposta em até 2h úteis e resolução em até 24h úteis. Silver resposta em até 4h úteis e resolução em até 48h úteis. Standard resposta em até 8h úteis e resolução em até 72h úteis.",
		updatedAt: "2024-01-15",
	},
	{
		chunkId: "SLA-2024-A",
		sourceDocument: "SLA-2024",
		content:
			"A NovaTech classifica clientes em três tiers: Gold, Silver e Standard. Não existem outros tiers além desses.",
		updatedAt: "2024-01-15",
	},
	{
		chunkId: "POL-001-A",
		sourceDocument: "POL-001",
		content:
			"O cliente pode solicitar devolução em até 7 dias úteis após o recebimento confirmado no tracking.",
		updatedAt: "2024-02-01",
	},
	{
		chunkId: "PROC-042-v2-B",
		sourceDocument: "PROC-042-v2",
		content:
			"Multiplicadores regionais atualizados do frete especial: Sul 1.3, Sudeste 1.1, Centro-Oeste 1.4, Nordeste 1.5 e Norte 1.8.",
		updatedAt: "2023-11-30",
	},
	{
		chunkId: "PROC-042-B",
		sourceDocument: "PROC-042",
		content:
			"Multiplicadores regionais da versão anterior: Sul 1.2, Sudeste 1.0, Centro-Oeste 1.3, Nordeste 1.4 e Norte 1.6.",
		updatedAt: "2023-06-01",
	},
	{
		chunkId: "FAQ-ATENDIMENTO-32",
		sourceDocument: "FAQ-Atendimento",
		content:
			"O FAQ de atendimento reúne dúvidas operacionais frequentes e deve ser usado apenas para orientação inicial, nunca como decisão final para temas sensíveis.",
		updatedAt: "2024-03-10",
	},
];

function tokenize(text: string): string[] {
	return text
		.normalize("NFD")
		.replace(/[\u0300-\u036f]/g, "")
		.toLowerCase()
		.split(/[^a-z0-9]+/)
		.filter((token) => token.length > 2)
		.filter((token) => !STOPWORDS.has(token));
}

function scoreChunk(questionTokens: string[], chunk: RetrievedChunk): number {
	const contentTokens = new Set(tokenize(chunk.content));
	let score = 0;
	for (const token of questionTokens) {
		if (contentTokens.has(token)) {
			score += 1;
		}
	}
	return score;
}

export async function searchRelevantChunks(question: string): Promise<RetrievedChunk[]> {
	const questionTokens = tokenize(question);
	const ranked = KNOWLEDGE_BASE.map((chunk) => ({
		chunk,
		score: scoreChunk(questionTokens, chunk),
	}))
		.filter((entry) => entry.score > 0)
		.sort((a, b) => {
			if (b.score !== a.score) {
				return b.score - a.score;
			}
			return b.chunk.updatedAt.localeCompare(a.chunk.updatedAt);
		})
		.slice(0, 5)
		.map((entry) => entry.chunk);

	return Promise.resolve(ranked);
}
