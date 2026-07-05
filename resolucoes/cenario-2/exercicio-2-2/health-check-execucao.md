# Execução real do script de health check — Exercício 2.2 (Tech Lead), Tarefas 2 e 3

> Saída bruta das execuções de `npm run mcp:health-check` (que roda `scripts/mcp-health-check.mjs` contra o `.mcp/mcp.json` do `novatech-assistant`), referenciadas em [`arquitetura-mcp.md`](./arquitetura-mcp.md) (Tarefa 2) e [`plano-contingencia-mcp.md`](./plano-contingencia-mcp.md) (Tarefa 3).

Ambiente: `praticas/pratica-2/Prática 2 - V2/novatech-assistant`, comando `npm run mcp:health-check`.

---

## 1. Baseline — todos os servers saudáveis (script original, antes da correção)

```
> novatech-assistant@0.1.0 mcp:health-check
> node ./scripts/mcp-health-check.mjs

PASS filesystem
  server: unknown
  tools: read_file, read_text_file, read_media_file, read_multiple_files, write_file, edit_file, create_directory, list_directory, list_directory_with_sizes, directory_tree, move_file, search_files, get_file_info, list_allowed_directories
  resources: (none)
  prompts: (none)
  PASS list_directory docs\novatech: [FILE] FAQ-atendimento.md [FILE] POL-001-politica-devolucao.md [FILE] PROC-042-frete-especial-v1.md [FILE] PROC-042-v2-frete-especial-revisado.md [FILE] README.
  PASS list_directory data\retrieval-corpus: [FILE] chunks-novatech.md [FILE] README.md
PASS git
  server: unknown
  tools: git_status, git_diff_unstaged, git_diff_staged, git_diff, git_commit, git_add, git_reset, git_log, git_create_branch, git_checkout, git_show, git_branch
  resources: (none)
  prompts: (none)
PASS memory
  server: unknown
  tools: create_entities, create_relations, add_observations, delete_entities, delete_observations, delete_relations, read_graph, search_nodes, open_nodes
  resources: knowledge-graph
  prompts: (none)
PASS everything
  server: unknown
  tools: echo, get-annotated-message, get-env, get-resource-links, get-resource-reference, get-structured-content, get-sum, get-tiny-image, gzip-file-as-resource, toggle-simulated-logging, toggle-subscriber-updates, trigger-long-running-operation, simulate-research-query
  resources: architecture.md, extension.md, features.md, how-it-works.md, instructions.md, startup.md, structure.md
  prompts: simple-prompt, args-prompt, completable-prompt, resource-prompt
SUMMARY 4/4 servers passed
```

Exit code: `0`.

---

## 2. Falha simulada — `docs/novatech/` renomeada (script original, ANTES da correção)

Procedimento: com os 4 servers saudáveis, a pasta `docs/novatech` foi renomeada para `docs/novatech_DISABLED` (simulando exatamente o cenário do enunciado: "filesystem sem a pasta de docs"), sem alterar `.mcp/mcp.json`.

```
> novatech-assistant@0.1.0 mcp:health-check
> node ./scripts/mcp-health-check.mjs

PASS filesystem
  server: unknown
  tools: read_file, read_text_file, read_media_file, read_multiple_files, write_file, edit_file, create_directory, list_directory, list_directory_with_sizes, directory_tree, move_file, search_files, get_file_info, list_allowed_directories
  resources: (none)
  prompts: (none)
  PASS list_directory docs\novatech: Access denied - path outside allowed directories: C:\Projetos\Zoop\dgs-ai-first\praticas\pratica-2\Prática 2 - V2\novatech-assistant\docs\novatech not in C:\Pro...
  PASS list_directory data\retrieval-corpus: [FILE] chunks-novatech.md [FILE] README.md
PASS git
  ...
PASS memory
  ...
PASS everything
  ...
SUMMARY 4/4 servers passed
```

Exit code: `0`.

**Achado:** o script reporta `PASS` mesmo com o filesystem server retornando uma mensagem de erro (`Access denied`). O check `runFilesystemChecks` em `scripts/mcp-health-check.mjs` considerava sucesso qualquer resposta com texto não vazio (`text.length > 0`), e uma mensagem de erro também é texto não vazio — falso-positivo. Chamando a mesma tool diretamente via SDK, a resposta completa é:

```json
{
  "content": [
    {
      "type": "text",
      "text": "Access denied - path outside allowed directories: ...\\docs\\novatech not in ...\\src, ...\\specs, ...\\skills, ...\\data\\retrieval-corpus"
    }
  ],
  "isError": true
}
```

O campo `isError: true` já vem no protocolo MCP e não estava sendo verificado.

Também observado no stderr do processo do filesystem server ao subir com o diretório ausente (evidência de que o *reference server* degrada silenciosamente por padrão, sem derrubar o processo):
```
Warning: Cannot access directory C:\...\novatech-assistant\docs\novatech, skipping
Secure MCP Filesystem Server running on stdio
Client does not support MCP Roots, using allowed directories set from server args: [
  '...\\src', '...\\specs', '...\\skills', '...\\data\\retrieval-corpus'
]
```

---

## 3. Correção aplicada

Arquivo `scripts/mcp-health-check.mjs`, função `runFilesystemChecks`:

```diff
     const text = extractText(response.content);
-    checks.push({
-      name: `list_directory ${path.relative(repoRoot, targetPath)}`,
-      ok: text.length > 0,
-      detail: text.length > 0 ? compactText(text) : 'empty response',
-    });
+    const ok = response.isError !== true && text.length > 0;
+    checks.push({
+      name: `list_directory ${path.relative(repoRoot, targetPath)}`,
+      ok,
+      detail: text.length > 0 ? compactText(text) : 'empty response',
+    });
```

---

## 4. Baseline — reexecutado após a correção (confirma que nada quebrou)

```
> novatech-assistant@0.1.0 mcp:health-check
> node ./scripts/mcp-health-check.mjs

PASS filesystem
  server: unknown
  tools: read_file, read_text_file, read_media_file, read_multiple_files, write_file, edit_file, create_directory, list_directory, list_directory_with_sizes, directory_tree, move_file, search_files, get_file_info, list_allowed_directories
  resources: (none)
  prompts: (none)
  PASS list_directory docs\novatech: [FILE] FAQ-atendimento.md [FILE] POL-001-politica-devolucao.md [FILE] PROC-042-frete-especial-v1.md [FILE] PROC-042-v2-frete-especial-revisado.md [FILE] README.
  PASS list_directory data\retrieval-corpus: [FILE] chunks-novatech.md [FILE] README.md
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

## 5. Falha simulada — reexecutada após a correção (DEPOIS)

Mesmo procedimento do item 2: `docs/novatech` renomeada para `docs/novatech_DISABLED`.

```
> novatech-assistant@0.1.0 mcp:health-check
> node ./scripts/mcp-health-check.mjs

FAIL filesystem
  server: unknown
  tools: read_file, read_text_file, read_media_file, read_multiple_files, write_file, edit_file, create_directory, list_directory, list_directory_with_sizes, directory_tree, move_file, search_files, get_file_info, list_allowed_directories
  resources: (none)
  prompts: (none)
  FAIL list_directory docs\novatech: Access denied - path outside allowed directories: C:\Projetos\Zoop\dgs-ai-first\praticas\pratica-2\Prática 2 - V2\novatech-assistant\docs\novatech not in C:\Pro...
  PASS list_directory data\retrieval-corpus: [FILE] chunks-novatech.md [FILE] README.md
PASS git
  server: unknown
  tools: git_status, git_diff_unstaged, git_diff_staged, git_diff, git_commit, git_add, git_reset, git_log, git_create_branch, git_checkout, git_show, git_branch
  resources: (none)
  prompts: (none)
PASS memory
  server: unknown
  tools: create_entities, create_relations, add_observations, delete_entities, delete_observations, delete_relations, read_graph, search_nodes, open_nodes
  resources: knowledge-graph
  prompts: (none)
PASS everything
  server: unknown
  tools: echo, get-annotated-message, get-env, get-resource-links, get-resource-reference, get-structured-content, get-sum, get-tiny-image, gzip-file-as-resource, toggle-simulated-logging, toggle-subscriber-updates, trigger-long-running-operation, simulate-research-query
  resources: architecture.md, extension.md, features.md, how-it-works.md, instructions.md, startup.md, structure.md
  prompts: simple-prompt, args-prompt, completable-prompt, resource-prompt
SUMMARY 3/4 servers passed
```

Exit code: `1`.

Após o teste, `docs/novatech_DISABLED` foi renomeada de volta para `docs/novatech`, e uma execução final de confirmação voltou a reportar `PASS filesystem` / `SUMMARY 4/4 servers passed` / exit code `0`.

---

## Conclusão

O ciclo completo (baseline → falha simulada → achado de bug no próprio mecanismo de detecção → correção → falha simulada novamente → baseline restaurado) é a evidência de execução real exigida pela Tarefa 2 e a base empírica do plano de contingência da Tarefa 3: um MCP server local pode responder normalmente ao protocolo mesmo tendo perdido acesso ao seu escopo, e só uma checagem explícita de erro (no script ou no agente) evita que isso seja lido como "sucesso".
