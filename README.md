# Agente ReAct com LangChain

Demo em Python de um agente **ReAct** (Reasoning + Acting) para aula / hands-on: você digita a pergunta no terminal, o agente calcula quando precisa (llm-math) e mostra o rastro de pensamento no console. Há três variantes: com busca web (SerpAPI), só com o conhecimento do modelo, ou com **tools customizadas** (tool use / function calling).

## O que demonstra

| Conceito | Implementação |
|----------|----------------|
| Agente ReAct zero-shot | `AgentType.ZERO_SHOT_REACT_DESCRIPTION` |
| `temperature=0` | `ChatOpenAI(..., temperature=0)` |
| Busca web *(opcional)* | ferramenta **serpapi** em `react_demo.py` |
| Cálculo | ferramenta **llm-math** |
| Tool use (tools próprias) | 3 `Tool` customizadas em `tool_use_demo.py` |
| Auditabilidade | `initialize_agent(..., verbose=True)` |
| Entrada | pergunta digitada no prompt interativo |

## Requisitos

- Python 3.9+
- [OpenAI API key](https://platform.openai.com/api-keys)
- [SerpAPI key](https://serpapi.com/manage-api-key) — apenas para `react_demo.py`

## Setup

```bash
git clone https://github.com/danvitoriano/langchain-react-agent-demo.git
cd langchain-react-agent-demo
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edite .env com suas chaves
```

## Executar

**Com busca web (SerpAPI + llm-math):**

```bash
python react_demo.py
```

**Sem SerpAPI (só llm-math, exige apenas `OPENAI_API_KEY`):**

```bash
python react_demo_sem_serpapi.py
```

**Tool use com ferramentas customizadas (exige apenas `OPENAI_API_KEY`):**

```bash
python tool_use_demo.py
python tool_use_demo.py "Qual o histórico de vendas do cliente 4099?"
```

Registra três `Tool` próprias (definidas em `tools_config.yaml`) e deixa o agente
escolher qual chamar: `Sistema_Legado_API` (histórico de vendas),
`Calculadora_Financeira` (juros compostos) e `Validador_Documental` (conformidade
LGPD). As funções são mocks — o foco é demonstrar o *tool use*, não o backend real.

O script pede a pergunta no terminal, por exemplo:

```
Pergunta: Qual é a população do Brasil elevada à potência de 0.5?
```

> A versão sem SerpAPI responde com o conhecimento do modelo e cálculos via `llm-math`, sem buscar dados atuais na web.

## Referências

- [LangChain](https://www.langchain.com)
- [SerpAPI](https://serpapi.com)
- [ReAct (Yao et al., 2023)](https://arxiv.org/abs/2210.03629)

## Licença

MIT
