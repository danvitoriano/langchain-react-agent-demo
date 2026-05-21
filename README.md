# Agente ReAct com LangChain

Demo em Python de um agente **ReAct** (Reasoning + Acting) para aula / hands-on: você digita a pergunta no terminal, o agente busca na web (SerpAPI), calcula quando precisa (llm-math) e mostra o rastro de pensamento no console.

## O que demonstra

| Conceito | Implementação |
|----------|----------------|
| `temperature=0` | `ChatOpenAI(..., temperature=0)` |
| Busca web | ferramenta **serpapi** |
| Cálculo | ferramenta **llm-math** |
| Auditabilidade | `AgentExecutor(..., verbose=True)` |
| Entrada | pergunta digitada no prompt interativo |

## Requisitos

- Python 3.9+
- [OpenAI API key](https://platform.openai.com/api-keys)
- [SerpAPI key](https://serpapi.com/manage-api-key)

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

```bash
python react_demo.py
```

O script pede a pergunta no terminal, por exemplo:

```
Pergunta: Qual é a população do Brasil elevada à potência de 0.5?
```

## Referências

- [LangChain](https://www.langchain.com)
- [SerpAPI](https://serpapi.com)
- [ReAct (Yao et al., 2023)](https://arxiv.org/abs/2210.03629)

## Licença

MIT
