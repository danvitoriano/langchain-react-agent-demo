import os
import sys

from dotenv import load_dotenv

load_dotenv()

if not os.getenv("OPENAI_API_KEY") or not os.getenv("SERPAPI_API_KEY"):
    print("Crie o arquivo .env com OPENAI_API_KEY e SERPAPI_API_KEY.")
    sys.exit(1)

pergunta = input("\nPergunta: ").strip()
if not pergunta:
    sys.exit(1)

from langchain.agents import AgentType, initialize_agent
from langchain_community.agent_toolkits.load_tools import load_tools
from langchain_openai import ChatOpenAI

from gerar_imagem import criar_ferramenta_gerar_imagem

modelo = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
llm = ChatOpenAI(model=modelo, temperature=0)

ferramentas = load_tools(["serpapi", "llm-math"], llm=llm)
ferramentas.append(criar_ferramenta_gerar_imagem())

executor = initialize_agent(
    ferramentas,
    llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True,
    return_intermediate_steps=True,
    handle_parsing_errors=True,
)

resultado = executor.invoke({"input": pergunta})

passos = resultado.get("intermediate_steps", [])
if passos:
    print("\n--- Rastro das ferramentas ---\n")
    for i, (acao, observacao) in enumerate(passos, start=1):
        print(f"[{i}] {acao.tool}")
        print(f"    Entrada: {acao.tool_input}")
        print(f"    Saída:   {observacao}")

print("\n--- Resposta ---\n")
print(resultado["output"])
