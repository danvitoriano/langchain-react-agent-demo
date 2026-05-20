#!/usr/bin/env python3
"""
Agente ReAct com LangChain — demo hands-on.

Demonstra:
  - temperature=0 (determinismo)
  - Ferramentas SerpAPI (busca) + LLM-Math (cálculo)
  - verbose=True (rastro Thought / Action / Observation no console)

Missão padrão: população do Brasil elevada à potência de 0.5.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

_DIR = Path(__file__).resolve().parent
_ENV = _DIR / ".env"

DEFAULT_QUESTION = (
    "Qual é a população do Brasil elevada à potência de 0.5?"
)

REACT_PROMPT = """Answer the following questions as best you can. You have access to the following tools:

{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {input}
Thought:{agent_scratchpad}"""


def _strip_env(value: str) -> str:
    v = value.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1].strip()
    return v


def _require_env(*names: str) -> None:
    missing = [n for n in names if not os.getenv(n)]
    if missing:
        print("Variáveis de ambiente ausentes:", ", ".join(missing))
        print("Copie .env.example para .env e preencha as chaves.")
        sys.exit(1)

    openai_key = _strip_env(os.environ["OPENAI_API_KEY"])
    os.environ["OPENAI_API_KEY"] = openai_key

    placeholders = ("sk-...", "...", "sua-chave", "your-key")
    if openai_key.lower() in placeholders or len(openai_key) < 20:
        print("OPENAI_API_KEY parece placeholder ou incompleta.")
        print("Gere uma chave real em https://platform.openai.com/api-keys")
        sys.exit(1)

    serp_key = _strip_env(os.environ["SERPAPI_API_KEY"])
    os.environ["SERPAPI_API_KEY"] = serp_key
    if serp_key in ("...", "your-key") or len(serp_key) < 8:
        print("SERPAPI_API_KEY parece placeholder ou incompleta.")
        print("Crie em https://serpapi.com/manage-api-key")
        sys.exit(1)


def build_executor(*, verbose: bool = True):
    from langchain.agents import AgentExecutor, create_react_agent
    from langchain_core.prompts import PromptTemplate
    from langchain_community.agent_toolkits.load_tools import load_tools
    from langchain_openai import ChatOpenAI

    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    llm = ChatOpenAI(model=model, temperature=0)

    tools = load_tools(["serpapi", "llm-math"], llm=llm)
    prompt = PromptTemplate.from_template(REACT_PROMPT)
    agent = create_react_agent(llm, tools, prompt)

    return AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=verbose,
        handle_parsing_errors=True,
        max_iterations=10,
    )


def main() -> int:
    if _ENV.exists():
        load_dotenv(_ENV)

    parser = argparse.ArgumentParser(
        description="Agente ReAct (LangChain) — demo hands-on",
    )
    parser.add_argument(
        "pergunta",
        nargs="?",
        default=DEFAULT_QUESTION,
        help="Pergunta para o agente (padrão: população do Brasil ^ 0.5)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Desliga o rastro verbose no console",
    )
    args = parser.parse_args()

    _require_env("OPENAI_API_KEY", "SERPAPI_API_KEY")

    print("Modelo:", os.getenv("OPENAI_MODEL", "gpt-4o-mini"), "| temperature=0")
    print("Ferramentas: serpapi, llm-math")
    print("Pergunta:", args.pergunta)
    print("-" * 60)

    executor = build_executor(verbose=not args.quiet)
    try:
        result = executor.invoke({"input": args.pergunta})
    except Exception as err:
        err_name = type(err).__name__
        if "AuthenticationError" in err_name or "401" in str(err):
            print("\nErro 401 — chave OpenAI rejeitada.")
            print("Confira OPENAI_API_KEY no .env")
            return 1
        raise

    print("-" * 60)
    print("\n=== Resposta final ===\n")
    print(result["output"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
