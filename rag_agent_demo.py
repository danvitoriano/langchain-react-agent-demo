"""
Demo de RAG agêntico com agente ReAct + LangChain.

Mesmo padrao do tool_use_demo.py, mas o retrieval e exposto como tool
(Base_Conhecimento). Usamos rank_bm25 direto (nao o retriever pronto do
LangChain) para que a Observation mostre o score BM25 de cada chunk no
rastro -- retrieval, ranking top-k e geracao aumentada ficam visiveis no
console.

Aqui o retrieval e lexical (BM25). Em producao a busca seria semantica,
com embeddings e banco vetorial, mas o fluxo Thought -> Action ->
Observation e o mesmo.

Rodar:
    pip install -r requirements.txt
    cp .env.example .env   # preencha OPENAI_API_KEY
    python rag_agent_demo.py
    python rag_agent_demo.py "Qual a politica de reembolso e quantos usuarios tem o Plano Pro?"
"""

import os
import sys
import json

from dotenv import load_dotenv
from rank_bm25 import BM25Okapi

load_dotenv()

if not os.getenv("OPENAI_API_KEY"):
    print("Crie o arquivo .env com OPENAI_API_KEY.")
    sys.exit(1)

from langchain.agents import AgentType, initialize_agent
from langchain_core.tools import Tool
from langchain_openai import ChatOpenAI


# ----------------------------------------------------------------------------
# 1) Base de conhecimento + retrieval BM25 (mock interno da empresa).
# ----------------------------------------------------------------------------

_BASE_CONHECIMENTO = [
    "A politica de reembolso da empresa permite devolucao em ate 30 dias "
    "apos a compra, com estorno integral no mesmo meio de pagamento.",
    "O Plano Pro inclui ate 10 usuarios, suporte prioritario e acesso "
    "completo a API. O Plano Basic e limitado a 2 usuarios.",
    "Clientes com contrato anual tem desconto de 15% sobre o valor "
    "de tabela e prioridade na fila de suporte.",
    "A LGPD exige que dados pessoais como CPF e RG sejam armazenados "
    "com criptografia e acesso restrito por perfil.",
    "O Add-on API permite ate 100 mil chamadas mensais. Acima disso, "
    "e cobrado um valor adicional por bloco de 10 mil chamadas.",
]

_bm25 = BM25Okapi([doc.lower().split() for doc in _BASE_CONHECIMENTO])


def base_conhecimento(pergunta: str) -> str:
    """RAG simples: recupera os trechos mais relevantes via BM25 com score."""
    consulta = pergunta.strip().strip('"').strip("'")
    scores = _bm25.get_scores(consulta.lower().split())
    ranqueados = sorted(
        zip(_BASE_CONHECIMENTO, scores), key=lambda x: x[1], reverse=True
    )
    top_k = [
        {"trecho": doc, "score": round(float(s), 3)}
        for doc, s in ranqueados[:2]
        if s > 0
    ]
    if not top_k:
        return "Nenhum trecho relevante encontrado na base de conhecimento."
    return json.dumps({"resultados": top_k}, ensure_ascii=False)


# ----------------------------------------------------------------------------
# 2) Registro da tool no LangChain.
# ----------------------------------------------------------------------------

ferramentas = [
    Tool(
        name="Base_Conhecimento",
        func=base_conhecimento,
        description=(
            "Busca informacoes na base de conhecimento interna da empresa "
            "(politicas, planos, regras de negocio, LGPD). "
            "Entrada: a pergunta em linguagem natural."
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
