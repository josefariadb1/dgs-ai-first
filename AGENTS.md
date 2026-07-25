# AGENTS.md — dgs-ai-first

Repositório de exercícios práticos do programa **DGS AI First** (DB1). Cada cenário
apresenta um exercício âncora (a NovaTech, empresa de logística) e propõe tarefas
por papel (Delivery Manager, Product Specialist, Desenvolvedor, Tech Lead, QA).

## Estrutura do repositório

```
praticas/                  # Enunciados dos exercícios (não editar — são o enunciado oficial)
├── assets/                # Anexos compartilhados entre todas as práticas (fonte única, não duplicar)
│   ├── anexo-a-documentacao-simulada-novatech.md
│   ├── anexo-b-chunks-referencia-rag.md
│   ├── anexo-c-estrutura-repositorio.md
│   ├── Anexo-D-starter-repo-novatech-assistant/   # cópia-base do repo novatech-assistant (Anexo D)
│   ├── FAQ-atendimento.md, POL-001-*.md, PROC-042*.md, SLA-2024-*.md  # docs-fonte da NovaTech
├── pratica-1/exercicios-1/exercicio-fase-1-entendimento.md      # Cenário 1 — Entendimento e Contexto
├── pratica-2/Prática 2 - V2/exercicio-2-fase-estruturacao.md    # Cenário 2 — Estruturação do Trabalho
└── pratica-3/Cenário/cenario-3-exercicios-fase-governanca.md    # Cenário 3 — Governança e Validação

resolucoes/                # Minhas resoluções (o que eu de fato produzo)
├── cenario-1/exercicio-1-1/  exercicio-1-2/  exercicio-1-3/
├── cenario-2/exercicio-2-1/  exercicio-2-2/  exercicio-2-3/
└── cenario-3/exercicio-3-1/  exercicio-3-2/
```

`pratica-N` (enunciado) corresponde a `cenario-N` (resolução) — a numeração dos
cenários e dos exercícios **não muda** entre a proposta e a resolução.

Os anexos em `praticas/assets/` são referenciados por todos os cenários (Anexo A =
documentação simulada, Anexo B = chunks de referência do RAG, Anexo C = estrutura
do repositório `novatech-assistant`, Anexo D = starter repo desse mesmo projeto).
Não copiar o conteúdo dos anexos para dentro de uma resolução — referenciar o
arquivo em `assets/`.

## Meu papel: Tech Lead

Eu só resolvo os exercícios da seção **`### TECH LEAD`** de cada arquivo de
cenário. Ignorar as seções de Delivery Manager, Product Specialist, Desenvolvedor
e QA — elas existem no enunciado só para dar contexto (às vezes um exercício de
Tech Lead referencia um artefato "simulado" de outro papel como input).

Ao me ajudar com um exercício, ler a seção `### TECH LEAD` completa do arquivo de
cenário correspondente antes de propor a resolução — ela contém contexto, inputs
fornecidos, a tarefa e os critérios de avaliação, que orientam o formato esperado
do entregável.

### Exercícios de Tech Lead por cenário

**Cenário 1 — Entendimento e Contexto** (`praticas/pratica-1/exercicios-1/exercicio-fase-1-entendimento.md`, seção `### TECH LEAD`)
- 1.1 — Decisões arquiteturais como ADRs (modelo LLM, gerenciamento de contexto, documentos contraditórios, build vs buy)
- 1.2 — Prompt engineering e context engineering como artefato de arquitetura (anatomia de contexto, script de teste de prompts)
- 1.3 — Revisão crítica de uma proposta de RAG júnior

**Cenário 2 — Estruturação do Trabalho** (`praticas/pratica-2/Prática 2 - V2/exercicio-2-fase-estruturacao.md`, seção `### TECH LEAD`)
- 2.1 — Construção e teste real do `AGENTS.md` do projeto `novatech-assistant` (v1 → teste com Copilot → v2)
- 2.2 — Arquitetura de MCP (servers locais) + script de health check com execução real
- 2.3 — Criação e teste da skill `azure-functions-endpoint` (v1 → teste com Copilot → v2) + critérios de maturidade

**Cenário 3 — Governança e Validação** (`praticas/pratica-3/Cenário/cenario-3-exercicios-fase-governanca.md`, seção `### TECH LEAD`)
- 3.1 — Design do harness do projeto nas 5 camadas + função de verificação de fonte (Verification loops)
- 3.2 — Revisão crítica de risco dos artefatos gerados por IA ao longo do projeto

Os arquivos `avaliacao-tech-lead.md` em `praticas/pratica-2/Correção - Prática 2/`
e `praticas/pratica-3/Correção/` são os critérios de correção — não são para o
participante, mas servem de checklist de qualidade antes de dar uma resolução por
concluída.

## Convenções ao produzir uma resolução

- Local: `resolucoes/cenario-N/exercicio-N-M/`, um diretório por exercício.
- Idioma: português — os enunciados, ADRs e artefatos são todos em PT-BR (código
  e nomes de campos/identificadores técnicos seguem inglês, conforme os próprios
  enunciados pedem, ex. AGENTS.md do projeto).
- ADRs seguem o formato usado em `cenario-1/exercicio-1-1/`: arquivo
  `ADR-NNNN-titulo-da-decisao.md`, com seções Status / Contexto / Decisão /
  Consequências / Alternativas consideradas.
- Quando o exercício pede iteração (ex. "gere v1, teste, gere v2"), manter as duas
  versões lado a lado com o sufixo `_v1` / `_v2` (ex. `AGENTS.md_v1`,
  `AGENTS.md_v2`, `azure-functions-endpoint.md_v1/_v2`) e um arquivo separado
  `teste-copilot-*.md` com a evidência real do teste — não só a versão final.
- Quando o exercício pede execução real (health check de MCP, testes com Copilot),
  o entregável precisa conter a saída real da execução, não uma descrição do que
  aconteceria.
- Exercícios que exigem rodar o Copilot/agente contra o repositório do projeto
  (2.1, 2.2, 2.3 do cenário 2, e o de verificação do cenário 3) usam uma cópia de
  trabalho do `novatech-assistant` a partir do Anexo D
  (`praticas/assets/Anexo-D-starter-repo-novatech-assistant/`) — não editar o
  Anexo D em si, ele é o estado inicial somente-leitura do starter repo.
