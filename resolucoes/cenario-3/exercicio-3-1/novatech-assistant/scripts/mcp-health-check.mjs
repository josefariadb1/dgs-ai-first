#!/usr/bin/env node
import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, "..");
const mcpConfigPath = path.join(repoRoot, ".mcp", "mcp.json");

// Escopos read-only que o filesystem server deve conseguir listar (Anexo A / Anexo B).
const READ_ONLY_SCOPES = ["docs/novatech", "data/retrieval-corpus"];

function compactText(text, max = 160) {
  const flat = text.replace(/\s+/g, " ").trim();
  return flat.length > max ? `${flat.slice(0, max)}...` : flat;
}

function extractText(content) {
  return (content ?? [])
    .filter((item) => item.type === "text")
    .map((item) => item.text)
    .join("\n");
}

async function connectServer(config) {
  const transport = new StdioClientTransport({
    command: config.command,
    args: config.args ?? [],
    cwd: repoRoot,
    stderr: "pipe",
  });
  const client = new Client(
    { name: "novatech-mcp-health-check", version: "0.1.0" },
    { capabilities: {} },
  );
  await client.connect(transport);
  return { client, transport };
}

async function safeList(client, method) {
  try {
    const result = await client[method]();
    return result;
  } catch {
    return null;
  }
}

async function runFilesystemChecks(client) {
  const checks = [];
  for (const scopePath of READ_ONLY_SCOPES) {
    // O server de filesystem resolve paths relativos contra o primeiro
    // diretório permitido (não contra o cwd do processo) - descoberto ao
    // rodar esta verificação de verdade. Por isso o path enviado à tool
    // precisa ser absoluto, batendo exatamente com um dos allowed dirs.
    const absolutePath = path.join(repoRoot, ...scopePath.split("/"));
    try {
      const response = await client.callTool({
        name: "list_directory",
        arguments: { path: absolutePath },
      });
      const text = extractText(response.content);
      const ok = response.isError !== true && text.length > 0;
      checks.push({
        name: `list_directory ${scopePath}`,
        ok,
        detail: text.length > 0 ? compactText(text) : "empty response",
      });
    } catch (err) {
      checks.push({
        name: `list_directory ${scopePath}`,
        ok: false,
        detail: err instanceof Error ? err.message : String(err),
      });
    }
  }
  return checks;
}

async function checkServer(name, config) {
  let client;
  try {
    ({ client } = await connectServer(config));
  } catch (err) {
    return {
      name,
      ok: false,
      connectError: err instanceof Error ? err.message : String(err),
      tools: [],
      resources: [],
      prompts: [],
      checks: [],
    };
  }

  const toolsResult = await safeList(client, "listTools");
  const resourcesResult = await safeList(client, "listResources");
  const promptsResult = await safeList(client, "listPrompts");

  const checks = name === "filesystem" ? await runFilesystemChecks(client) : [];
  const ok = checks.every((check) => check.ok);

  await client.close();

  return {
    name,
    ok,
    connectError: null,
    tools: (toolsResult?.tools ?? []).map((t) => t.name),
    resources: (resourcesResult?.resources ?? []).map((r) => r.name ?? r.uri),
    prompts: (promptsResult?.prompts ?? []).map((p) => p.name),
    checks,
  };
}

async function main() {
  const raw = await readFile(mcpConfigPath, "utf8");
  const { mcpServers } = JSON.parse(raw);
  const serverNames = Object.keys(mcpServers);

  const results = [];
  for (const name of serverNames) {
    results.push(await checkServer(name, mcpServers[name]));
  }

  for (const result of results) {
    console.log(`${result.ok ? "PASS" : "FAIL"} ${result.name}`);
    if (result.connectError) {
      console.log(`  connect error: ${result.connectError}`);
      continue;
    }
    console.log(`  tools: ${result.tools.join(", ") || "(none)"}`);
    console.log(`  resources: ${result.resources.join(", ") || "(none)"}`);
    console.log(`  prompts: ${result.prompts.join(", ") || "(none)"}`);
    for (const check of result.checks) {
      console.log(`  ${check.ok ? "PASS" : "FAIL"} ${check.name}: ${check.detail}`);
    }
  }

  const passedCount = results.filter((r) => r.ok).length;
  console.log(`SUMMARY ${passedCount}/${results.length} servers passed`);

  process.exit(passedCount === results.length ? 0 : 1);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
