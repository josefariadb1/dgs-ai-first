# ADR-0004: Build vs. Buy para o pipeline de RAG

## Status
Proposto

## Contexto

Precisamos decidir como construir o pipeline de RAG (extração → chunking → embeddings →
vector store → retrieval → geração) que sustenta o assistente. Forças:

- **A NovaTech já tem Azure** (Microsoft 365 E3 + disposição para Azure AI Services) e a
  entrega final é **em Teams + SharePoint**. Conectores nativos de SharePoint, autenticação
  Entra ID e residência de dados já resolvidos são um peso grande.
- **Prazo curto:** 3 meses para discovery + desenvolvimento + go-live.
- **Capacidade operacional enxuta:** não há time dedicado de MLOps para sustentar
  infraestrutura própria 24/7.
- **Fontes heterogêneas:** PDFs com tabelas complexas, ~15% escaneados (OCR), wiki com
  links/macros, planilhas com fórmulas. A extração é o maior desafio técnico.
- **Necessidade de controle** sobre chunking, versionamento de documentos e
  gerenciamento de contexto — pontos onde está o maior risco do projeto e que exigem
  lógica própria, não configuração de caixa-preta.

## Decisão

Adotar uma abordagem **managed-first**: usar **Azure AI Search** (indexação, busca
vetorial + semantic ranking, indexer nativo de SharePoint) como vector store/retriever e
**Azure OpenAI** para embeddings e geração.

Manter, porém, uma **fina camada de orquestração própria** (no nosso código) responsável
por: estratégia de chunking, atribuição de metadados de versão/vigência, montagem e
orçamento de contexto, rerank/multi-query e detecção de conflito. O acesso ao vector
store/retriever fica **isolado atrás de uma interface estável** nessa camada — para que
o Azure AI Search possa ser **substituído sem reescrever o resto do pipeline**, caso os
testes de retrieval do QA (contra o gabarito do Anexo B) mostrem qualidade insuficiente.
Ou seja: **comprar a infraestrutura, construir a lógica de negócio — e deixar a
infraestrutura trocável no ponto certo.**

## Consequências

**Positivas**
- **Time-to-go-live** compatível com 3 meses: o indexer de SharePoint, a busca vetorial
  gerenciada e a integração com Teams reduzem trabalho de plataforma.
- **Operação gerenciada:** escalabilidade, disponibilidade e segurança ficam com a
  Azure, não com o time.
- **Governança e compliance** dentro do tenant já contratado.
- A camada de orquestração própria preserva o **controle sobre chunking, versionamento e
  contexto** — exatamente onde está o valor e o risco do projeto.

**Negativas / riscos**
- **Lock-in** mais forte na Azure (parcialmente mitigado por isolar a lógica de negócio
  na nossa camada e usar interfaces estáveis).
- **Menos controle de baixo nível** sobre o algoritmo de retrieval do que num stack
  open-source.
- **Custos gerenciados recorrentes** (tier do Azure AI Search, OCR/Document Intelligence
  para escaneados) que precisam ser dimensionados.
- A extração de PDFs complexos/escaneados **não é resolvida de graça** pelo serviço —
  exigirá Azure AI Document Intelligence e validação de qualidade.

## Alternativas consideradas

- **Build full open-source (LangChain/LlamaIndex + ChromaDB/FAISS + embeddings
  self-hosted).** Máximo controle e sem custo de licença de plataforma. Descartado para
  o MVP: sem conector nativo de SharePoint, exige infra e operação próprias, é mais lento
  para o go-live e não aproveita o investimento Azure já existente. **Recomendado para a
  PoC/prototipagem local** (validar chunking e retrieval barato antes de provisionar
  Azure), e reavaliável se custo ou necessidade de controle crescerem.
- **Buy "puro" / solução SaaS de chat-sobre-documentos pronta (caixa-preta).**
  Descartado: tira justamente o controle de versionamento e gerenciamento de contexto que
  são críticos aqui, além de levantar questões de residência de dados.
- **Híbrido invertido (vector store open-source + geração Azure).** Viável tecnicamente,
  mas perde o indexer nativo de SharePoint e o semantic ranking gerenciado sem ganho
  proporcional para este caso.

## Contra-argumentos (Devil's Advocate) e respostas

- *"Managed = lock-in caro e perda de controle."* — Por isso a lógica de negócio
  (chunking, versionamento, contexto) fica **no nosso código**, não na configuração do
  serviço. Trocamos infraestrutura, não a inteligência do pipeline. E no volume estimado
  do projeto (~4.000–4.500 consultas/mês) o custo gerenciado é modesto frente ao custo de
  operar infra própria.
- *"O desenvolvedor já provou um pipeline open-source na PoC; por que não levá-lo a
  produção?"* — A PoC é o caminho certo para **validar barato** (e a recomendamos), mas
  produção exige conectores de SharePoint, OCR, segurança e operação que o open-source não
  entrega prontos no prazo. Decisão de PoC ≠ decisão de produção.
- *"E se a qualidade do retrieval gerenciado for pior?"* — A camada de orquestração nos
  permite medir (testes de retrieval do QA contra o gabarito do Anexo B) e, se necessário,
  substituir o componente de busca sem reescrever o resto. A decisão é reversível no ponto
  certo.
- *"OCR e tabelas complexas vão custar caro de qualquer forma."* — Verdade, e isso vale
  para build **ou** buy. Não é argumento a favor do open-source; é um custo do domínio que
  o managed ao menos entrega como serviço testado (Document Intelligence).

## Histórico de iterações

- **Iteração 0 — Criação:** decisão managed-first (Azure AI Search + Azure OpenAI) com
  camada de orquestração própria para chunking, versionamento e contexto; a versão
  inicial não especificava como o time reagiria se a qualidade do retrieval gerenciado
  se mostrasse insuficiente — o vector store estava implicitamente fixado ao Azure AI
  Search.
- **Iteração 1 — Devil's advocate:** *"E se a qualidade do retrieval gerenciado for
  pior?"* levou a explicitar, na própria Decisão, que o acesso ao vector store/retriever
  fica **isolado atrás de uma interface estável** na camada de orquestração — permitindo
  substituir o Azure AI Search sem reescrever o resto do pipeline, com o gatilho sendo os
  testes de retrieval do QA contra o gabarito do Anexo B. A decisão managed-first deixou
  de ser apresentada como definitiva e passou a ser **reversível no ponto certo**.
