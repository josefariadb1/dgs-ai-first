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

Opcionalmente, carregar casos de um JSON:
  python script-teste-prompts.py --cases casos.json --mock

Formato esperado de casos.json:
[
  {
    "id": "faq-1",
    "question": "Qual o prazo de entrega?",
    "expected_contains": ["SLA", "2 dias"],
    "forbidden_terms": ["garantido"]
  }
]
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


@dataclass
class TestResult:
    case_id: str
    ok: bool
    checks: dict[str, bool]
    response: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Teste automatizado de prompt para LLM")
    parser.add_argument("--prompt-file", help="Arquivo .md/.txt com prompt de sistema")
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
        # Casos minimos de demonstracao.
        return [
            TestCase(
                id="devolucao-1",
                question="Qual o prazo para solicitar devolucao?",
                expected_contains=["prazo", "devolucao"],
                forbidden_terms=["processar sem analise", "inventar"]
            ),
            TestCase(
                id="frete-1",
                question="Quando posso usar frete especial?",
                expected_contains=["frete especial"],
                forbidden_terms=["promessa absoluta", "100% garantido"]
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
            )
        )
    return cases


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


def mock_llm_answer(question: str) -> str:
    q = question.lower()
    if "devolucao" in q:
        return (
            "O prazo para solicitar devolucao deve seguir a politica vigente e ser validado no atendimento. "
            "[FONTE: POL-001-politica-devolucao.md]"
        )
    return (
        "O frete especial depende de regras operacionais e aprovacao quando aplicavel. "
        "[FONTE: PROC-042-v2-frete-especial-revisado.md]"
    )


def contains_source_citation(text: str) -> bool:
    # Aceita padroes comuns de citacao de fonte.
    patterns = [
        r"\[\s*FONTE\s*:\s*[^\]]+\]",
        r"\bFonte\s*:\s*.+",
    ]
    return any(re.search(p, text, flags=re.IGNORECASE) for p in patterns)


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
    ok = all(checks.values())
    return TestResult(case_id=case.id, ok=ok, checks=checks, response=response)


def print_report(results: list[TestResult]) -> None:
    print("\n=== Relatorio de Testes de Prompt ===")
    passed = 0
    for result in results:
        status = "PASS" if result.ok else "FAIL"
        if result.ok:
            passed += 1

        print(f"\n[{status}] Caso: {result.case_id}")
        for name, value in result.checks.items():
            print(f"  - {name}: {'OK' if value else 'ERRO'}")
        print(f"  - resposta: {result.response}")

    print("\nResumo:")
    print(f"  - aprovados: {passed}")
    print(f"  - total: {len(results)}")


def main() -> int:
    args = parse_args()
    system_prompt = load_prompt(args.prompt_file)
    cases = load_cases(args.cases)

    if not args.mock:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("ERRO: defina OPENAI_API_KEY ou use --mock", file=sys.stderr)
            return 2

    results: list[TestResult] = []
    for case in cases:
        if args.mock:
            response = mock_llm_answer(case.question)
        else:
            response = call_llm_openai_compatible(
                api_key=os.environ["OPENAI_API_KEY"],
                api_base=args.api_base,
                model=args.model,
                system_prompt=system_prompt,
                user_question=case.question,
            )

        results.append(evaluate_response(case, response))

    print_report(results)
    return 0 if all(r.ok for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
