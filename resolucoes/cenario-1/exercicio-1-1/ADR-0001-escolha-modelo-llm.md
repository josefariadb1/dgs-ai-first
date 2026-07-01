# ADR-0001: Escolha do modelo de LLM para o assistente de atendimento

## Status
Proposto

## Contexto

O assistente da NovaTech precisa gerar respostas em português, fundamentadas em
documentação interna recuperada via RAG, com citação de fonte e **sem inventar
informação** (requisito do Product Specialist). Forças que atuam sobre a decisão:

- **Ecossistema Microsoft já existente.** A NovaTech possui licenças Microsoft 365 E3
  e está disposta a provisionar Azure AI Services. A integração final é em Teams +
  SharePoint. Governança de dados, autenticação (Entra ID) e compliance favorecem
  manter o processamento dentro do tenant Azure.
- **Volume e custo.** ~320 chamados/dia × 60% com consulta ≈ **192 queries/dia**
  (~4.000–4.500/mês em ~22 dias úteis). Cada query envia, em ordem de grandeza,
  system prompt + guardrails (~2K tokens) + metadados do cliente + 6–8 chunks
  recuperados (~3–4K tokens) + pergunta, e gera ~300–600 tokens de resposta.
  Isso resulta em ~30M tokens de entrada e ~2M de saída por mês. Mesmo nas tarifas
  atuais de modelos de fronteira, o custo fica na ordem de **baixas centenas de
  dólares/mês** — ou seja, **custo não é a restrição dominante**; qualidade da
  fundamentação nas fontes e integração são.
- **Janela de contexto.** Para RAG com poucos chunks por query, **128K tokens são
  mais que suficientes**. Janela maior não é diferencial relevante aqui — encher o
  contexto com texto irrelevante tende, inclusive, a degradar a qualidade da resposta.
- **Requisito de não alucinar.** Nenhum modelo elimina alucinação por si só. A
  mitigação real vem do RAG (fundamentar a resposta nos documentos recuperados),
  do prompt e de validação determinística fora do modelo. O modelo precisa apenas
  ser **forte em seguir instruções e em fidelidade ao contexto fornecido** em
  português.

## Decisão

Adotar **Azure OpenAI Service com GPT-4o** como modelo primário de geração, acessado
via endpoint dentro do tenant Azure da NovaTech. A escolha **não é assumida de
antemão**: ela só é confirmada depois de um **teste de fidelidade às fontes, em
português**, feito na fase de descoberta (discovery). Esse teste é um **ponto de
decisão de "seguir ou não seguir" com o GPT-4o** e funciona assim:

1. Montamos um conjunto de ~30–50 perguntas reais de atendimento, cada uma com a
   resposta correta e o trecho do documento que a fundamenta (retirados da própria base
   da NovaTech).
2. Rodamos esse mesmo conjunto no GPT-4o e em ao menos um modelo concorrente, usando o
   RAG já montado.
3. Medimos, para cada resposta, se ela está factualmente correta, se cita a fonte certa
   e se **não inventa** nada fora dos trechos recuperados.
4. Se o GPT-4o atingir o patamar mínimo de acerto combinado com a NovaTech, seguimos com
   ele; se não atingir, trocamos o modelo pela camada de abstração (abaixo), sem alterar
   o resto da arquitetura.

O acesso ao modelo será feito por meio de uma **camada de abstração de geração** —
uma interface única (`GenerationClient`) no orquestrador, com **adapters por
fornecedor** (Azure OpenAI no MVP; Claude e Ollama como adapters de
contingência/benchmark). A abstração é deliberadamente **fina e bem delimitada**, para
não virar uma falsa promessa de portabilidade:

**Dentro da abstração (contrato estável):**
- `generate(messages, params) -> { texto, uso_tokens, modelo, latência }` — assinatura única.
- Parâmetros de geração (temperatura, max_tokens, top_p) e identidade do modelo
  (deployment, versão fixada, região) vêm de **configuração**, não de código.
- **Contagem de tokens** via tokenizer do fornecedor encapsulada atrás da interface
  (tiktoken do OpenAI ≠ tokenizer do Claude). O cálculo do orçamento de contexto do
  pipeline consome essa função, em vez de chamar um tokenizer diretamente.
- **Observabilidade obrigatória:** cada chamada registra `modelo`, `versão do
  deployment`, tokens de entrada/saída e latência.
- **Resiliência:** timeout, retry com backoff e um modelo de fallback opcional por
  configuração.

**Fora da abstração (resolvido por adapter, não "achatado"):**
- Formatos nativos de tool-calling / structured output, prompt caching e semântica de
  system prompt **diferem entre fornecedores** e ficam no adapter específico — não
  fingimos que são idênticos. A abstração garante a troca do **caminho de geração**,
  não a portabilidade de toda feature avançada.

## Consequências

**Positivas**
- Dados de prompt e documentos permanecem na fronteira Azure/Entra ID — sem egress
  para um terceiro fora da governança já contratada pela NovaTech.
- Integração nativa com Teams, SharePoint e os serviços de busca do Azure reduz
  fricção e prazo no go-live de 3 meses.
- Faturamento, contrato e compliance consolidados sob a relação Azure existente.
- GPT-4o tem boa qualidade em português e em gerar respostas fundamentadas nas fontes
  fornecidas, e 128K de janela cobrem o caso de uso com folga.

**Negativas / riscos**
- Dependência de um fornecedor de modelo gerenciado (lock-in parcial), mitigada pela
  camada de abstração.
- Disponibilidade regional e cotas (TPM/RPM) do Azure OpenAI precisam ser confirmadas
  para a região e validadas contra o pico de chamados. **Provisionamento e aprovação de
  cota podem ter lead time** — risco direto ao prazo de 3 meses.
- Se a região com residência de dados exigida não oferecer GPT-4o, surge um **trade-off
  residência × latência × disponibilidade do modelo** que precisa ser decidido
  explicitamente.
- **Risco de abstração vazante/prematura:** a camada de abstração dá uma sensação de
  portabilidade que não é total (tool-calling, caching e contagem de tokens diferem por
  fornecedor). Mitigado ao delimitar o contrato (acima) e isolar o específico no adapter.
- Custo por token é recorrente (vs. CAPEX de um modelo self-hosted), embora baixo no
  volume estimado.

## Alternativas consideradas

- **Claude via API (Anthropic).** Qualidade de ponta e janela maior (200K), forte em
  seguir guardrails. Descartado como primário porque introduz um **segundo fornecedor
  fora da governança Azure** já contratada (egress de dados, contrato e billing
  separados, revisão de compliance adicional) sem ganho proporcional para este caso de
  uso. Permanece como **alternativa de contingência/benchmark** graças à camada de
  abstração.
- **Modelos open-source self-hosted via Ollama (ex.: Llama, Mistral).** Sem custo por
  token e com controle total dos dados. Descartado para o MVP por exigir infraestrutura
  de GPU, operação e tuning que o time não tem capacidade de sustentar no prazo de 3
  meses, além de qualidade tipicamente inferior em PT para tarefas ancoradas e ausência
  de SLA gerenciado. Reavaliável no futuro caso custo/privacidade se tornem dominantes.
- **Gemini (Google).** Modelo forte, com janela de contexto ampla e boa qualidade em
  português. Descartado como primário pelo mesmo motivo do Claude: roda no Google Cloud,
  **fora da governança Azure/Microsoft** já contratada (saída de dados, contrato e
  faturamento separados, revisão de compliance adicional), sem ganho que justifique para
  este caso de uso ancorado. Pode entrar como **concorrente** no teste de fidelidade
  descrito na seção Decisão.
- **DeepSeek.** Custo competitivo e boa qualidade. Como **API hospedada**, porém, fica
  fora da governança Azure e levanta preocupações de **residência e soberania de dados**
  (provedor sediado na China) — sensível para uma empresa com forte componente de
  compliance como a NovaTech. Os pesos são abertos, então só seria considerado pelo
  caminho **self-hosted**, recaindo na mesma carga de infraestrutura/operação do item
  anterior. Descartado como primário por governança/residência.

## Contra-argumentos (Devil's Advocate) e respostas

- *"Se custo não é a restrição, por que não Claude, que pode ser melhor em fidelidade?"*
  — Para o volume da NovaTech a diferença de qualidade não justifica abrir mão da
  integração e da governança Azure já pagas. A camada de abstração nos deixa medir
  ambos e migrar se um benchmark com a base real provar vantagem material.
- *"GPT-4o vai ser depreciado e te força a migrar."* — Por isso a decisão não é
  "GPT-4o para sempre", e sim "Azure OpenAI com modelo configurável". A troca de
  versão (ex.: para um sucessor no mesmo serviço) é uma mudança de configuração, não de
  arquitetura.
- *"O modelo escolhido resolve a alucinação?"* — Não, e nenhum resolve. A garantia de
  não inventar é responsabilidade do RAG + prompt + validação determinística, não do
  modelo. Esta ADR escolhe o gerador; o anti-alucinação é tratado em outras decisões de
  arquitetura do projeto (gerenciamento de contexto e tratamento de documentos
  contraditórios).
- *"Você decidiu o modelo antes de qualquer evidência de fidelidade na base real — isso
  é escolha por conveniência de governança, não pelo requisito que mais importa."*
  — Procede. Por isso a decisão passou a ser **condicional ao teste de fidelidade às
  fontes em português** descrito na seção Decisão, e a camada de abstração existe
  justamente para rodar o mesmo conjunto de perguntas em GPT-4o e em um concorrente a
  baixo custo de troca. Se o GPT-4o reprovar, trocamos o modelo, não a arquitetura.
- *"Cota/região do Azure OpenAI e residência de dados podem furar o prazo de 3 meses."*
  — Risco aceito e movido para o início: **provisionar o recurso e validar cota/região
  na primeira semana do discovery**, com o trade-off residência × latência decidido
  explicitamente caso a região com residência não tenha GPT-4o.
- *"Uma camada de abstração sobre um único fornecedor é abstração prematura e vai
  vazar."* — Em parte sim, e é por isso que o contrato foi **delimitado** (interface
  fina, tokenizer/observabilidade/resiliência dentro; tool-calling/caching/structured
  output por adapter). Não prometemos portabilidade de toda feature — só do caminho de
  geração, que é o suficiente para benchmark e contingência.

## Histórico de iterações

- **Iteração 0 — Criação:** versão inicial; decisão por Azure OpenAI GPT-4o com uma camada de abstração descrita de forma genérica ("interface única configurável").
- **Iteração 1 — Devil's advocate + detalhamento da camada de abstração**, em dois eixos:
  - *Devil's advocate:* a decisão foi tornada **condicional ao teste de fidelidade às fontes em português** na fase de descoberta (antes era assumida); adicionados os riscos de lead time de cota/região/residência do Azure e de escolha por conveniência de governança.
  - *Camada de abstração:* especificada de forma delimitada — contrato `GenerationClient`, adapters por fornecedor, com tokenizer/observabilidade/resiliência *dentro* e tool-calling/caching/structured output *fora*; adicionado o risco de abstração vazante/prematura.
- **Iteração 2 — Clareza do teste de fidelidade + novas alternativas:** o termo "benchmark de grounding (go/no-go)" foi reescrito em português, com o processo explicado em passos na seção Decisão; o conteúdo da Iteração 1 foi separado nos dois eixos acima; adicionadas as alternativas **Gemini (Google)** e **DeepSeek** às alternativas consideradas.
- **Iteração 3 — Remoção do termo "grounding":** as demais ocorrências da palavra em inglês (em Contexto e Consequências) foram substituídas por "fundamentação/fundamentado(a) nas fontes", mantendo o mesmo sentido técnico sem estrangeirismo.
