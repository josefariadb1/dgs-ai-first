# ADR-0003: Tratamento de documentos contraditórios no pipeline de RAG

## Status
Proposto

## Contexto

A documentação da NovaTech é atualizada por 3 áreas (Operações, Compliance, Comercial)
**sem processo unificado de revisão**, e versões coexistem sem hierarquia clara. O caso
canônico real na base:

- **PROC-042 v1** (emissão 03/03/2023): multiplicador Norte **1.6**, Sudeste **1.0**,
  prazo de frete especial **+2 dias úteis**.
- **PROC-042-v2** (emissão 10/11/2023): multiplicador Norte **1.8**, Sudeste **1.1**,
  prazo **+3 dias úteis**, e uma **cláusula transitória**: chamados abertos antes de
  **01/12/2023** usam a v1; chamados a partir de 01/12/2023 usam a v2.

Ambos os arquivos declaram explicitamente que **não há indicação formal de vigência ou
de substituição** no sistema. Forças:

- **Requisito do Product Specialist:** documentos contraditórios devem **mostrar ambas
  as versões com indicação de data**; o assistente **nunca deve inventar** qual é a
  válida.
- **Risco de mistura silenciosa:** o pior cenário é a resposta combinar o multiplicador
  de uma versão com o prazo da outra sem o atendente perceber.
- **RAG é um problema de dados, não só de modelo:** pedir ao LLM que "decida qual está
  certo" é probabilístico e não auditável. A vigência é um fato de negócio que pertence
  aos **metadados**, não ao palpite do modelo.
- A regra correta nem sempre é "a mais recente": a cláusula transitória mostra que a
  versão aplicável pode **depender da data de abertura do chamado**.

## Decisão

Resolver contradições na **camada de dados (ingestão + metadados)**, não delegando a
escolha ao LLM:

1. **Versionamento explícito na ingestão.** Cada documento recebe metadados:
   `doc_id` lógico (ex.: `PROC-042`), `versao`, `data_emissao`, `data_vigencia_inicio`,
   `status` (`vigente` | `substituido` | `transitorio`) e `fonte`. Curadoria humana
   define `status` quando o documento não traz indicação — esse é um **gap de processo
   da NovaTech que o projeto expõe**, não algo que o RAG adivinha.
2. **Preferência por versão vigente no retrieval**, mantendo **ambas indexadas**. O
   retriever prioriza a versão `vigente`; versões `substituido`/`transitorio`
   permanecem recuperáveis para casos que dependem de data.
3. **Detecção de conflito.** Quando dois chunks do **mesmo `doc_id`** com **versões
   diferentes** forem relevantes para a query, o orquestrador marca conflito e instrui
   o LLM a **apresentar ambas as versões com suas datas** e a **não fundir** valores —
   exatamente o requisito do Product Specialist.
4. **Não inventar a regra de desempate de negócio.** Quando a aplicação depende de uma
   data (ex.: cláusula transitória do PROC-042-v2), o assistente **expõe a condição**
   ("para chamados a partir de 01/12/2023, multiplicador 1.8; antes disso, 1.6") em vez
   de escolher sozinho, e sugere validar com o supervisor se a data do chamado não for
   conhecida.

## Consequências

**Positivas**
- Atende diretamente o requisito de "mostrar ambas as versões com data".
- Elimina o risco mais grave: a **mistura silenciosa** de regras de versões diferentes.
- A decisão de vigência é **auditável e centralizada** nos metadados, não dispersa em
  prompts.
- Cria pressão saudável para a NovaTech adotar um processo de versionamento formal.

**Negativas / riscos**
- Exige **curadoria humana inicial** para classificar `status` dos documentos sem
  vigência declarada — esforço real na fase de discovery/ingestão.
- A detecção de conflito por `doc_id` depende de **identificadores consistentes**;
  documentos com o mesmo conteúdo mas IDs diferentes podem escapar.
- Respostas com "duas versões" são mais longas e podem ser percebidas como menos
  diretas pelo atendente (mitigável no design da resposta).

## Alternativas consideradas

- **Manter apenas a versão mais recente (descartar as antigas na ingestão).**
  Descartado: violaria a cláusula transitória do PROC-042-v2 (chamados antigos exigem a
  v1) e o requisito de mostrar ambas as versões. Perde informação legítima.
- **Delegar 100% ao LLM a escolha da versão correta via instrução no prompt.**
  Descartado como mecanismo primário: é probabilístico, não auditável e propenso a
  alucinar a regra de vigência. O prompt é usado apenas para **apresentar** o conflito
  detectado pelos dados, não para **decidir** qual vale.
- **Resolver só no prompt, sem metadados de versão.** Descartado: empurra um problema
  de dados para a camada probabilística, justamente o anti-padrão que esta ADR evita.

## Contra-argumentos (Devil's Advocate) e respostas

- *"Curadoria manual de status não escala para ~1.250 fontes."* — Não precisa: a
  contradição é exceção, não regra. Agentes de IA na fase de Intent **sinalizam
  candidatos** a conflito (mesmo `doc_id`/tema, datas diferentes) e humanos só
  classificam esse subconjunto. A maioria dos docs entra como `vigente` por padrão.
- *"Mostrar duas versões confunde o atendente."* — Confunde menos do que uma resposta
  única e confiante que mistura 1.6 com prazo +3 dias. A transparência sobre a
  contradição é o comportamento correto enquanto a NovaTech não unifica o processo.
- *"O LLM poderia simplesmente preferir a data mais recente."* — Quase sempre sim, mas
  o PROC-042-v2 prova que "mais recente" **não é universal** (chamados antigos usam v1).
  Por isso a regra de negócio mora nos metadados/orquestrador, não na heurística do
  modelo.
