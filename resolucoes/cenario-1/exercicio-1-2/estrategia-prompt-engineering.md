# Estratégia de Prompt Engineering e Context Engineering — Assistente de Atendimento NovaTech

**Status:** Proposto (v1 do artefato)
**Autor:** Tech Lead · **Ferramentas usadas:** Claude (chat) para as seções 1, 2 e 4 · GitHub Copilot para o script de teste automatizado (ver seção 3 — gerado à parte, fora deste documento)
**Relacionado a:** [ADR-0001](../exercicio-1-1/ADR-0001-escolha-modelo-llm.md) (modelo), [ADR-0002](../exercicio-1-1/ADR-0002-gerenciamento-contexto.md) (orçamento de contexto), [ADR-0003](../exercicio-1-1/ADR-0003-documentos-contraditorios.md) (documentos contraditórios)

## Por que este documento existe

O prompt do assistente não é um texto informal que "alguém ajusta quando a
resposta sai errada". Ele é a peça de código que carrega os guardrails de
negócio (citar fonte, não inventar, tratar contradição) e, como qualquer
código de produção, precisa de versionamento, dono, revisão e testes de
regressão. Este documento define como isso funciona na prática, mais a
anatomia completa do contexto que o LLM recebe a cada query e a divisão entre
o que é responsabilidade do prompt (probabilístico) e o que é responsabilidade
do código ao redor dele (determinístico).

---

## 1. Onde e como os prompts são versionados

### 1.1 Estrutura no repositório

```
prompts/
  system/
    system-prompt.v1.md        # histórico — nunca editado após ser substituído
    system-prompt.v2.md        # vigente
  CHANGELOG.md                 # motivo de cada versão, ligado a um caso de teste
  tests/
    test_prompt_scenarios.*    # suíte de regressão gerada com o Copilot (seção 3)
```

Reproduzido neste exercício em [`prompts/`](prompts/) com `system-prompt.v1.md`
(baseline fornecida) e `system-prompt.v2.md` (versão revisada nesta entrega). O
script de teste em si é entregue como artefato separado (seção 3).

### 1.2 Nomenclatura e ciclo de vida

- Um arquivo por versão (`system-prompt.vN.md`), nunca editado in-place depois
  de publicado — mudança de conteúdo sempre gera uma nova versão. Isso dá o
  mesmo benefício de imutabilidade que uma tag de release em código.
- A versão **vigente** é referenciada por **configuração**
  (`PROMPT_VERSION=v2`), não por um caminho fixo no código da aplicação — o
  mesmo padrão já adotado para a versão do modelo no
  [ADR-0001](../exercicio-1-1/ADR-0001-escolha-modelo-llm.md). Trocar de
  versão (inclusive fazer rollback) é uma mudança de configuração, não um
  deploy de código.
- Cada versão carrega front-matter (`status: vigente | substituido`,
  `aprovadores`, `substitui`) para que a árvore de versões seja auditável sem
  depender só do `git log`.

### 1.3 Como são testados

- Nenhuma versão nova de prompt é promovida a `vigente` sem passar pela suíte
  de testes automatizados (seção 3) rodando contra o **mapa de cobertura do
  Anexo B** (pergunta → chunks esperados) como gabarito.
- O CI roda a suíte em dois momentos: (a) em todo PR que altera um arquivo em
  `prompts/**`, e (b) como teste de regressão sempre que um documento-fonte
  muda de forma que afete metadados de vigência (conecta com o teste de
  regressão do plano de testes do QA).
- Os testes automatizados cobrem apenas a parte **determinística** do
  guardrail (citação presente? termo proibido ausente? formato correto?). A
  qualidade de conteúdo (a resposta está factualmente certa?) continua
  dependendo de amostragem humana com a rubrica do QA — um script não
  substitui esse julgamento, só barra regressões óbvias antes que cheguem lá.

### 1.4 Quem pode alterar

- Qualquer desenvolvedor pode **propor** uma mudança de prompt via PR.
- Merge exige aprovação de **duas partes**, porque um prompt mistura dois
  tipos de decisão diferentes:
  - **Tech Lead** — aprova mudanças que afetam estrutura, orçamento de
    contexto, ou a forma como o prompt se relaciona com os guardrails
    determinísticos (seção 4).
  - **Product Specialist** — aprova mudanças de guardrail de negócio (o que
    conta como "resposta aceitável", como tratar contradição, o que é
    fallback correto), porque isso é requisito de produto, não detalhe
    técnico.
- Isso evita o anti-padrão mais comum em projetos de IA: um desenvolvedor
  "ajusta o prompt" isoladamente para corrigir um caso pontual e
  silenciosamente muda uma regra de negócio que não era dele para decidir.

---

## 2. Anatomia do contexto de uma query

Uma query real ao assistente não é "o prompt" — é a composição de cinco
partes, algumas estáticas e outras dinâmicas, montadas pelo orquestrador a
cada pergunta.

| # | Parte | Estático / Dinâmico | Conteúdo | Tamanho estimado | Cresce durante a sessão? |
|---|-------|----------------------|----------|-------------------|---------------------------|
| 1 | System prompt + guardrails | **Estático** (só muda por nova versão publicada) | Identidade, regras, formato de resposta, instruções de uso dos chunks — `system-prompt.v2.md` | **~700 tokens** | Não |
| 2 | Metadados do cliente | Dinâmico (varia por chamado, tamanho fixo) | Tier (Gold/Silver/Standard), canal, `chamado_id`, região | **~80 tokens** | Não |
| 3 | Chunks recuperados | Dinâmico (varia por pergunta) | 5–8 chunks pós-rerank, ~500 tokens cada, com metadado `doc_id`/`versao`/`status` | **~4.000–5.000 tokens** | Não (top-K é um teto fixo, não acumula) |
| 4 | Pergunta do atendente | Dinâmico | Texto livre da pergunta atual | **~30 tokens** | Não |
| 5 | Histórico da sessão (Teams) | Dinâmico e **crescente** | Últimas N trocas + resumo, para suportar follow-up ("e para o Sudeste?") | **0 na 1ª pergunta → até ~2.500 tokens** (janela curta com teto, por [ADR-0002](../exercicio-1-1/ADR-0002-gerenciamento-contexto.md)) | **Sim, até o teto — depois disso o mais antigo é descartado, nunca o system prompt** |
| | **Total por query (orçamento-alvo)** | | | **~5.000–8.500 tokens**, dentro do teto de **~16K** definido no ADR-0002 | |

Notas sobre a anatomia:

- **Só a parte 5 cresce.** Isso é o ponto de maior risco de *context rot* em
  conversas longas no Teams: se ela crescer sem teto, eventualmente compete
  com os chunks recuperados pela atenção do modelo e a 5ª ou 6ª pergunta da
  sessão passa a ser respondida com base no histórico velho em vez dos chunks
  novos. Por isso o histórico tem orçamento próprio e fixo, independente do
  orçamento total — quando o teto é atingido, corta-se o histórico antes de
  cortar qualquer outra parte.
- **Ordem de montagem defende contra *lost in the middle*.** O bloco de
  chunks (a parte mais decisiva para a resposta) é posicionado **logo após**
  o system prompt e **antes** do histórico — nas extremidades do contexto, não
  no meio dele. O histórico (a parte menos crítica quando existe conflito com
  os chunks) fica no meio; a pergunta atual, no final. Dentro do próprio bloco
  de chunks, os 1–2 chunks de maior score de relevância são repetidos como
  primeiro e último do bloco quando o bloco tiver mais de 4 chunks — um "sanduíche"
  de relevância para os casos de contexto mais longo.
- **Overflow é tratado explicitamente, nunca por truncamento silencioso.**
  Antes de chamar o LLM, o orquestrador mede tokens reais (via o tokenizer do
  fornecedor, encapsulado atrás da interface definida no ADR-0001) e, se o
  total ultrapassar o orçamento-alvo, corta primeiro o histórico (parte 5),
  depois reduz o número de chunks (parte 3) — nunca corta o system prompt
  (parte 1) nem a pergunta atual (parte 4).
- **128K de janela ≠ 16K de orçamento-alvo.** A janela do modelo (ADR-0001) é
  o teto físico; o orçamento-alvo de ~16K é uma escolha de engenharia para não
  degradar a qualidade enchendo a janela com texto de baixa relevância — a
  mesma lógica de "orçamento de atenção" do ADR-0002.

---

## 3. Script de teste automatizado

O script de teste é gerado com o **GitHub Copilot** e entregue como artefato
separado deste documento (fora do escopo desta v1 do texto de estratégia). Ele
deve seguir o contrato abaixo, para que qualquer implementação do script seja
compatível com o resto desta estratégia:

- **Entrada:** um prompt versionado (`system-prompt.v1.md` / `v2.md`), um
  conjunto de cenários derivados do mapa de cobertura do **Anexo B**
  (pergunta → chunks esperados), e os chunks de referência correspondentes.
- **Execução:** para cada cenário, monta o contexto completo (prompt estático
  + chunks + pergunta) e envia ao LLM — real ou simulado, dependendo do que o
  ambiente de execução permitir.
- **Verificação:** aplica checagens **determinísticas** por cenário — presença
  de citação de fonte reconhecível (`POL-NNN`, `PROC-NNN`, `SLA-NNNN`,
  `FAQ-NN`), ausência de termos proibidos (ex.: confirmar um tier inexistente,
  linguagem hedging tipo "acho que"), e regras específicas do cenário (ex.:
  não afirmar que carga perigosa pode ser devolvida).
- **Saída esperada:** um relatório comparando `v1` vs `v2` que demonstre que a
  v2 corrige os cenários em que a v1 falha (ver
  [Changelog](prompts/CHANGELOG.md) — casos "tier inexistente" e "versões de
  frete conflitantes") — evidência de que a iteração do prompt resolveu um
  problema real, não apenas reescreveu texto.
- **Escopo:** o script não precisa ser uma suíte de produção completa; o
  objetivo é demonstrar o conceito de teste de prompt como regressão
  automatizada, conforme pedido no enunciado do exercício.

---

## 4. Enforcement probabilístico vs. determinístico

Regra geral: **todo guardrail que pode ser expresso como uma checagem
objetiva e estruturada deve sair do prompt e virar código no orquestrador
(o Harness).** O prompt continua responsável apenas pelo que exige julgamento
em linguagem natural — como formular a resposta, como apresentar um conflito
de versões, o tom. Nenhum guardrail crítico deveria depender **só** da
instrução de prompt: o prompt é a primeira linha de defesa (barata, flexível,
mas probabilística); o código é a rede de segurança (mais rígida de mudar,
mas confiável).

| Guardrail (Product Specialist) | Onde vive hoje | Enforcement | Por quê |
|---|---|---|---|
| (1) Sempre citar a fonte | Prompt (regra 2, `system-prompt.v2.md`) **+** código | Prompt instrui; **código valida**: resposta é rejeitada/reenviada se não contiver um padrão de citação reconhecível (`POL-\d{3}`, `PROC-\d{3}`, `SLA-\d{4}`, `FAQ-\d+`) | "Citar fonte" é uma checagem de formato — objetiva, fácil de validar por regex. Não há razão para confiar só na instrução. |
| (2) Nunca inventar prazos/valores | Prompt (regras 1 e 2) **+** código | Prompt instrui a usar só os chunks; **código faz checagem numérica de fundamentação**: todo número/data presente na resposta precisa aparecer em algum chunk do contexto enviado, senão a resposta é sinalizada para revisão | Fidelidade a números é exatamente o tipo de coisa que um LLM pode "arredondar" ou combinar de forma plausível mas errada — a checagem determinística não depende de o modelo "se lembrar" da regra. |
| (3) Quando não encontrar resposta, dizer explicitamente | Código, **antes** de chamar o LLM | **Determinístico primário**: se o retrieval não retorna nenhum chunk acima do score mínimo, o orquestrador nem chama o LLM — retorna a mensagem de fallback fixa e already aciona o fluxo de escalonamento ao supervisor. O prompt (regra 3) é a rede de segurança para o caso em que chunks fracos passam do limiar mas ainda não respondem à pergunta. | Isso remove o caso mais comum de falha (sem chunk nenhum) da mão do modelo por completo — é mais barato e 100% confiável decidir isso em código do que confiar que o modelo sempre vai admitir "não sei". |
| (4) Responder em português formal | Prompt (regra 3, formato) **+** código | Prompt instrui o tom; **código faz detecção de idioma** na resposta antes de entregá-la ao atendente, com um retry automático se detectar outro idioma | Guardrail de formato, checável objetivamente sem entender o conteúdo. |
| Não misturar versões de documento contraditórias ([ADR-0003](../exercicio-1-1/ADR-0003-documentos-contraditorios.md)) | Código **detecta** o conflito, prompt **apresenta** | **Determinístico para detecção**: o orquestrador identifica, antes de montar o contexto, se os chunks recuperados incluem o mesmo `doc_id` em versões diferentes, e marca a query como "em conflito". **Probabilístico para apresentação**: o prompt (regra 4) decide como comunicar isso ao atendente. | A decisão de *que existe* conflito é um fato dos metadados, auditável; a forma de *comunicar* o conflito é redação, que pertence ao prompt. |
| Não confirmar tier/categoria inexistente (caso "Platinum") | Prompt (regra 5) **+** código | **Determinístico como reforço**: valores de tier mencionados na pergunta são resolvidos contra uma lista fechada (`Gold`, `Silver`, `Standard`) **antes** de chegar ao LLM; se o tier citado não existe, a resposta de "tier inexistente" pode ser dada por código, sem depender do modelo perceber a armadilha sozinho. | Esse é hoje o guardrail mais frágil se deixado só no prompt (a armadilha do Anexo B mostra exatamente esse caso) — uma lista fechada validada em código elimina o risco por completo em vez de reduzi-lo. |
| Orçamento de contexto / anti-overflow (seção 2) | Código, 100% | **Determinístico**: contagem de tokens e corte de histórico/chunks antes da chamada ao LLM | Não é um guardrail de conteúdo — é gerenciamento de recursos, não faz sentido pedir ao modelo para "se cortar sozinho". |

Consequência prática para a arquitetura: **o prompt nunca é a única defesa
para um guardrail que envolve fato verificável (existe citação? o número está
no contexto? o tier existe? há chunk nenhum?)**. Esses viram checagens de
código no Harness, com o prompt como primeira tentativa mais barata. O prompt
segue sendo indispensável para tudo que é redação e julgamento — que é
justamente onde o LLM é bom e uma regra determinística seria rígida demais
(ex.: como exatamente frasear a apresentação de duas versões conflitantes de
forma clara para o atendente).

---

## Próximos passos (fora do escopo desta v1 do artefato)

- Gerar o script de teste automatizado com o **GitHub Copilot**, seguindo o
  contrato definido na seção 3, e rodá-lo contra o conjunto completo do
  Anexo B (não só os cenários críticos citados no Changelog).
- Submeter esta v1 a uma rodada de *devil's advocate* com o Claude, no mesmo
  formato usado nas ADRs do Exercício 1.1, antes de marcar como "Aceito".
- Definir o limiar de score mínimo de retrieval citado na seção 4 (guardrail
  3) em conjunto com o Desenvolvedor, a partir de dados reais de retrieval
  (hoje é um placeholder conceitual).
