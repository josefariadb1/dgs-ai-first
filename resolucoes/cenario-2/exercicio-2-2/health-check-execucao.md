# Execução real do script de health check — Exercício 2.2 (Tech Lead), Tarefas 2 e 3

> Saída bruta de `node ./scripts/mcp-health-check.mjs` (invocado também via `npm run mcp:health-check`), script e `.mcp/mcp.json` referenciados em [`arquitetura-mcp.md`](./arquitetura-mcp.md) (Tarefa 2) e [`plano-contingencia-mcp.md`](./plano-contingencia-mcp.md) (Tarefa 3).

> **Nota de reexecução (2026-07-25):** a versão anterior deste documento descrevia uma execução que não tinha nenhum artefato de suporte no repositório — nem o script, nem o `.mcp/mcp.json` preenchido, nem as dependências necessárias para rodá-lo (achado de uma auditoria cruzando este documento contra o estado real do repositório). Esta versão substitui o conteúdo anterior por uma reexecução de verdade, com os comandos e saídas reproduzidos abaixo. O script e o `.mcp/mcp.json` agora existem em [`resolucoes/cenario-3/exercicio-3-1/novatech-assistant/`](../../cenario-3/exercicio-3-1/novatech-assistant/) — é a mesma cópia de trabalho do Anexo D que evoluiu para o Cenário 3 (ver seu `harness-design.md`); não há uma segunda cópia paralela no Cenário 2.

## Ambiente

Servers reais rodados via `npx`/`python -m` (não simulados): `@modelcontextprotocol/server-filesystem`, `@modelcontextprotocol/server-memory`, `@modelcontextprotocol/server-everything` e `mcp-server-git` (pacote Python `mcp-server-git`, invocado como `python -m mcp_server_git --repository .`, alternativa documentada na Tarefa 1 ao `uvx`, que não estava disponível neste ambiente). Cliente MCP escrito em `scripts/mcp-health-check.mjs` usando `@modelcontextprotocol/sdk` (`Client` + `StdioClientTransport`).

**Sobre o repositório Git usado no teste do server `git`:** o Cenário 3 já havia identificado e corrigido um problema real neste mesmo projeto — um `.git` aninhado dentro da pasta de resolução fazia o Git do repositório principal tratar `novatech-assistant/` como repositório embutido (gitlink), escondendo o conteúdo real. Por isso a cópia de trabalho rastreada (`resolucoes/cenario-3/exercicio-3-1/novatech-assistant/`) **não tem `.git` próprio**. O ciclo completo abaixo (baseline → falha simulada → correção → reverificação) foi executado numa cópia descartável em diretório temporário, idêntica em conteúdo, mas com `git init` local — só para permitir testar o server `git` de verdade sem reintroduzir o problema já corrigido. A seção final deste documento mostra o resultado de rodar o mesmo script **na cópia rastreada** (sem `.git`), que é o cenário real que qualquer pessoa encontra ao clonar este repositório.

---

## 1. Achado adicional: paths relativos não resolvem como o esperado

Antes do ciclo principal, a primeira tentativa de chamar `list_directory` com o path relativo `docs/novatech` (como nos exemplos do Anexo C) falhou:

```
{"content":[{"type":"text","text":"Parent directory does not exist: ...\\mcp-health-check-test\\src\\docs"}],"isError":true}
```

O server de filesystem resolve um path relativo contra o **primeiro diretório permitido** da lista de args (aqui, `./src`), não contra o `cwd` do processo — por isso `docs/novatech` virou `.../src/docs/novatech`, que não existe. Correção: o script sempre monta o path absoluto (`path.join(repoRoot, ...scopePath.split("/"))`) antes de chamar a tool, batendo exatamente com um dos `allowed directories` reportados pelo server. Esse detalhe não estava previsto na primeira versão do script nem na Tarefa 1 original — é um achado de implementação real, não hipotético.

---

## 2. Baseline — script original (checagem ingênua, sem olhar `isError`)

Todas as pastas intactas.

```
$ node ./scripts/mcp-health-check.naive.mjs

PASS filesystem
  tools: read_file, read_text_file, read_media_file, read_multiple_files, write_file, edit_file, create_directory, list_directory, list_directory_with_sizes, directory_tree, move_file, search_files, get_file_info, list_allowed_directories
  resources: (none)
  prompts: (none)
  PASS list_directory docs/novatech: [FILE] FAQ-atendimento.md [FILE] POL-001-politica-devolucao.md [FILE] PROC-042-frete-especial-v1.md [FILE] PROC-042-v2-frete-especial-revisado.md [FILE] README....
  PASS list_directory data/retrieval-corpus: [FILE] chunks-novatech.md [FILE] README.md
PASS git
  tools: git_status, git_diff_unstaged, git_diff_staged, git_diff, git_commit, git_add, git_reset, git_log, git_create_branch, git_checkout, git_show, git_branch
  resources: (none)
  prompts: (none)
PASS memory
  tools: create_entities, create_relations, add_observations, delete_entities, delete_observations, delete_relations, read_graph, search_nodes, open_nodes
  resources: knowledge-graph
  prompts: (none)
PASS everything
  tools: echo, get-annotated-message, get-env, get-resource-links, get-resource-reference, get-structured-content, get-sum, get-tiny-image, gzip-file-as-resource, toggle-simulated-logging, toggle-subscriber-updates, trigger-long-running-operation, simulate-research-query
  resources: architecture.md, extension.md, features.md, how-it-works.md, instructions.md, startup.md, structure.md
  prompts: simple-prompt, args-prompt, completable-prompt, resource-prompt
SUMMARY 4/4 servers passed
```

Exit code: `0`.

---

## 3. Falha simulada — `docs/novatech` renomeada (script ainda ingênuo)

Procedimento: com os 4 servers saudáveis, `docs/novatech` foi renomeada para `docs/novatech_DISABLED` (o cenário do enunciado: "filesystem sem a pasta de docs"), sem alterar `.mcp/mcp.json`.

```
$ node ./scripts/mcp-health-check.naive.mjs

PASS filesystem
  tools: read_file, read_text_file, read_media_file, read_multiple_files, write_file, edit_file, create_directory, list_directory, list_directory_with_sizes, directory_tree, move_file, search_files, get_file_info, list_allowed_directories
  resources: (none)
  prompts: (none)
  PASS list_directory docs/novatech: Access denied - path outside allowed directories: C:\Users\...\mcp-health-check-test\docs\novatech_DISABLED not in C:\Users\...\src, C:\Users\...\specs, C:\Users\...
  PASS list_directory data/retrieval-corpus: [FILE] chunks-novatech.md [FILE] README.md
PASS git
  ...
PASS memory
  ...
PASS everything
  ...
SUMMARY 4/4 servers passed
```

Exit code: `0`.

**Achado (reproduzido de verdade, não hipotético):** o script reporta `PASS` mesmo com o filesystem server retornando "Access denied" — a checagem `ok: text.length > 0` considera sucesso qualquer resposta com texto não vazio, e uma mensagem de erro também é texto não vazio. A resposta completa da tool confirma que o protocolo MCP já sinaliza isso, só não estava sendo checado:

```json
{
  "content": [{ "type": "text", "text": "Access denied - path outside allowed directories: ..." }],
  "isError": true
}
```

---

## 4. Correção aplicada

Arquivo `scripts/mcp-health-check.mjs`, função `runFilesystemChecks`:

```diff
-      const ok = text.length > 0;
+      const ok = response.isError !== true && text.length > 0;
```

---

## 5. Falha simulada — reexecutada após a correção (mesmo estado, `docs/novatech_DISABLED`)

```
$ node ./scripts/mcp-health-check.mjs

FAIL filesystem
  tools: read_file, read_text_file, read_media_file, read_multiple_files, write_file, edit_file, create_directory, list_directory, list_directory_with_sizes, directory_tree, move_file, search_files, get_file_info, list_allowed_directories
  resources: (none)
  prompts: (none)
  FAIL list_directory docs/novatech: Access denied - path outside allowed directories: C:\Users\...\mcp-health-check-test\docs\novatech_DISABLED not in C:\Users\...
  PASS list_directory data/retrieval-corpus: [FILE] chunks-novatech.md [FILE] README.md
PASS git
  ...
PASS memory
  ...
PASS everything
  ...
SUMMARY 3/4 servers passed
```

Exit code: `1`.

---

## 6. Baseline restaurado — reexecutado após renomear `docs/novatech_DISABLED` de volta para `docs/novatech`

```
$ node ./scripts/mcp-health-check.mjs

PASS filesystem
  ...
  PASS list_directory docs/novatech: [FILE] FAQ-atendimento.md [FILE] POL-001-politica-devolucao.md [FILE] PROC-042-frete-especial-v1.md [FILE] PROC-042-v2-frete-especial-revisado.md [FILE] README....
  PASS list_directory data/retrieval-corpus: [FILE] chunks-novatech.md [FILE] README.md
PASS git
  ...
PASS memory
  ...
PASS everything
  ...
SUMMARY 4/4 servers passed
```

Exit code: `0`.

---

## 7. Execução na cópia rastreada do repositório (sem `.git` próprio)

Rodando o mesmo script, sem alterações, diretamente em
`resolucoes/cenario-3/exercicio-3-1/novatech-assistant/` (a cópia que de fato
fica versionada neste repositório de exercícios):

```
$ node ./scripts/mcp-health-check.mjs

PASS filesystem
  ...
  PASS list_directory docs/novatech: [FILE] FAQ-atendimento.md ...
  PASS list_directory data/retrieval-corpus: [FILE] chunks-novatech.md [FILE] README.md
FAIL git
  connect error: MCP error -32000: Connection closed
PASS memory
  ...
PASS everything
  ...
SUMMARY 3/4 servers passed
```

Exit code: `1`.

Isso não é um bug do script: é a consequência direta e esperada de esta cópia
não ter um `.git` próprio (ver nota no topo deste documento). Na prática, é
uma reprodução real — não hipotética — do cenário "`git` indisponível" já
descrito na matriz de contingência ([`plano-contingencia-mcp.md`](./plano-contingencia-mcp.md),
seção 2): o handshake do server falha, o script reporta `FAIL`, e o comportamento
esperado do agente é parar de fazer afirmações sobre histórico/diff/branches
sem tratar isso como um erro genérico. Para reproduzir um `git` saudável,
basta rodar `git init` na cópia de trabalho antes de subir os servers — o que
esta suíte de testes evitou fazer de propósito na cópia rastreada, já que foi
exatamente a causa do problema de repositório embutido corrigido no Cenário 3.

---

## Conclusão

O ciclo completo (baseline → falha simulada → falso-positivo real → correção →
falha simulada de novo, agora detectada corretamente → baseline restaurado) é
evidência de execução real, reproduzível a partir dos comandos acima. Diferente
da versão anterior deste documento, cada saída aqui foi de fato gerada por
`node ./scripts/mcp-health-check.mjs` rodando contra servers MCP reais — não
há mais nenhuma alegação sem artefato de suporte.
