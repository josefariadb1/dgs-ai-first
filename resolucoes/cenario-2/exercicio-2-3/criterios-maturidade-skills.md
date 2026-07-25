# Critérios de "Skill Madura" — Exercício 2.3 (Tech Lead), Tarefa 4

> Quando uma skill técnica do projeto (Foundation, Domain ou Artifact) está pronta para uso pelo time sem supervisão extra — ou seja, o time pode confiar nela sem reler o código gerado linha a linha "por desconfiança da skill em si". Critérios pensados para serem aplicáveis a qualquer skill do projeto, mas usando `skills/domain/azure-functions-endpoint.md` (Tarefas 1-3 deste exercício) como caso concreto de referência, porque é a única com teste real até agora.

## Por que isso não pode ser "quando parecer boa"

Uma skill mal calibrada tem dois modos de falha, e "parece boa" não distingue nenhum dos dois:
- **Falso positivo de maturidade:** a skill foi lida e parece coerente, mas nunca foi testada contra um agente real — o que ela previne é uma hipótese, não um fato observado.
- **Maturidade prematuramente descartada:** a skill funcionou bem uma vez e o time já a trata como definitiva, sem revisitar quando uma dependência dela muda (ex.: a Foundation skill que ela pressupõe é escrita depois e contradiz uma regra).

Os critérios abaixo existem para tornar essas duas falhas visíveis e mensuráveis, não para burocratizar a criação de skills.

## Critérios (checklist objetivo)

| # | Critério | Como verificar | É sobre... |
|---|---|---|---|
| 1 | **≥ 3 gerações reais** com a skill presente, em rodadas distintas (não 3 arquivos na mesma rodada) | Contar entradas no "Histórico de iteração" da skill + documentos `teste-copilot-*-vN.md` | Confiança estatística mínima — 1 rodada prova que funcionou uma vez, não que é confiável |
| 2 | **≥ 2 artefatos-alvo diferentes** (ex.: `query` e `feedback`, não só o endpoint-exemplo do próprio SKILL.md) | Conferir quais `src/functions/<nome>/` foram gerados durante os testes | Generalização — a skill não pode ter "decorado" o único exemplo que ela mesma mostra |
| 3 | **0 violações reais nas últimas 2 rodadas consecutivas** | Comparar código gerado com a lista de regras prescritivas, regra a regra, nas 2 rodadas mais recentes | Estabilidade — gaps documentados ("regra ainda não testável", como retry.ts) não contam como violação; regra ignorada, conta |
| 4 | **Teste de controle:** pelo menos 1 anti-padrão da lista foi reproduzido gerando o **mesmo artefato sem a skill presente**, confirmando que ela de fato previne o que diz prevenir | Rodar a mesma instrução ao Copilot uma vez com a skill e uma vez sem, comparar | Sem isso, a lista de "anti-padrões comuns" é uma hipótese sobre o que um LLM faria, não uma evidência — ainda pendente para `azure-functions-endpoint` |
| 5 | **Validação empírica, não só leitura:** código gerado com a skill passa `npm run build` e `npm run test` de verdade | Rodar os comandos, anexar saída | Consistente com o padrão já usado neste projeto (Tarefas 2/3 do Exercício 2.2 de MCP) — "parece certo" não é o mesmo que "funciona" |
| 6 | **Revisão por ≥ 1 pessoa além de quem escreveu** (ex.: Tech Lead escreveu, 1 Dev revisa antes de considerar madura) | Registro de aprovação (comentário, ADR, ou nota no PR-markdown) | Evita ponto cego do autor sobre a própria skill |
| 7 | **Toda mudança de regra é rastreável** na seção "Histórico de iteração" da própria skill, com o motivo (gap encontrado vs. correção de erro) | Ler a skill | Skill como artefato vivo, não documento estático — já em prática desde a v2 |
| 8 | **Revisitada quando uma dependência muda:** se uma Foundation skill referenciada nasce ou muda, ou o AGENTS.md muda uma seção relacionada, a skill Domain/Artifact é reavaliada em até 1 sprint | Checklist de onboarding / revisão periódica | Evita que a skill fique desatualizada silenciosamente em relação à fonte de verdade normativa |

Nenhum critério isolado torna uma skill madura — são cumulativos. Uma skill pode atender 7 de 8 e ainda não ser madura se o critério 3 (zero violação em 2 rodadas) falhar, porque é o único que mede se ela realmente funciona quando usada.

## Níveis de maturidade

| Nível | Definição | Uso permitido pelo time |
|---|---|---|
| **Rascunho** | Escrita (Tarefa 1), nunca testada com agente | Não usar em código de produção sem revisão linha a linha do output |
| **Em teste** | 1-2 rodadas de teste real, gaps documentados, nenhuma violação encontrada até agora | Usar com revisão normal de code review (nenhuma confiança extra ainda) |
| **Madura** | Atende os 8 critérios acima | Usar com o nível de confiança de qualquer código revisado — a skill deixa de ser o item sob suspeita quando algo dá errado |
| **Estável / referência** | Madura + usada em produção real por ≥ 3 sprints sem precisar de nova iteração | Vira modelo para escrever outras skills do mesmo nível (Domain ou Artifact) |

Rebaixamento é esperado e normal: uma skill "Madura" que passa a violar uma regra numa rodada nova (ex.: porque o Copilot mudou de versão, ou uma dependência mudou) volta para "Em teste" até nova validação — maturidade não é permanente.

## Estado atual: `skills/domain/azure-functions-endpoint.md`

| Critério | Status | Observação |
|---|---|---|
| 1. ≥ 3 gerações reais | ⚠️ 2/3 | Rodada 1 (`query`, skill v1) e rodada 2 (`feedback`, skill v2) — falta 1 |
| 2. ≥ 2 artefatos-alvo | ✅ 2/2 | `query` (rodada 1) e `feedback` (rodada 2) — critério fechado |
| 3. 0 violações em 2 rodadas consecutivas | ❌ reiniciado | Rodada 1: 0 violações. Rodada 2: **1 violação** (regra 10, indentação). A contagem de "2 rodadas limpas seguidas" reinicia a partir da próxima rodada |
| 4. Teste de controle (com/sem skill) | ❌ não feito | Pendência real — hoje não temos prova de que os anti-padrões listados aconteceriam sem a skill |
| 5. Validação empírica (build+test) | ✅ feito (2x) | Rodada 1: 2/2 testes, build limpo. Rodada 2: 4/4 testes (query + feedback), build limpo, sem regressão em `query` |
| 6. Revisão por ≥ 1 pessoa além do autor | ❌ não feito | Ainda não houve revisão de um segundo humano nesta trilha |
| 7. Histórico de iteração rastreável | ✅ feito | Seção "Histórico de iteração" da skill registra v1→v2 com motivo; achado da rodada 2 registrado em `teste-copilot-skill-azure-functions-endpoint-v2.md` |
| 8. Revisitada quando dependência muda | N/A ainda | Nenhuma Foundation skill foi escrita ainda para disparar isso |

**Classificação atual: "Em teste"** (ainda, não regrediu para "Rascunho" — a violação é pontual e de estilo, não estrutural). A rodada 2 fechou o critério 2 (generalização confirmada: a skill funciona também em `feedback`, não só no exemplo do próprio SKILL.md) mas **reabriu** o critério 3 ao expor a primeira violação real: a regra 10 (indentação) é puramente prompt-level e o teste prova que isso não basta — o Copilot seguiu em 2 de 4 arquivos da mesma leva e ignorou nos outros 2, sem padrão aparente. Isso reforça, com dado real, a mesma lição que o Product Specialist já havia formalizado para guardrails de produto no Exercício 2.2: regras sem consequência funcional visível (nada quebra se a indentação estiver errada) tendem a ser as primeiras a falhar quando o enforcement é só texto. Caminho objetivo para "Madura": (a) decidir se a regra 10 migra para enforcement de código (formatter automático) em vez de prompt — ver recomendação em `teste-copilot-skill-azure-functions-endpoint-v2.md` — e então rodar mais 2 rodadas limpas seguidas para fechar o critério 3; (b) fazer o teste de controle (critério 4); (c) uma revisão de segunda pessoa (critério 6).
