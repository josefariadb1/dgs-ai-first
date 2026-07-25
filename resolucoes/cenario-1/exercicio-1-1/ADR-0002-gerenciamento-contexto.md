# ADR-0002: Estratégia de gerenciamento de contexto do pipeline de RAG

## Status
Proposto

## Contexto

A qualidade da resposta de um LLM não depende só do modelo, mas do **contexto que ele
recebe a cada query**. A base da NovaTech é grande (~12M tokens estimados pelo
desenvolvedor) e o assistente roda como bot no Teams, onde o atendente pode fazer
**várias perguntas na mesma sessão**. Forças que atuam:

- **Orçamento de atenção limitado.** Mesmo com uma janela de contexto grande (ex.:
  128K tokens), encher o contexto **degrada** a qualidade. "Maior não é melhor": mais
  texto irrelevante compete por atenção e aumenta custo/latência.
- **Lost in the middle.** Informação no meio de um contexto longo é processada com
  menos peso do que a do início e do fim.
- **Context rot em sessões longas.** Em conversas com muitas perguntas seguidas, o
  histórico acumulado passa a "abafar" os chunks novos, e respostas posteriores
  ignoram o material recuperado em favor de repetir o histórico.
- **Perguntas multi-domínio.** Algumas perguntas cruzam SLA + frete + devolução; uma
  única busca por similaridade pode trazer chunks fortes de um tema e nenhum de outro.
- **Context overflow.** Pergunta + chunks + system prompt + histórico podem exceder o
  orçamento e causar truncamento silencioso.

## Decisão

Definir um **orçamento de contexto explícito e gerenciado**, em vez de "encher a
janela":

1. **Orçamento-alvo de trabalho ≈ 16K tokens por query** (não os 128K disponíveis),
   distribuído em: system prompt + guardrails (~2K, estático), metadados do cliente
   (~0,2K), **chunks recuperados (~4–5K)**, pergunta (~0,2K) e histórico controlado
   (~2–3K). Sobra de janela é margem de segurança, não espaço a ser preenchido.
2. **Retrieval em duas fases, opcional e ativado por flag:** o MVP sobe com **top-K
   simples** — os 5–8 chunks mais similares direto do vector store, sem segunda fase.
   Buscar top-K amplo (ex.: 15–20 candidatos) e **reordenar (rerank)** antes de
   selecionar os 5–8 chunks finais de ~500 tokens é uma capacidade que existe desde já
   na arquitetura, mas só é **ativada por flag** quando os testes de retrieval do QA
   mostrarem necessidade (ex.: precisão baixa em perguntas ambíguas). Só os chunks
   finais (reordenados ou não) entram no contexto.
3. **Posicionamento contra lost-in-the-middle:** colocar os chunks de maior relevância
   nas **extremidades** do bloco de contexto (mais relevante primeiro e último), e
   manter o bloco pequeno o suficiente para que o "meio" seja curto.
4. **Perguntas multi-domínio, também por flag:** detectar/decompor a pergunta em
   subtemas e fazer **retrieval por subtema** (multi-query), garantindo cobertura
   mínima de cada domínio antes de montar o contexto, em vez de confiar numa única
   busca. Como o rerank do item 2, entra quando os testes do QA mostrarem perguntas
   multi-domínio (SLA + frete + devolução na mesma pergunta) falhando com busca única
   — não é requisito do MVP.
5. **Sessões longas no Teams — combate ao context rot:** tratar cada pergunta como uma
   **query RAG essencialmente stateless**: re-recuperar chunks a cada pergunta e **não
   acumular** todo o histórico. Manter apenas uma janela curta das últimas N trocas e,
   se necessário, um **resumo** da sessão. Oferecer/forçar "novo assunto" que limpa o
   histórico.
6. **Proteção contra overflow:** antes de chamar o LLM, **medir os tokens** do contexto
   montado e, se exceder o orçamento, cortar primeiro o histórico, depois reduzir o
   número de chunks — nunca truncar cego.

## Consequências

**Positivas**
- Respostas mais consistentes e mais baratas: menos tokens, menos ruído competindo por
  atenção.
- Robustez a sessões longas — a 5ª pergunta recebe o mesmo cuidado de retrieval que a 1ª.
- Cobertura de perguntas que cruzam SLA + frete + devolução.
- Overflow vira um caso tratado, não uma falha silenciosa.

**Negativas / riscos**
- Rerank e multi-query adicionam **latência e custo** por query (etapas extras).
- Decompor perguntas e resumir histórico introduz **componentes que também podem
  errar** e precisam de teste (responsabilidade do QA).
- O orçamento de 16K é uma hipótese inicial que **precisa ser calibrada** com dados
  reais (tamanho médio de chunk, taxa de acerto do retrieval).

## Alternativas consideradas

- **"Stuff" — jogar muitos chunks / quase a janela inteira no contexto.** Descartado:
  é exatamente o que causa context rot, lost-in-the-middle e custo alto. Simplicidade
  aparente, qualidade pior.
- **Janela de contexto enorme como solução (depender de um modelo de 1M tokens).**
  Descartado: janela grande não corrige relevância nem posicionamento; só adia o
  problema e aumenta o custo.
- **Manter todo o histórico da sessão no contexto.** Descartado: degrada respostas
  tardias na sessão (context rot) e estoura o orçamento. Substituído por janela curta +
  resumo + re-retrieval.

## Contra-argumentos (Devil's Advocate) e respostas

- *"Limitar a 16K com uma janela de 128K é desperdício."* — A janela é um teto físico,
  não uma meta. O recurso escasso é a **atenção do modelo**, não os tokens disponíveis.
  Encher a janela troca custo por **pior** qualidade.
- *"Rerank e multi-query são overengineering para um MVP."* — São opcionais por flag.
  O MVP pode subir com top-K simples; rerank/multi-query entram quando os testes de
  retrieval (QA) mostrarem perguntas multi-domínio falhando. A arquitetura prevê o
  ponto de extensão desde já.
- *"Tratar cada pergunta como stateless quebra perguntas de follow-up ('e para o
  Sudeste?')."* — Por isso mantemos uma **janela curta** de histórico e/ou um resumo,
  não zero histórico. O objetivo é evitar acúmulo ilimitado, não eliminar contexto
  conversacional útil.

## Histórico de iterações

- **Iteração 0 — Criação:** orçamento de ~16K tokens definido; a versão inicial descrevia
  retrieval em duas fases (top-K amplo + rerank) e decomposição multi-query como parte
  do pipeline **desde o MVP**; sessões longas no Teams eram tratadas como "cada pergunta
  é totalmente stateless, sem qualquer histórico acumulado".
- **Iteração 1 — Devil's advocate**, dois ajustes concretos na Decisão:
  - *"Rerank e multi-query são overengineering para um MVP"* levou a tornar os dois
    **opcionais, ativados por flag** (itens 2 e 4), entrando só quando os testes de
    retrieval do QA mostrarem necessidade — deixaram de ser requisito do MVP, viraram
    ponto de extensão já previsto na arquitetura.
  - *"Tratar cada pergunta como stateless quebra follow-up"* levou a substituir "zero
    histórico" por uma **janela curta das últimas N trocas e/ou um resumo da sessão**
    (item 5) — o re-retrieval a cada pergunta continua (combate ao context rot), mas
    sem eliminar todo o contexto conversacional útil.
