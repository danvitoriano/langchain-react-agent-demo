#!/usr/bin/env python3
"""
Agente ReAct com LangChain — demo hands-on (motor de persistência).

Demonstra:
  - temperature=0 (determinismo)
  - Ferramentas SerpAPI (busca) + LLM-Math (cálculo)
  - verbose=True (rastro Thought / Action / Observation no console)
  - Loop autônomo com até 3 tentativas (slide: lógica na prática):
      * Motor de Persistência — while estado != sucesso e tentativas < 3
      * Percepção e Ação — realizar_acao(objetivo)
      * Observação e Feedback — validar_resultado(resultado)
      * Replanejamento Autônomo — ajustar_estrategia + nova tentativa

Missão padrão: população do Brasil elevada à potência de 0.5.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

_DIR = Path(__file__).resolve().parent
_ENV = _DIR / ".env"

MAX_TENTATIVAS = 3

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

_RESPOSTAS_INVALIDAS = (
    "don't know",
    "do not know",
    "não sei",
    "nao sei",
    "unable to",
    "cannot answer",
    "não foi possível",
    "nao foi possivel",
)


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


def ajustar_estrategia(objetivo: str, tentativa: int) -> str:
    """Replanejamento autônomo: enriquece o objetivo a cada retentativa."""
    if tentativa == 0:
        return objetivo
    if tentativa == 1:
        return (
            "[Estratégia: priorize a ferramenta serpapi para obter dados atuais "
            "antes de calcular.]\n\n"
            f"{objetivo}"
        )
    return (
        "[Estratégia: decomponha em passos — (1) serpapi para população atual do "
        "Brasil, (2) llm-math para elevar à potência de 0.5. Inclua o número final.]\n\n"
        f"{objetivo}"
    )


def realizar_acao(executor: Any, objetivo: str, tentativa: int) -> dict[str, Any]:
    """Percepção e ação: invoca o agente ReAct com o objetivo (e estratégia) atual."""
    numero = tentativa + 1
    print(f"\n(Motor de Persistência) tentativa {numero}/{MAX_TENTATIVAS}")
    print("(Percepção e Ação) invocando agente...")
    return executor.invoke({"input": objetivo})


def validar_resultado(resultado: dict[str, Any], objetivo: str) -> bool:
    """Observação e feedback: heurística sobre a resposta do ambiente (agente)."""
    saida = (resultado.get("output") or "").strip()
    if len(saida) < 30:
        print("(Observação e Feedback) resposta curta ou vazia — inválida.")
        return False

    saida_lower = saida.lower()
    for trecho in _RESPOSTAS_INVALIDAS:
        if trecho in saida_lower:
            print(f"(Observação e Feedback) resposta genérica detectada — inválida.")
            return False

    if "população" in objetivo.lower() or "populacao" in objetivo.lower():
        if "potência" in objetivo.lower() or "potencia" in objetivo.lower():
            if not re.search(r"\d", saida):
                print(
                    "(Observação e Feedback) esperado número na resposta — inválida."
                )
                return False

    print("(Observação e Feedback) resultado aceito.")
    return True


def executar_loop_persistencia(
    executor: Any,
    objetivo: str,
) -> tuple[str, dict[str, Any] | None, bool]:
    """
    Motor de persistência: até MAX_TENTATIVAS ciclos ação → validação → replanejamento.
    Retorna (estado_final, ultimo_resultado, sucesso).
    """
    estado_atual = "em_andamento"
    tentativas = 0
    ultimo_resultado: dict[str, Any] | None = None

    while estado_atual != "sucesso" and tentativas < MAX_TENTATIVAS:
        entrada = ajustar_estrategia(objetivo, tentativas)
        ultimo_resultado = realizar_acao(executor, entrada, tentativas)

        if validar_resultado(ultimo_resultado, objetivo):
            estado_atual = "sucesso"
            break

        tentativas += 1
        if tentativas < MAX_TENTATIVAS:
            print(
                "\n(Replanejamento Autônomo) ajustando estratégia para próxima tentativa..."
            )

    return estado_atual, ultimo_resultado, estado_atual == "sucesso"


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
        description="Agente ReAct (LangChain) — demo hands-on com motor de persistência",
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
    print(f"Motor de persistência: até {MAX_TENTATIVAS} tentativas")
    print("-" * 60)

    executor = build_executor(verbose=not args.quiet)
    try:
        estado, ultimo, ok = executar_loop_persistencia(executor, args.pergunta)
    except Exception as err:
        err_name = type(err).__name__
        if "AuthenticationError" in err_name or "401" in str(err):
            print("\nErro 401 — chave OpenAI rejeitada.")
            print("Confira OPENAI_API_KEY no .env")
            return 1
        raise

    print("-" * 60)
    if ok and ultimo:
        print("\n=== Resposta final (sucesso) ===\n")
        print(ultimo["output"])
        return 0

    print(f"\n=== Falha após {MAX_TENTATIVAS} tentativas (estado: {estado}) ===\n")
    if ultimo and ultimo.get("output"):
        print("Última saída parcial:\n")
        print(ultimo["output"])
    else:
        print("Nenhuma saída obtida.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
