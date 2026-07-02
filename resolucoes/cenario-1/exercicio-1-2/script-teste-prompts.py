#!/usr/bin/env python3
"""
Script de teste automatizado de prompts (conceito).

Objetivo:
- Enviar perguntas para um LLM usando um prompt de sistema.
- Validar criterios basicos da resposta:
  1) contem citacao de fonte
  2) nao contem termos proibidos
  3) contem termos esperados para o caso de teste

Uso rapido:
  python script-teste-prompts.py --mock

Uso com API OpenAI-compativel:
  set OPENAI_API_KEY=seu_token
  python script-teste-prompts.py --model gpt-4o-mini

Carregar casos de um JSON (cada caso pode incluir chunks recuperados, que
sao injetados no contexto junto com a pergunta -- ver casos-anexo-b.json
para os cenarios reais do projeto NovaTech):
  python script-teste-prompts.py --cases casos-anexo-b.json --prompt-file prompts/system-prompt.v2.md --mock

Comparar duas versoes de prompt no mesmo lote de casos (ex.: v1 vs v2):
  python script-teste-prompts.py --cases casos-anexo-b.json \
      --prompt-file prompts/system-prompt.v1.md \
      --prompt-file-b prompts/system-prompt.v2.md --mock

Formato esperado do JSON de casos:
[
  {
    "id": "faq-1",
    "question": "Qual o prazo de entrega?",
    "chunks": ["Secao 2: o prazo padrao e de 2 dias uteis."],
    "expected_contains": ["SLA", "2 dias"],
    "forbidden_terms": ["garantido"],
    "expected_source_pattern": "SLA-\\d{4}"
  }
]

- "chunks" (opcional): trechos ja recuperados pelo pipeline de RAG, injetados
  no contexto enviado ao LLM junto com a pergunta. Sem chunks, o teste so
  valida a adesao ao system prompt, nao a fidelidade a uma fonte concreta.
- "expected_source_pattern" (opcional): regex que a citacao de fonte da
  resposta precisa casar (ex.: "POL-\\d{3}"). Sem isso, o script so confirma
  que *alguma* citacao no formato "[FONTE: ...]"/"Fonte: ..." existe, sem
  garantir que aponta para um documento real.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Iterable


DEFAULT_SYSTEM_PROMPT = (
    "Voce e um assistente de atendimento. "
    "Sempre responda de forma objetiva e inclua citacao de fonte no formato [FONTE: nome-do-arquivo]. "
    "Se nao souber, diga que nao encontrou a informacao na base."
)


@dataclass
class TestCase:
    id: str
    question: str
    expected_contains: list[str]
    forbidden_terms: list[str]
    chunks: list[str]
    expected_source_pattern: str | None = None


@dataclass
class TestResult:
    case_id: str
    ok: bool
    checks: dict[str, bool]
    response: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Teste automatizado de prompt para LLM")
    parser.add_argument("--prompt-file", help="Arquivo .md/.txt com prompt de sistema")
    parser.add_argument(
        "--prompt-file-b",
        help="Segundo arquivo de prompt para rodar a mesma suite e comparar (ex.: versao anterior vs. vigente)",
    )
    parser.add_argument("--cases", help="Arquivo JSON com casos de teste")
    parser.add_argument("--model", default="gpt-4o-mini", help="Modelo do LLM")
    parser.add_argument("--api-base", default="https://api.openai.com/v1", help="Base URL da API")
    parser.add_argument("--mock", action="store_true", help="Nao chama API; usa respostas simuladas")
    return parser.parse_args()


def load_prompt(prompt_file: str | None) -> str:
    if not prompt_file:
        return DEFAULT_SYSTEM_PROMPT
    with open(prompt_file, "r", encoding="utf-8") as f:
        return f.read().strip()


def load_cases(cases_file: str | None) -> list[TestCase]:
    if not cases_file:
        # Casos minimos de demonstracao (sem chunks -- so testa adesao ao
        # system prompt). Para os cenarios reais do projeto, com chunks do
        # Anexo B, use --cases casos-anexo-b.json.
        return [
            TestCase(
                id="devolucao-1",
                question="Qual o prazo para solicitar devolucao?",
                expected_contains=["prazo", "devolucao"],
                forbidden_terms=["processar sem analise", "inventar"],
                chunks=[],
            ),
            TestCase(
                id="frete-1",
                question="Quando posso usar frete especial?",
                expected_contains=["frete especial"],
                forbidden_terms=["promessa absoluta", "100% garantido"],
                chunks=[],
            ),
        ]

    with open(cases_file, "r", encoding="utf-8") as f:
        raw = json.load(f)

    cases: list[TestCase] = []
    for item in raw:
        cases.append(
            TestCase(
                id=item["id"],
                question=item["question"],
                expected_contains=item.get("expected_contains", []),
                forbidden_terms=item.get("forbidden_terms", []),
                chunks=item.get("chunks", []),
                expected_source_pattern=item.get("expected_source_pattern"),
            )
        )
    return cases


def build_user_message(question: str, chunks: list[str]) -> str:
    if not chunks:
        return question
    chunk_block = "\n".join(f"- {chunk}" for chunk in chunks)
    return f"## Chunks recuperados\n{chunk_block}\n\n## Pergunta do atendente\n{question}"


def call_llm_openai_compatible(
    *,
    api_key: str,
    api_base: str,
    model: str,
    system_prompt: str,
    user_question: str,
) -> str:
    payload = {
        "model": model,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_question},
        ],
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{api_base.rstrip('/')}/chat/completions",
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            response_data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Falha HTTP ao chamar LLM: {e.code} - {detail}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Falha de rede ao chamar LLM: {e}") from e

    try:
        return response_data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as e:
        raise RuntimeError(f"Resposta inesperada da API: {response_data}") from e


def mock_llm_answer(question: str, system_prompt: str, chunks: list[str]) -> str:
    """Simula o comportamento tipico esperado de um LLM dado o prompt e os
    chunks fornecidos -- nao e uma previsao real do modelo. As respostas
    variam conforme o CONTEUDO do system_prompt (nao o nome do arquivo), para
    que o mock reflita se o guardrail relevante esta ou nao presente no
    prompt sendo testado. `chunks` recebido para simetria com o caminho real
    (que os usa via build_user_message) -- o mock decide so por palavra-chave
    da pergunta, sem ler o conteudo dos chunks."""
    q = question.lower()
    prompt_lower = system_prompt.lower()

    if "platinum" in q:
        tier_guardrail = "invente categorias" in prompt_lower or "nao estejam descritos nos chunks" in prompt_lower
        if tier_guardrail:
            return (
                "Nao existe tier Platinum na NovaTech. Os tiers validos sao "
                "Gold, Silver e Standard. [FONTE: SLA-2024, secao 1]"
            )
        return (
            "O cliente Platinum tem resposta em ate 1h e resolucao em ate 12h. "
            "[FONTE: SLA-2024]"
        )

    if "sudeste" in q and "multiplicador" in q:
        conflict_guardrail = "nao escolha uma versao sozinho" in prompt_lower or "apresente as duas" in prompt_lower
        if conflict_guardrail:
            return (
                "Existem duas versoes vigentes para datas diferentes: PROC-042 "
                "(ate 30/11/2023) usa multiplicador 1.0 para o Sudeste; "
                "PROC-042-v2 (a partir de 01/12/2023) usa 1.1. Confirme a data "
                "de abertura do chamado com o supervisor. [FONTE: PROC-042-v2, secao 5]"
            )
        return "O multiplicador regional para o Sudeste e 1.1. [FONTE: PROC-042-v2]"

    if "perigosa" in q and "devolv" in q:
        return (
            "Nao. Cargas perigosas (classes 1 a 6 da ANTT) nao sao elegiveis "
            "para devolucao pelo processo padrao. [FONTE: POL-001, secao 3.2]"
        )

    if "devolucao" in q:
        return (
            "O prazo para solicitar devolucao deve seguir a politica vigente. "
            "[FONTE: POL-001-politica-devolucao.md]"
        )

    return (
        "O frete especial depende de regras operacionais e aprovacao quando aplicavel. "
        "[FONTE: PROC-042-v2-frete-especial-revisado.md]"
    )


def contains_source_citation(text: str) -> bool:
    # Aceita padroes comuns de citacao de fonte (checagem de FORMATO, nao
    # garante que a fonte citada seja real -- ver expected_source_pattern
    # por caso para uma checagem de conteudo mais forte).
    patterns = [
        r"\[\s*FONTE\s*:\s*[^\]]+\]",
        r"\bFonte\s*:\s*.+",
    ]
    return any(re.search(p, text, flags=re.IGNORECASE) for p in patterns)


def matches_expected_source(text: str, expected_source_pattern: str | None) -> bool:
    if not expected_source_pattern:
        return True
    return re.search(expected_source_pattern, text, flags=re.IGNORECASE) is not None


def contains_any_forbidden_term(text: str, forbidden_terms: Iterable[str]) -> bool:
    low_text = text.lower()
    return any(term.lower() in low_text for term in forbidden_terms)


def contains_expected_terms(text: str, expected_terms: Iterable[str]) -> bool:
    low_text = text.lower()
    return all(term.lower() in low_text for term in expected_terms)


def evaluate_response(case: TestCase, response: str) -> TestResult:
    checks = {
        "has_source_citation": contains_source_citation(response),
        "no_forbidden_terms": not contains_any_forbidden_term(response, case.forbidden_terms),
        "contains_expected_terms": contains_expected_terms(response, case.expected_contains),
    }
    if case.expected_source_pattern:
        checks["matches_expected_source"] = matches_expected_source(response, case.expected_source_pattern)
    ok = all(checks.values())
    return TestResult(case_id=case.id, ok=ok, checks=checks, response=response)


def print_report(results: list[TestResult], label: str) -> None:
    print(f"\n=== Relatorio de Testes de Prompt -- {label} ===")
    passed = 0
    for result in results:
        status = "PASS" if result.ok else "FAIL"
        if result.ok:
            passed += 1

        print(f"\n[{status}] Caso: {result.case_id}")
        for name, value in result.checks.items():
            print(f"  - {name}: {'OK' if value else 'ERRO'}")
        print(f"  - resposta: {result.response}")

    print(f"\nResumo {label}: {passed}/{len(results)} aprovados")


def print_comparison(label_a: str, results_a: list[TestResult], label_b: str, results_b: list[TestResult]) -> None:
    print(f"\n=== Comparacao {label_a} vs {label_b} ===")
    by_id_b = {r.case_id: r for r in results_b}
    for result_a in results_a:
        result_b = by_id_b.get(result_a.case_id)
        status_a = "PASS" if result_a.ok else "FAIL"
        status_b = "PASS" if (result_b and result_b.ok) else "FAIL"
        marker = "  " if status_a == status_b else ">>"
        print(f"{marker} {result_a.case_id}: {label_a}={status_a}  {label_b}={status_b}")


def run_suite(system_prompt: str, cases: list[TestCase], args: argparse.Namespace, api_key: str | None) -> list[TestResult]:
    results: list[TestResult] = []
    for case in cases:
        user_message = build_user_message(case.question, case.chunks)
        if args.mock:
            response = mock_llm_answer(case.question, system_prompt, case.chunks)
        else:
            response = call_llm_openai_compatible(
                api_key=api_key,
                api_base=args.api_base,
                model=args.model,
                system_prompt=system_prompt,
                user_question=user_message,
            )
        results.append(evaluate_response(case, response))
    return results


def main() -> int:
    args = parse_args()
    cases = load_cases(args.cases)

    api_key = None
    if not args.mock:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("ERRO: defina OPENAI_API_KEY ou use --mock", file=sys.stderr)
            return 2

    system_prompt_a = load_prompt(args.prompt_file)
    label_a = args.prompt_file or "prompt-default"
    results_a = run_suite(system_prompt_a, cases, args, api_key)
    print_report(results_a, label_a)

    all_ok = all(r.ok for r in results_a)

    if args.prompt_file_b:
        system_prompt_b = load_prompt(args.prompt_file_b)
        label_b = args.prompt_file_b
        results_b = run_suite(system_prompt_b, cases, args, api_key)
        print_report(results_b, label_b)
        print_comparison(label_a, results_a, label_b, results_b)
        all_ok = all_ok and all(r.ok for r in results_b)

    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
