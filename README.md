# Agente ReAct com LangChain

Demo em Python de um agente **ReAct** (Reasoning + Acting) para aula / hands-on: busca a população do Brasil na web (SerpAPI), calcula a raiz quadrada (llm-math) e mostra o rastro de pensamento no terminal.

## O que demonstra

| Conceito | Implementação |
|----------|----------------|
| `temperature=0` | `ChatOpenAI(..., temperature=0)` |
| Busca web | ferramenta **serpapi** |
| Cálculo | ferramenta **llm-math** |
| Auditabilidade | `AgentExecutor(..., verbose=True)` |
| Missão padrão | população do Brasil ^ 0.5 |

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

Na branch `main`, uma única invocação do agente:

```bash
python react_demo.py
```

Outra pergunta:

```bash
python react_demo.py "Quantos habitantes tem São Paulo vezes 2?"
```

## Motor de persistência (hands-on)

A branch `hands-on/motor-persistencia` expõe no mesmo script o loop do slide *A lógica na prática*: até **3 tentativas** com validação e replanejamento antes de desistir.

```bash
git checkout hands-on/motor-persistencia
python react_demo.py
```

| Conceito (slide) | No código (`react_demo.py`) |
|------------------|-----------------------------|
| Motor de Persistência | `while estado_atual != "sucesso" and tentativas < MAX_TENTATIVAS` em `executar_loop_persistencia()` |
| Percepção e Ação | `realizar_acao()` → `executor.invoke(...)` |
| Observação e Feedback do ambiente | `validar_resultado()` — heurística sobre `output` |
| Replanejamento Autônomo | `ajustar_estrategia()` + incremento de `tentativas` |

Com `verbose=True` (padrão), cada tentativa ainda mostra o ciclo interno ReAct (Thought / Action / Observation). O loop externo é o **motor de persistência**; o rastro verbose é o **micro-loop** do agente dentro de cada ação.

## Referências

- [LangChain](https://www.langchain.com)
- [SerpAPI](https://serpapi.com)
- [ReAct (Yao et al., 2023)](https://arxiv.org/abs/2210.03629)

## Licença

MIT
