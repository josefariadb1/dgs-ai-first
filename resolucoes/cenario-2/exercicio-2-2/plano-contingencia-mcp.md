# Plano de Contingência de MCP — NovaTech Assistant

> Exercício 2.2 (Tech Lead), Tarefa 3. O que acontece quando um MCP server local fica indisponível (ou perde escopo) durante o desenvolvimento — e como o agente deve se comportar nesse intervalo.

## Contexto

A Tarefa 1 ([`arquitetura-mcp.md`](./arquitetura-mcp.md)) definiu os servers, escopos e o mecanismo de monitoramento (script de health check, Tarefa 2). Esta tarefa parte de uma pergunta diferente: **o monitoramento detecta a falha, mas o que o agente faz enquanto ninguém rodou o health check?** Na prática, um dev não roda o script antes de cada pergunta ao Claude/Copilot — a maior parte das degradações é vivida "ao vivo", dentro de uma sessão de agente, antes de qualquer alerta formal.

O princípio que guia este plano, alinhado ao critério de avaliação do exercício: **agente degradado (capacidade reduzida, mas avisando) é sempre melhor que agente quebrado (para tudo) ou agente que finge que está tudo bem (inventa).** Este último é o pior caso e é literalmente o Incidente #3 do Exercício 2.2 do Product Specialist: o assistente disse "não encontrei informação" sobre SLA Gold quando o documento estava indexado — ali a causa provável não foi o modelo "alucinar", foi o `filesystem` server ter perdido acesso ao escopo e o agente ter tratado "não consigo ler" como "não existe".

---

## 1. Evidência real: o próprio mecanismo de detecção pode falhar silenciosamente

Antes de definir a matriz de contingência, vale registrar um teste real feito para esta tarefa, porque ele prova o risco central deste documento em vez de apenas descrevê-lo. Saída bruta completa (baseline, falha antes da correção, falha depois da correção) em [`health-check-execucao.md`](./health-check-execucao.md); abaixo, o resumo do achado.

**Teste:** com os 4 servers no ar e o health check (Tarefa 2) passando (`4/4 servers passed`), a pasta `docs/novatech/` foi renomeada temporariamente para simular exatamente o cenário do enunciado ("filesystem sem a pasta de docs").

**Resultado 1 (script original):**
```
PASS filesystem
  PASS list_directory docs\novatech: Access denied - path outside allowed directories: ...docs\novatech not in ...\src, ...\specs, ...\skills, ...\data\retrieval-corpus
  PASS list_directory data\retrieval-corpus: [FILE] chunks-novatech.md [FILE] README.md
SUMMARY 4/4 servers passed
```
O script marcou `PASS` mesmo com o filesystem respondendo "Access denied". Causa raiz: `scripts/mcp-health-check.mjs` considerava sucesso qualquer resposta com texto não-vazio (`text.length > 0`), sem checar o campo `isError` que o SDK do MCP retorna na resposta da tool (`{"content":[...], "isError": true}`). Uma mensagem de erro também é "texto não-vazio" — daí o falso-positivo.

**Correção aplicada:** `ok: response.isError !== true && text.length > 0` em `runFilesystemChecks` (arquivo `scripts/mcp-health-check.mjs`).

**Resultado 2 (script corrigido, mesmo cenário de falha):**
```
FAIL filesystem
  FAIL list_directory docs\novatech: Access denied - path outside allowed directories: ...
  PASS list_directory data\retrieval-corpus: [FILE] chunks-novatech.md [FILE] README.md
SUMMARY 3/4 servers passed
```
(exit code 1 — o script agora falha corretamente o processo de CI/onboarding que o invocar). A pasta foi restaurada ao estado original logo em seguida; o `4/4 servers passed` voltou a ser reproduzido.

**Por que isso importa para o plano de contingência:** confirma empiricamente que "o servidor MCP continuar respondendo" não é sinônimo de "o servidor está saudável" — o *reference server* de filesystem não derruba a conexão quando perde escopo, ele responde uma mensagem de erro dentro do protocolo normal. Qualquer camada de detecção (script, ou o próprio agente lendo a resposta) precisa checar o conteúdo/flag de erro, não só "houve resposta". Isso também apareceu no log de start do server: ao subir com um diretório inexistente na lista de argumentos, o processo **não falha** — imprime `Warning: Cannot access directory ..., skipping` no stderr e continua servindo os diretórios restantes. Ou seja, o comportamento padrão dos reference servers já é "degradar silenciosamente"; é responsabilidade do projeto (script + AGENTS.md) tornar essa degradação visível.

---

## 2. Matriz de contingência por server

Para cada server, três colunas: **como a falha se manifesta** (o que o dev ou o agente observam), **o que o agente deve fazer** (comportamento esperado, prescritivo — deve poder ir para o AGENTS.md), e **o que o time faz** (ação humana/operacional).

### `filesystem` — perda de `docs/novatech` (read-only, fonte de negócio)

| | |
|---|---|
| Como a falha se manifesta | Tool `list_directory`/`read_file` retorna `isError: true` com "Access denied" ou "no such file", **não** uma lista vazia (lista vazia só ocorre se o server estiver saudável e a pasta genuinamente vazia). |
| O que o agente DEVE fazer | Responder que **não conseguiu acessar a documentação** ("não tenho acesso à base de conhecimento no momento"), nunca "não encontrei essa informação" — são duas afirmações diferentes e só a segunda vale quando o escopo respondeu normalmente e a busca não teve match. Não inventar conteúdo para compensar. Sugerir rodar `npm run mcp:health-check`. |
| O que o agente NÃO DEVE fazer | Tratar erro de acesso como "documento não existe" ou "informação não disponível" — é a causa direta do Incidente #3 do PS. |
| O que o time faz | Roda `npm run mcp:health-check`; se `FAIL filesystem`, confere se `./docs/novatech` existe no caminho declarado em `.mcp/mcp.json`. Reabre a sessão do agente após restaurar (o cliente MCP não faz auto-retry de escopo). |
| Severidade | Alta — bloqueia toda resposta de negócio (SLA, frete, devolução); é fonte primária de contexto para RAG simulado. |

### `filesystem` — perda de `data/retrieval-corpus` (read-only)

| | |
|---|---|
| Como a falha se manifesta | Mesma assinatura de erro do caso acima, mas no diretório de chunks. |
| O que o agente DEVE fazer | Avisar que a recuperação de chunks está indisponível e que a resposta, se houver, não deve ser tratada como baseada em busca real. |
| O que o time faz | Mesmo fluxo de health check; prioridade um pouco menor que perder `docs/novatech` porque o corpus é o material de "recuperação simulada", não a fonte de negócio primária — mas ainda bloqueia a demonstração do pipeline de RAG. |
| Severidade | Alta para quem está testando o fluxo de busca; média para quem só está trabalhando em código de outra camada (ex.: painel web). |

### `filesystem` — perda de escopo de escrita (`./src`, `./specs`, `./skills`)

| | |
|---|---|
| Como a falha se manifesta | `write_file`/`edit_file`/`create_directory` retornam `isError: true`; diferente dos casos acima, aqui o impacto é sobre **geração de artefato**, não sobre leitura de contexto. |
| O que o agente DEVE fazer | Reportar que não consegue persistir o arquivo gerado e, se possível, devolver o conteúdo gerado no chat para o dev copiar manualmente — nunca reportar "arquivo criado" sem confirmação de sucesso da tool. |
| O que o time faz | Health check não cobre isso hoje (só testa leitura via `list_directory`); tratado como gap conhecido — ver seção 4. |
| Severidade | Média — degrada produtividade, não gera resposta incorreta ao cliente final (não há cliente final nesta fase). |

### `git` — indisponível ou sem acesso ao repositório

| | |
|---|---|
| Como a falha se manifesta | Handshake MCP falha ao conectar (`client.connect` lança erro — cenário diferente dos casos de filesystem, porque aqui é o processo do server que não sobe, não uma tool que responde erro), ou tools de git retornam erro de "not a git repository". |
| O que o agente DEVE fazer | Avisar que não tem acesso ao histórico/diff/branches e parar de fazer afirmações sobre "o que mudou recentemente" ou "quem commitou X" — essas viram suposição sem a tool. |
| O que o time faz | Confirma que `python -m mcp_server_git` está instalado no ambiente (é a dependência mais frágil por não ser `npx`, ver seção 4) e que o comando roda a partir da raiz do repositório. |
| Severidade | Baixa a média — nenhuma resposta ao "cliente" da NovaTech depende de `git`; afeta principalmente Tech Lead/Dev revisando histórico com o agente. |

### `memory` — indisponível

| | |
|---|---|
| Como a falha se manifesta | Handshake falha, ou `read_graph`/`search_nodes` retornam grafo vazio de forma persistente entre sessões (diferente de "vazio porque ainda não gravamos nada"). |
| O que o agente DEVE fazer | Operar sem a linguagem ubíqua/decisões persistidas, mas **avisar explicitamente** que está sem memória de sessões anteriores (ex.: pode reperguntar algo já decidido, como "Gold é tier ou metal?") — o custo de reperguntar é menor que o de assumir uma definição errada. |
| O que o time faz | Reinicia a sessão do agente; se o grafo estava persistido em arquivo local e foi perdido, reconstrói a partir das ADRs/AGENTS.md (fontes de verdade documentais não dependem do `memory` server). |
| Severidade | Baixa — é uma camada de conveniência sobre decisões que também existem documentadas (ADRs, AGENTS.md); a documentação é sempre a fonte de verdade, `memory` é cache de sessão. |

### `everything` — indisponível

| | |
|---|---|
| Como a falha se manifesta | Handshake falha. |
| O que o agente DEVE fazer | Nada especial — este server não é usado em fluxo de produção do projeto (ver Tarefa 1, princípio geral), então sua ausência não deve gerar nenhum aviso ao usuário final da sessão. |
| O que o time faz | Ignora, a menos que alguém esteja especificamente estudando primitivas MCP. |
| Severidade | Nenhuma. |

---

## 3. Regra geral (formato AGENTS.md — prescritiva)

Esta seção é redigida para poder ser colada, sem tradução, na seção "Project Management Rules" ou "Coding Standards" do AGENTS.md do projeto:

```
Contingência de MCP servers:

DEVE:
- Distinguir explicitamente "não tenho acesso à fonte" (erro de tool/servidor)
  de "busquei e não encontrei" (tool respondeu normalmente, sem match).
  Nunca apresentar a primeira situação como se fosse a segunda.
- Ao detectar isError=true (ou falha de handshake) em qualquer chamada de
  tool de um MCP server, avisar o usuário na mesma resposta e sugerir rodar
  `npm run mcp:health-check`.
- Continuar operando com os servers ainda saudáveis (ex.: sem `docs/novatech`,
  o agente ainda pode usar `git` e `memory` normalmente) — degradação é
  parcial, não um "parar tudo".

NÃO DEVE:
- Inventar conteúdo de documento, histórico de commit, ou decisão registrada
  para compensar um MCP server indisponível.
- Reportar sucesso de escrita (`write_file`/`create_directory`/commit) sem
  confirmação explícita de sucesso da tool correspondente.
- Tratar resposta vazia de um escopo de leitura como "não há dados" sem
  primeiro confirmar que não é resposta de erro.

QUANDO EM DÚVIDA:
- Se não for possível confirmar se uma tool falhou por erro de escopo ou
  por ausência real de dado, a resposta deve dizer as duas hipóteses
  explicitamente, não escolher uma.
```

Isso é consistente com o guardrail já formalizado pelo Product Specialist ("QUANDO EM DÚVIDA: prefixar resposta com aviso de baixa confiança") — aqui aplicado à camada de infraestrutura (MCP), não só à qualidade da resposta de negócio.

---

## 4. Gaps conhecidos (honestidade sobre o que o mecanismo atual NÃO cobre)

- O health check (Tarefa 2) testa leitura (`list_directory`) nos escopos read-only, mas não testa escrita nos escopos `rw` (`./src`, `./specs`, `./skills`) nem o server `git`/`memory` além do handshake — um `FAIL` de escrita hoje só aparece durante o uso real pelo agente, não pelo script. Ação futura: estender `runFilesystemChecks` com uma escrita/remoção de um arquivo temporário de teste, e adicionar um check equivalente de "round-trip" para `git` (`git_status`) e `memory` (`create_entities` + `delete_entities` de uma entidade de teste).
- O server `git` usa `python -m mcp_server_git`, dependente de um interpretador Python + pacote instalado — é o único server dos 4 que não roda via `npx -y` (auto-instalável). Isso o torna o mais frágil em onboarding de máquina nova; vale documentar isso explicitamente em `docs/onboarding.md` (referenciado na Tarefa 1, seção 3) como pré-requisito adicional.
- Este plano assume que a degradação é detectada **dentro da sessão do agente** (a tool retorna erro) ou **pelo health check rodado manualmente**. Não há hoje um watcher automático rodando em background durante uma sessão longa — coerente com a Tarefa 1 (não é gate de CI real nesta fase), mas é uma limitação real, não teórica.

---

## Resumo executivo

| Cenário de falha | Severidade | Comportamento esperado do agente |
|---|---|---|
| `filesystem` perde `docs/novatech` | Alta | Avisa que não acessou a fonte; não diz "não encontrei" |
| `filesystem` perde `data/retrieval-corpus` | Alta/Média | Avisa que a recuperação de chunks está indisponível |
| `filesystem` perde escopo de escrita | Média | Devolve o conteúdo no chat; não afirma que salvou |
| `git` indisponível | Baixa/Média | Para de afirmar coisas sobre histórico; opera nas outras frentes |
| `memory` indisponível | Baixa | Avisa que pode reperguntar algo já decidido; usa AGENTS.md/ADRs como fonte de verdade |
| `everything` indisponível | Nenhuma | Sem impacto — não é usado em fluxo real |

**Princípio único que resume o documento:** o agente deve ser capaz de dizer "não consigo verificar isso agora" — essa frase, sozinha, é a diferença entre um agente degradado (aceitável) e um agente que aparenta funcionar normalmente enquanto inventa (o pior cenário, e o que este plano existe para prevenir).
