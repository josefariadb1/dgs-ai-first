# Changelog — Prompts do Assistente de Atendimento NovaTech

Formato: cada entrada referencia o cenário de teste que motivou a mudança,
implementado em [`casos-anexo-b.json`](../casos-anexo-b.json) e executável com
[`script-teste-prompts.py`](../script-teste-prompts.py) (ver seção 3 da
[estratégia](../estrategia-prompt-engineering.md)), para manter
rastreabilidade entre prompt e caso de teste — nenhuma mudança de prompt
deveria acontecer sem um caso de teste associado (novo ou existente que
falhou).

## v2 — 2026-07-01
**Status:** vigente · **Aprovado por:** Tech Lead + Product Specialist (simulado)

- Adicionada regra 4 (apresentar ambas as versões com data em caso de
  conflito), alinhada à [ADR-0003](../../exercicio-1-1/ADR-0003-documentos-contraditorios.md).
  Motivada pelo caso de teste `frete-versoes-conflitantes`, que no v1 não tinha
  instrução alguma sobre como agir diante de dois chunks do mesmo `doc_id`.
- Adicionada regra 5 (nunca confirmar tier/categoria inexistente). Motivada
  pelo caso de teste `sla-platinum-inexistente` (armadilha do Anexo B): o v1
  não impedia o modelo de "inventar" um SLA para um tier que não existe.
- Adicionada regra 6 (FAQ é fonte informal, não oficial). Motivada pelos
  chunks FAQ-32 e FAQ-38 do Anexo B, que não têm respaldo em documento formal
  e podem ser citados com falsa autoridade se tratados como qualquer outra
  fonte.
- Prompt reestruturado em seções numeradas (identidade / regras / formato /
  uso de chunks / contexto dinâmico) para permitir testes por seção e
  facilitar revisão em PR.
- Placeholders de contexto dinâmico (`{{TIER_CLIENTE}}`, `{{CHUNKS_RECUPERADOS}}`
  etc.) tornados explícitos no próprio arquivo do prompt, em vez de ficarem
  implícitos no código de orquestração.

## v1 — baseline
**Status:** substituído

- Versão mínima fornecida como ponto de partida: identidade, instrução de
  citar fonte, instrução de "se não souber, diga que não sabe".
- Não tratava: conflito entre versões de documento, tiers/categorias
  inexistentes, nem diferença de confiabilidade entre fonte formal e FAQ.
- Falha confirmada nos cenários `sla-platinum-inexistente` e
  `frete-versoes-conflitantes` ao rodar `script-teste-prompts.py --mock
  --cases casos-anexo-b.json` contra esta versão (ver seção 3 da estratégia).
