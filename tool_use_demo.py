"""
Demo de TOOL USE (Function Calling) com agente ReAct + LangChain.

Mesma ideia do react_demo.py, mas em vez de ferramentas prontas (serpapi/llm-math)
aqui registramos TRES tools customizadas, definidas no tools_config.yaml:

    1. Sistema_Legado_API   -> consulta historico de vendas de um cliente
    2. Calculadora_Financeira -> juros compostos / projecoes
    3. Validador_Documental -> checa conformidade de um PDF com a LGPD

O agente le a descricao de cada tool e DECIDE sozinho qual chamar, com quais
argumentos. As funcoes abaixo sao mocks (dados fake) so pra demonstrar o fluxo
de chamada -- o ponto da aula e o "tool use", nao o backend real.

Rodar:
    pip install -r requirements.txt
    cp .env.example .env   # preencha OPENAI_API_KEY
    python tool_use_demo.py
    python tool_use_demo.py "Qual o historico de vendas do cliente 4099?"
"""

import os
import sys
import json

from dotenv import load_dotenv

load_dotenv()

if not os.getenv("OPENAI_API_KEY"):
    print("Crie o arquivo .env com OPENAI_API_KEY.")
    sys.exit(1)

from langchain.agents import AgentType, initialize_agent
from langchain_core.tools import Tool
from langchain_openai import ChatOpenAI


# ----------------------------------------------------------------------------
# 1) Implementacao das tools (mocks). Cada uma recebe UMA string como entrada,
#    que e o padrao do agente ZERO_SHOT_REACT_DESCRIPTION.
# ----------------------------------------------------------------------------

_VENDAS_FAKE = {
    "4099": [
        {"data": "2026-01-12", "produto": "Plano Pro", "valor": 1290.00},
        {"data": "2026-03-04", "produto": "Add-on API", "valor": 350.00},
    ],
    "1001": [
        {"data": "2025-11-20", "produto": "Plano Basic", "valor": 99.00},
    ],
}


def sistema_legado_api(customer_id: str) -> str:
    """Consulta o historico de vendas de um cliente no sistema legado."""
    cid = customer_id.strip().strip('"').strip("'")
    vendas = _VENDAS_FAKE.get(cid)
    if not vendas:
        return f"Nenhuma venda encontrada para o cliente {cid}."
    total = sum(v["valor"] for v in vendas)
    return json.dumps(
        {"customer_id": cid, "vendas": vendas, "total": total},
        ensure_ascii=False,
    )


def calculadora_financeira(entrada: str) -> str:
    """
    Juros compostos. Entrada esperada como JSON, ex:
    {"principal": 1000, "taxa_mensal": 0.01, "meses": 12}
    """
    try:
        dados = json.loads(entrada)
        p = float(dados["principal"])
        i = float(dados["taxa_mensal"])
        n = int(dados["meses"])
    except Exception:
        return ('Entrada invalida. Use JSON: '
                '{"principal": 1000, "taxa_mensal": 0.01, "meses": 12}')
    montante = p * (1 + i) ** n
    juros = montante - p
    return json.dumps(
        {"montante": round(montante, 2), "juros": round(juros, 2)},
        ensure_ascii=False,
    )


def validador_documental(caminho_pdf: str) -> str:
    """Verifica (mock) a conformidade de um PDF com a LGPD."""
    nome = caminho_pdf.strip().strip('"').strip("'")
    achados = []
    lower = nome.lower()
    if "cpf" in lower or "rg" in lower:
        achados.append("Possivel dado pessoal sensivel no nome do arquivo.")
    if not lower.endswith(".pdf"):
        achados.append("Arquivo nao parece ser um PDF.")
    conforme = len(achados) == 0
    return json.dumps(
        {
            "documento": nome,
            "conforme_lgpd": conforme,
            "alertas": achados or ["Nenhum alerta de conformidade."],
        },
        ensure_ascii=False,
    )


# ----------------------------------------------------------------------------
# 2) Registro das tools no LangChain. O 'description' e o que o LLM usa pra
#    decidir QUANDO chamar cada uma -- escreva com cuidado.
# ----------------------------------------------------------------------------

ferramentas = [
    Tool(
        name="Sistema_Legado_API",
        func=sistema_legado_api,
        description=(
            "Consulta o historico de vendas de um cliente. "
            "Entrada: o customer_id (string), ex: 4099."
        ),
    ),
    Tool(
        name="Calculadora_Financeira",
        func=calculadora_financeira,
        description=(
            "Calcula juros compostos e projecoes. "
            "Entrada: JSON com principal, taxa_mensal e meses, ex: "
            '{{"principal": 1000, "taxa_mensal": 0.01, "meses": 12}}.'
        ),
    ),
    Tool(
        name="Validador_Documental",
        func=validador_documental,
        description=(
            "Verifica a conformidade de um PDF com a LGPD. "
            "Entrada: o caminho ou nome do arquivo PDF."
        ),
    ),
]


# ----------------------------------------------------------------------------
# 3) Monta o agente ReAct e executa.
# ----------------------------------------------------------------------------

modelo = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
llm = ChatOpenAI(model=modelo, temperature=0)

executor = initialize_agent(
    ferramentas,
    llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True,
    return_intermediate_steps=True,
    handle_parsing_errors=True,
)

pergunta = " ".join(sys.argv[1:]).strip()
if not pergunta:
    pergunta = input("\nPergunta: ").strip()
if not pergunta:
    sys.exit(1)

resultado = executor.invoke({"input": pergunta})

passos = resultado.get("intermediate_steps", [])
if passos:
    print("\n--- Rastro das ferramentas ---\n")
    for i, (acao, observacao) in enumerate(passos, start=1):
        print(f"[{i}] {acao.tool}")
        print(f"    Entrada: {acao.tool_input}")
        print(f"    Saida:   {observacao}")

print("\n--- Resposta ---\n")
print(resultado["output"])
