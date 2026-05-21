import os
import sys

from dotenv import load_dotenv

load_dotenv()

if not os.getenv("OPENAI_API_KEY") or not os.getenv("SERPAPI_API_KEY"):
    print("Crie o arquivo .env com OPENAI_API_KEY e SERPAPI_API_KEY.")
    sys.exit(1)

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

pergunta = input("\nPergunta: ").strip()
if not pergunta:
    sys.exit(1)

from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import PromptTemplate
from langchain_community.agent_toolkits.load_tools import load_tools
from langchain_openai import ChatOpenAI

modelo = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
llm = ChatOpenAI(model=modelo, temperature=0)
ferramentas = load_tools(["serpapi", "llm-math"], llm=llm)
agente = create_react_agent(
    llm,
    ferramentas,
    PromptTemplate.from_template(REACT_PROMPT),
)
executor = AgentExecutor(
    agent=agente,
    tools=ferramentas,
    verbose=True,
    handle_parsing_errors=True,
)

resultado = executor.invoke({"input": pergunta})

print("\n--- Resposta ---\n")
print(resultado["output"])
