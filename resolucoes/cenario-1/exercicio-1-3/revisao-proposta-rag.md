# Revisão Crítica de uma Proposta de RAG — Exercício 1.3 (Tech Lead)

**Ferramentas usadas:** revisão humana sem IA, depois Claude (chat) como segunda opinião independente.

## Proposta em revisão (simulada, de um desenvolvedor júnior)

> Vamos usar Azure AI Search com embeddings do ada-002. Todos os documentos
> serão indexados num único índice. Chunking fixo de 512 tokens sem overlap.
> O LLM recebe os 3 chunks mais similares. Usaremos GPT-4o para geração. O
> pipeline de ingestão roda manualmente quando alguém lembra de atualizar.

---

## 1. Revisão original (humana, feita antes de consultar o Claude)

1. **Chunking fixo sem overlap.** Pode quebrar respostas na fronteira entre
   chunks e reduzir a assertividade; tende a não passar em testes de
   qualidade.
2. **Apenas os chunks mais similares, sem estrutura de contexto suficiente.**
   Perguntas multi-domínio ou conversas mais longas tendem a degradar a
   resposta.
3. **O modelo de embeddings `ada-002` está defasado** e não deveria atender
   aos critérios de qualidade do projeto.
4. **Pipeline de ingestão manual não é, de fato, um pipeline** — a definição
   de pipeline pressupõe automação. Um processo manual e sem controle cria
   risco, especialmente por ignorar uma etapa crítica de qualidade.

---

## 2. Segunda revisão (Claude)

Pedido ao Claude: "revise esta proposta de arquitetura de RAG para o projeto
NovaTech e aponte problemas." Lista obtida, organizada por tema:

1. **Chunking fixo de 512 tokens sem overlap.** Mesmo problema do item 1 da
   revisão humana — informação na borda de um chunk (ex.: a exceção de carga
   perigosa do POL-001, seção 3.2) pode ficar cortada e incompleta em ambos
   os chunks vizinhos.
2. **Chunking não é adaptado ao tipo de conteúdo.** 512 tokens fixos tratam
   igual um parágrafo de política, uma tabela de multiplicadores regionais
   com várias colunas e uma cláusula transitória — o tamanho certo de um
   chunk depende da estrutura do documento (seção, tabela inteira), não de
   uma contagem arbitrária de tokens.
3. **Top-3 chunks fixos, sem reranking e sem score mínimo.** Dois problemas
   distintos aqui: (a) três chunks podem não ser suficientes para perguntas
   que cruzam SLA + frete + devolução; (b) sem um limiar mínimo de
   similaridade, os "3 mais similares" são sempre injetados no contexto —
   mesmo quando nenhum deles é realmente relevante. Isso empurra o modelo a
   tentar responder com lixo semântico em vez de dizer "não encontrei",
   contrariando diretamente o guardrail 3 do Product Specialist.
4. **Índice único sem metadados de versionamento.** "Todos os documentos num
   único índice", sem menção a `doc_id`, versão, data de vigência ou status,
   é exatamente o anti-padrão que a
   [ADR-0003](../exercicio-1-1/ADR-0003-documentos-contraditorios.md) deste
   mesmo projeto descarta explicitamente. Com PROC-042 e PROC-042-v2 no mesmo
   índice sem diferenciação, o retrieval pode trazer os dois com peso igual e
   nenhuma forma de decidir qual vale — o cenário de mistura silenciosa de
   regras que o projeto já identificou como o pior risco.
5. **`ada-002` é um modelo de embeddings legado.** A OpenAI já oferece
   `text-embedding-3-small`/`large` (2024), com melhor qualidade de retrieval
   e menor custo por token. `GPT-4o`, usado para geração, **não** tem esse
   problema — é o modelo já recomendado no
   [ADR-0001](../exercicio-1-1/ADR-0001-escolha-modelo-llm.md) deste projeto.
6. **Ingestão manual, sem automação nem validação.** "Quando alguém lembra"
   torna impossível cumprir o requisito de disponibilizar documentos novos em
   até 24h (input do Product Specialist no ADR-0001) e reproduz exatamente o
   problema que o projeto existe para resolver: informação desatualizada
   resolvida informalmente.
7. **Nenhuma menção a testes ou guardrails antes do go-live.** A proposta
   descreve só o caminho feliz técnico (embeddings → índice → retrieval →
   geração); não há citação obrigatória, checagem determinística de fonte,
   nem suíte de teste de retrieval/prompt antes de produção.
8. **Nenhuma observabilidade do pipeline.** Sem logging de score de
   similaridade, taxa de respostas "não encontrei" ou amostragem para QA, não
   há como detectar degradação de qualidade ao longo do tempo.

---

## 3. Comparação honesta: humano vs. Claude

| # | Problema | Quem encontrou | Observação |
|---|---|---|---|
| 1 | Chunking fixo sem overlap | **Ambos** | Convergência total — é o problema mais óbvio da proposta. |
| 2 | Chunking não adaptado ao tipo de conteúdo (tabelas, seções) | **Só Claude** | O humano tratou "chunking" como um problema só (overlap); Claude separou um segundo problema de chunking que o exercício de análise técnica do Desenvolvedor ([Exercício 1.1](../exercicio-1-1/)) já havia levantado para este projeto. |
| 3a | Top-K fixo insuficiente para perguntas multi-domínio | **Ambos** | O humano identificou isso dentro do item 2 da sua lista. |
| 3b | Ausência de score mínimo de similaridade (retrieval "sempre injeta 3 chunks") | **Só Claude** | Refinamento mais técnico do mesmo problema — o humano viu o sintoma (degradação), Claude achou uma causa raiz adicional e mais específica (falta de threshold), que conecta diretamente com o guardrail "dizer que não encontrou" do Product Specialist. |
| 3c | Context rot em conversas longas no Teams | **Só humano** | Boa captura independente: a proposta não menciona histórico de conversa em nenhum momento — o humano inferiu esse risco a partir do contexto do projeto (bot multi-turno no Teams), algo que o Claude não priorizou na primeira passada por não estar explícito no texto da proposta. |
| 4 | Índice único sem metadados de versionamento/vigência | **Só Claude** | O humano não mencionou isso. É um dos problemas mais graves da proposta porque contradiz uma decisão já tomada (ADR-0003) neste mesmo projeto. |
| 5 | `ada-002` é um modelo de embeddings legado | **Ambos** | Convergência total, e num ponto fácil de confundir com o modelo de geração (GPT-4o) — a resposta do humano já havia sido esclarecida como referindo-se especificamente ao `ada-002` antes da comparação. |
| 6 | Ingestão manual sem automação | **Ambos** | Convergência total; Claude acrescentou o vínculo direto com o SLA de 24h já definido pelo Product Specialist. |
| 7 | Ausência de testes/guardrails antes do go-live | **Só Claude** | O humano focou em riscos de dados/arquitetura; Claude trouxe a dimensão de processo/qualidade (nada na proposta garante que ela vai ser validada antes de ir ao ar). |
| 8 | Ausência de observabilidade | **Só Claude** | Achado secundário — importante, mas o menos crítico dos oito. |

**Honestidade da comparação:** o Claude encontrou mais problemas técnicos
específicos (4, 7, 8) porque tem acesso explícito às ADRs e ao restante da
documentação do projeto para cruzar contra a proposta. O humano, por outro
lado, fez uma captura que o Claude não fez na primeira passada — o risco de
*context rot* em sessões longas — porque isso exige inferir uma limitação
não mencionada no texto da proposta (como o pipeline vai lidar com múltiplas
perguntas na mesma sessão do Teams), o que é mais um exercício de imaginar
cenários de uso do que de checar a proposta contra documentos. No problema 5,
as duas revisões convergiram no mesmo ponto (o `ada-002`, não o GPT-4o, é o
modelo defasado) — um risco real dessa proposta é justamente confundir os
dois modelos citados no texto, e vale registrar que essa ambiguidade existiu
e foi verificada antes de consolidar a comparação.

---

## 4. Alternativas propostas para cada problema

| # | Problema | Alternativa proposta |
|---|---|---|
| 1 | Chunking fixo sem overlap | Chunking por seção/estrutura do documento (não por contagem fixa de tokens), com overlap de ~10-15% entre chunks adjacentes — mesma recomendação já usada na análise técnica do Desenvolvedor (Exercício 1.1). |
| 2 | Chunking não adaptado ao conteúdo | Regra de chunking diferenciada por tipo: parágrafos de política por seção; tabelas mantidas inteiras num único chunk (ou divididas por linha lógica, nunca no meio de uma linha); cláusulas transitórias sempre no mesmo chunk que a regra a que se referem. |
| 3a | Top-3 fixo insuficiente para multi-domínio | Retrieval em duas fases: busca ampla (15-20 candidatos) seguida de reranking para 5-8 chunks; para perguntas que cruzam temas, decompor a pergunta e buscar por subtema antes de montar o contexto (mesma decisão do [ADR-0002](../exercicio-1-1/ADR-0002-gerenciamento-contexto.md)). |
| 3b | Sem score mínimo de similaridade | Definir um limiar de corte: abaixo dele, nenhum chunk é injetado e o orquestrador aciona a resposta de fallback ("não encontrei") **antes** de chamar o LLM, sem depender do modelo perceber que os chunks são ruins. |
| 3c | Context rot em sessões longas no Teams | Tratar cada pergunta como uma consulta RAG essencialmente stateless: re-recuperar chunks a cada pergunta, manter só uma janela curta do histórico recente (ou um resumo), nunca acumular a sessão inteira no contexto. |
| 4 | Índice único sem metadados de versionamento | Manter um único índice tecnicamente, mas com metadados obrigatórios por documento na ingestão: `doc_id`, `versao`, `data_vigencia`, `status` (`vigente`/`substituido`/`transitorio`); o orquestrador detecta conflito quando dois chunks do mesmo `doc_id` com versões diferentes são recuperados juntos. |
| 5 | `ada-002` legado | Migrar para `text-embedding-3-large` (ou `-small`, se custo for mais restritivo) via Azure OpenAI — troca de configuração, não de arquitetura. Manter GPT-4o para geração, já validado no ADR-0001. |
| 6 | Ingestão manual | Pipeline de ingestão automatizado e agendado (job diário + gatilho de atualização do SharePoint/Confluence), com validação de sucesso/falha e alerta em caso de erro, para cumprir o SLA de 24h. |
| 7 | Sem testes/guardrails antes do go-live | Suíte mínima de testes de retrieval (contra um gabarito de perguntas de referência) e de prompt (citação obrigatória, checagem de fonte real, idioma) rodando em CI antes de qualquer versão ir a produção — mesmo padrão definido no [Exercício 1.2](../exercicio-1-2/estrategia-prompt-engineering.md). |
| 8 | Sem observabilidade | Logar, por query: score de similaridade dos chunks recuperados, se a resposta foi "não encontrei", e latência — dados suficientes para o QA amostrar periodicamente sem instrumentação sofisticada. |

---

## 5. Proposta reescrita

> Vamos usar **Azure AI Search** como vector store, com um único índice
> contendo metadados obrigatórios por documento (`doc_id`, `versao`,
> `data_vigencia`, `status`). Embeddings gerados com
> **text-embedding-3-large** via Azure OpenAI (substituindo o `ada-002`
> legado). O **chunking segue a estrutura do documento** (por seção, com
> tabelas mantidas inteiras), não uma contagem fixa de tokens, com **overlap
> de ~10-15%** entre chunks adjacentes.
>
> O retrieval roda em duas fases: busca ampla dos 15-20 chunks mais
> similares, seguida de **reranking** para selecionar os 5-8 mais relevantes.
> Um **score mínimo de similaridade** define quando nenhum chunk é
> injetado — nesse caso, o orquestrador responde "não encontrei" sem chamar o
> LLM. Perguntas que cruzam múltiplos temas (ex.: frete + devolução) são
> **decompostas por subtema** antes do retrieval. Quando dois chunks do
> mesmo `doc_id` com versões diferentes são recuperados juntos, o
> orquestrador marca a query como "em conflito" para o prompt apresentar
> ambas as versões.
>
> Sessões multi-turno no Teams tratam cada pergunta como uma consulta RAG
> essencialmente stateless, com apenas uma **janela curta do histórico
> recente** incluída no contexto — evitando degradação em conversas longas.
>
> A geração usa **GPT-4o** via Azure OpenAI (mantido do plano original,
> condicionado ao teste de fidelidade às fontes já previsto no ADR-0001).
>
> A ingestão roda como **pipeline automatizado e agendado** (job diário +
> gatilho de atualização do SharePoint/Confluence), com validação de
> sucesso/falha e alerta, garantindo a disponibilização de documentos novos
> em até 24h.
>
> Antes do go-live, uma **suíte mínima de testes** (retrieval contra um
> gabarito de perguntas de referência, e prompt com checagem de citação,
> fonte real e idioma) precisa passar em CI.

Nada aqui introduz um componente ou fornecedor novo em relação à proposta
original ou ao [ADR-0004](../exercicio-1-1/ADR-0004-build-vs-buy-rag.md)
(continua Azure AI Search + Azure OpenAI) — as mudanças são de configuração
(modelo de embedding), de lógica de orquestração (rerank, threshold,
metadados, automação da ingestão) e de processo (testes antes do go-live),
não de arquitetura. Isso evita o overengineering de, por exemplo, propor um
vector store adicional ou um serviço de observabilidade dedicado para um MVP
de 3 meses.

---

## Reflexão: IA como par de revisão, não substituto do julgamento

O valor do Claude aqui não foi só "encontrar mais problemas" — foi **cruzar a
proposta contra decisões já tomadas no projeto** (ADR-0002, ADR-0003) que um
desenvolvedor júnior — ou um revisor sem o histórico completo do projeto —
não teria como saber de cor (itens 4, 7 e 8, que o humano não mencionou). Ao
mesmo tempo, o humano capturou um risco (*context rot* em sessões longas) que
exigia imaginar um cenário de uso não descrito na proposta, e que o Claude
não priorizou na primeira passada. No ponto do modelo defasado (item 5), o
texto original da revisão humana citava só "o modelo escolhido", o que é
ambíguo entre `ada-002` (embeddings) e GPT-4o (geração) — só um dos dois é
de fato legado. Confirmado com o autor que a intenção sempre foi o `ada-002`,
a revisão humana estava certa; o próprio fato de a formulação ter permitido
essa leitura ambígua é, em si, um lembrete de por que a segunda revisão
existe: força a explicitar qual afirmação exatamente está sendo feita.
Nenhuma das duas revisões sozinha seria suficiente; a combinação foi.
