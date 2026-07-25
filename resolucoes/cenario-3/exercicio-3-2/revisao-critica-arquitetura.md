# Revisão Crítica de Risco dos Artefatos Gerados por IA

> Exercício 3.2 (Tech Lead). Ferramenta: Claude (chat) — não depende de GitHub Copilot.

## Contexto

Faltam 2 semanas para a demo à diretoria. Quatro artefatos do projeto foram
produzidos com apoio pesado de IA ao longo dos Cenários 1 e 2. Antes do go-live,
avalio o risco de cada um **antes** de usar o Claude como segunda opinião, para
depois comparar honestamente o que cada revisão pegou.

Artefatos em avaliação:
1. AGENTS.md — gerado pelo Claude, refinado 4 vezes, versão atual com 15 páginas.
2. 3 skills — Foundation refinada após testes reais; Domain e Artifact usadas sem refinamento.
3. Pipeline de ingestão e query endpoint — ~60-70% gerados pelo Copilot.
4. System prompt — iterado 6 vezes, sem registro de por que cada mudança foi feita.

---

## 1. Minha avaliação (antes de usar o Claude)

### AGENTS.md (15 páginas, 4 refinamentos)

- **Risco de ter sido gerado por IA:** documentos longos escritos e refinados por
  IA tendem a acumular regras que soam prescritivas mas nunca foram testadas —
  o próprio Cenário 2 já mostrou isso: o Copilot ignorou 4 regras do AGENTS.md
  num módulo real (`as any`, `console.log`, `require` dinâmico, PII em log).
  Um documento de 15 páginas pode conter mais regras "de papel" do que o time
  imagina.
- **O que verificar antes do go-live:** conferir se as seções mais críticas
  (guardrails de código, orçamento de contexto da ADR-0002) estão perto do
  início do documento — um AGENTS.md longo sofre do mesmo risco de
  *lost-in-the-middle* que qualquer contexto grande; regra enterrada na página
  12 tem menos chance de ser seguida pelo agente do que uma na página 2.
  Reconferir cada regra contra pelo menos um caso real do repositório (igual
  já foi feito com o módulo de feedback) em vez de assumir que "está escrito,
  logo está valendo".

### Skills (Foundation refinada; Domain e Artifact sem refinamento)

- **Risco:** as duas skills nunca testadas contra o Copilot são a incógnita
  real do projeto — a Foundation foi validada empiricamente (gerou, testou,
  corrigiu), as outras duas foram apenas escritas e assumidas como corretas.
  Não sabemos se o Copilot realmente as segue.
- **O que verificar:** repetir, para Domain e Artifact, o mesmo ciclo já
  aplicado à Foundation no Cenário 2 (gerar um artefato de exemplo com o
  Copilot, comparar ao esperado, iterar) — priorizando a skill que será mais
  usada dado o que ainda falta implementar (specs de `feedback-api`,
  `teams-bot` e `painel-web` no Anexo C ainda não têm código).

### Pipeline de ingestão e query endpoint (~60-70% Copilot)

- **Risco:** são os dois componentes mais centrais do sistema — se o padrão
  de erro visto no módulo de feedback (código do Copilot ignorando o
  AGENTS.md) se repetiu aqui, o impacto é maior, porque ingestão e query
  endpoint são o caminho que gera **toda** resposta ao atendente, não um
  endpoint isolado.
- **O que verificar:** cobertura de teste **desses dois módulos
  especificamente** (a média geral de 75% pode estar escondendo um módulo
  bem coberto e outro mal coberto); auditoria pontual contra as mesmas 4
  regras do AGENTS.md que já pegaram o bug do feedback (Zod, pino, imports
  estáticos, PII em log).

### System prompt (6 iterações, sem registro do porquê)

- **Risco (governança):** é o artefato mais crítico do sistema — é onde os
  guardrails de produto vivem hoje (só probabilisticamente, harness ainda em
  construção) — e é o **menos rastreável** dos quatro: sem saber por que cada
  uma das 6 mudanças foi feita, não há como saber se uma iteração recente
  resolveu um caso e quebrou outro sem ninguém perceber, nem como fazer
  **rollback informado** se algo regredir depois do go-live.
- **O que verificar:** reconstituir o histórico real via `git log -p` no
  arquivo do prompt (o Git tem o diff mesmo sem o changelog preenchido);
  rodar as golden queries (`prompts/eval/golden-queries.json`, Anexo D)
  contra a versão atual e comparar contra o comportamento esperado antes da
  demo.

---

## 2. Claude como segundo revisor

Pedi ao Claude uma segunda avaliação dos mesmos quatro artefatos, sem repetir
o que já tinha levantado. Riscos adicionais que não tinha considerado:

- **AGENTS.md — viés de autoconfirmação:** o mesmo modelo que escreveu e
  refinou o documento tende a validar as próprias escolhas quando é ele
  quem revisa depois. As 4 iterações podem ter convergido para "o que o
  Claude acha consistente", não necessariamente para "o que o time
  realmente precisa seguir". Vale uma leitura por alguém (ou outro modelo)
  que não participou da redação.
- **Skills sem refinamento — o risco é pior do que "inconsistente":** um
  Copilot seguindo uma skill não testada não necessariamente gera output
  aleatório — pode gerar output **consistente e consistentemente errado**.
  Se a skill `azure-functions-endpoint` tiver um padrão sutilmente errado
  (ex.: um tipo de erro mal tratado), todo endpoint futuro gerado a partir
  dela repete o mesmo defeito, e por serem todos "iguais" o erro passa
  despercebido no code review.
- **Pipeline e query endpoint — a % não diz onde está o risco:** "60-70%
  gerado pelo Copilot" trata todo o código como equivalente, mas não diz se
  a parte gerada foi lógica de negócio (ex.: como um guardrail é checado) ou
  boilerplate (ex.: setup do handler HTTP). O risco real está em saber
  **qual** 60-70%, não só o quanto.
- **Padrão sistêmico, não quatro riscos isolados:** nenhum dos quatro
  artefatos tem um processo de reavaliação periódica — todos foram escritos,
  iterados uma vez, e depois tratados como prontos. O risco maior não é um
  artefato específico, é a ausência de uma cadência (ex.: revisão trimestral
  do AGENTS.md, teste de regressão do prompt a cada mudança) que pegaria
  degradação **depois** do go-live, não só antes.

## 3. Comparação

| Risco | Eu identifiquei | Claude identificou | Convergência |
|---|---|---|---|
| Skills sem refinamento são a maior incógnita | Sim | Sim (aprofundou: erro consistente, não aleatório) | Convergente, Claude aprofundou |
| System prompt sem changelog = risco de governança/rollback | Sim | Sim (implícito no ponto de cadência) | Convergente |
| AGENTS.md pode ter regras "de papel" | Sim (via lost-in-the-middle) | Sim (via viés de autoconfirmação) | Convergente, ângulos diferentes |
| % de código Copilot não localiza o risco real | Não | Sim | Só o Claude pegou |
| Falta de cadência de reavaliação como risco sistêmico | Não (tratei os 4 como independentes) | Sim | Só o Claude pegou |
| Skills sem refinamento (qual delas verificar primeiro) | Priorizei por uso futuro (specs pendentes) | Não entrou nesse nível de detalhe | Só eu pontuei |

A segunda revisão foi útil onde eu tratei os artefatos de forma isolada: o
Claude achou o padrão comum entre eles (falta de cadência) que eu só via
como quatro problemas separados, e apontou que "60-70% Copilot" é uma métrica
que esconde mais do que revela. Onde eu tinha ido mais fundo (lost-in-the-middle
aplicado ao AGENTS.md, e qual skill priorizar) o Claude não desceu ao mesmo
nível de especificidade — o que é esperado, já que ele não tem acesso ao
Anexo C para saber quais specs ainda estão pendentes.

## 4. Priorização (2 semanas até a demo)

| Ordem | Ação | Por quê primeiro |
|---|---|---|
| 1 | Reconstituir histórico do system prompt (`git log -p`) + rodar golden queries contra a versão atual | Maior risco de governança (sem rollback informado) e o mais barato de verificar — é auditoria, não nova geração. Se houver regressão, é o único item que pode derrubar a demo inteira. |
| 2 | Testar as skills Domain e Artifact contra o Copilot, mesmo ciclo aplicado à Foundation, priorizando `azure-functions-endpoint` (mais reusada nas specs pendentes) | Reduz o risco de repetir o mesmo defeito em múltiplos endpoints ainda a implementar — quanto mais cedo, menos código nasce do padrão errado. |
| 3 | Auditoria dirigida do pipeline de ingestão e do query endpoint contra as 4 regras do AGENTS.md que já pegaram o bug do feedback | Foco no que **já tem histórico de falhar** (mesmo padrão de erro), não uma revisão genérica de todo o código. |

**Risco residual aceito:** releitura completa das 15 páginas do AGENTS.md em
busca de contradições internas fica para depois da demo. É o artefato sem
nenhum incidente concreto atribuído a ele até agora (ao contrário do prompt e
das skills), e o esforço de reler tudo por completo não compensa dentro de 2
semanas. Fica registrado como item para o próximo ciclo, junto com a proposta
de instituir uma cadência de reavaliação periódica (o padrão sistêmico que o
Claude apontou) para os quatro artefatos, não só para este.
