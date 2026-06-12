"""
Demo de onboarding corporativo com agente ReAct + guardrails (Aula 4 — hands-on final).

Simula um agente que processa formularios de onboarding e decide sobre aprovacao
de contratos. A versao refatorada inclui:

    1. check_active_contracts(client_id) — consulta CRM mock antes de aprovar
    2. Guardrails — conflito de exclusividade ou valor acima do limite -> HITL
    3. Observation — resultados da verificacao registrados no historico da sessao
    4. Metricas — log de decisoes (aprovado / bloqueado / human_review + motivo)

Rodar:
    pip install -r requirements.txt
    cp .env.example .env   # preencha OPENAI_API_KEY
    python onboarding_agent_demo.py
    python onboarding_agent_demo.py "Processe o onboarding do cliente 6002"
"""

from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent
CRM_PATH = ROOT / "data" / "active_contracts.json"
VALUE_LIMIT = float(os.getenv("ONBOARDING_VALUE_LIMIT", "200000"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("onboarding_agent")


# ----------------------------------------------------------------------------
# Formularios de onboarding (mock) — unica fonte visivel ao agente inicialmente.
# ----------------------------------------------------------------------------

_ONBOARDING_FORMS: dict[str, dict[str, Any]] = {
    "6002": {
        "client_id": "6002",
        "client_name": "Nova FinTech Beta",
        "annual_value": 180000,
        "clauses": {
            "exclusivity_sector": "fintech",
            "exclusivity_region": "brasil",
            "payment_terms": "anual",
        },
    },
    "7001": {
        "client_id": "7001",
        "client_name": "Mega Corp Enterprise",
        "annual_value": 350000,
        "clauses": {
            "exclusivity_sector": None,
            "exclusivity_region": None,
            "payment_terms": "anual",
        },
    },
}


class Decision(str, Enum):
    APPROVED = "aprovado"
    BLOCKED = "bloqueado"
    HUMAN_REVIEW = "enviado_para_humano"


@dataclass
class ObservationRecord:
    tool: str
    tool_input: str
    output: str
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass
class MetricRecord:
    client_id: str
    decision: Decision
    reason: str
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass
class OnboardingSession:
    """Memoria da sessao: observations do ciclo ReAct + resultados de CRM."""

    observations: list[ObservationRecord] = field(default_factory=list)
    crm_checked_for: set[str] = field(default_factory=set)
    crm_snapshots: dict[str, dict[str, Any]] = field(default_factory=dict)
    metrics: list[MetricRecord] = field(default_factory=list)

    def record_observation(self, tool: str, tool_input: str, output: str) -> None:
        record = ObservationRecord(tool=tool, tool_input=tool_input, output=output)
        self.observations.append(record)
        logger.info("Observation | tool=%s | input=%s", tool, tool_input)

    def record_crm_check(self, client_id: str, snapshot: dict[str, Any]) -> None:
        self.crm_checked_for.add(client_id)
        self.crm_snapshots[client_id] = snapshot

    def crm_was_checked(self, client_id: str) -> bool:
        return client_id in self.crm_checked_for

    def log_metric(self, client_id: str, decision: Decision, reason: str) -> None:
        record = MetricRecord(client_id=client_id, decision=decision, reason=reason)
        self.metrics.append(record)
        logger.info(
            "Metrica | client=%s | decision=%s | reason=%s",
            client_id,
            decision.value,
            reason,
        )


_session = OnboardingSession()


def reset_session() -> None:
    """Reinicia estado global — util para testes."""
    global _session
    _session = OnboardingSession()


def get_session() -> OnboardingSession:
    return _session


def load_crm_data() -> dict[str, Any]:
    with CRM_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def _normalize_client_id(raw: str) -> str:
    return raw.strip().strip('"').strip("'")


def _parse_exclusivity(clauses: dict[str, Any]) -> dict[str, str] | None:
    sector = clauses.get("exclusivity_sector")
    region = clauses.get("exclusivity_region")
    if sector and region:
        return {"sector": str(sector).lower(), "region": str(region).lower()}
    return None


def find_exclusivity_conflicts(
    new_exclusivity: dict[str, str] | None,
    crm_data: dict[str, Any],
    exclude_client_id: str | None = None,
) -> list[dict[str, Any]]:
    if not new_exclusivity:
        return []

    conflicts: list[dict[str, Any]] = []
    for contract in crm_data.get("contracts", []):
        if contract.get("status") != "active":
            continue
        if exclude_client_id and contract.get("client_id") == exclude_client_id:
            continue
        existing = contract.get("exclusivity")
        if not existing:
            continue
        if (
            existing.get("sector", "").lower() == new_exclusivity["sector"]
            and existing.get("region", "").lower() == new_exclusivity["region"]
        ):
            conflicts.append(contract)
    return conflicts


def evaluate_guardrails(
    client_id: str,
    annual_value: float,
    clauses: dict[str, Any],
    crm_data: dict[str, Any],
) -> tuple[Decision, str]:
    exclusivity = _parse_exclusivity(clauses)
    conflicts = find_exclusivity_conflicts(exclusivity, crm_data, exclude_client_id=client_id)

    if conflicts:
        other = conflicts[0]
        reason = (
            f"Conflito de exclusividade ({exclusivity['sector']}/{exclusivity['region']}) "
            f"com contrato ativo {other['contract_id']} do cliente {other['client_name']} "
            f"({other['client_id']})."
        )
        return Decision.HUMAN_REVIEW, reason

    if annual_value > VALUE_LIMIT:
        reason = (
            f"Valor anual R$ {annual_value:,.2f} acima do limite automatico "
            f"de R$ {VALUE_LIMIT:,.2f}."
        )
        return Decision.HUMAN_REVIEW, reason

    return Decision.APPROVED, "Sem conflitos de exclusividade e valor dentro do limite."


def request_human_approval(client_id: str, reason: str, form: dict[str, Any]) -> str:
    """Human-in-the-loop: pausa e pede confirmacao antes de aprovar."""
    print("\n" + "=" * 60)
    print("APROVACAO HUMANA NECESSARIA")
    print("=" * 60)
    print(f"Cliente: {form.get('client_name')} ({client_id})")
    print(f"Valor anual: R$ {form.get('annual_value'):,.2f}")
    print(f"Clausulas: {json.dumps(form.get('clauses', {}), ensure_ascii=False)}")
    print(f"Motivo: {reason}")
    print("=" * 60)

    if not sys.stdin.isatty():
        return json.dumps(
            {
                "status": "pendente_aprovacao_humana",
                "client_id": client_id,
                "reason": reason,
                "message": "Ambiente nao interativo — contrato NAO aprovado automaticamente.",
            },
            ensure_ascii=False,
        )

    resposta = input("\nAprovar manualmente este contrato? (s/n): ").strip().lower()
    if resposta in {"s", "sim", "y", "yes"}:
        return json.dumps(
            {
                "status": "aprovado_por_humano",
                "client_id": client_id,
                "approved_at": datetime.now(timezone.utc).isoformat(),
                "reason": reason,
            },
            ensure_ascii=False,
        )

    return json.dumps(
        {
            "status": "rejeitado_por_humano",
            "client_id": client_id,
            "reason": reason,
        },
        ensure_ascii=False,
    )


# ----------------------------------------------------------------------------
# Tools do agente
# ----------------------------------------------------------------------------


def ler_formulario_onboarding(client_id: str) -> str:
    """Le o formulario de onboarding pendente de um cliente."""
    cid = _normalize_client_id(client_id)
    form = _ONBOARDING_FORMS.get(cid)
    if not form:
        output = f"Nenhum formulario de onboarding encontrado para o cliente {cid}."
    else:
        output = json.dumps(form, ensure_ascii=False)

    _session.record_observation("Ler_Formulario_Onboarding", cid, output)
    return output


def check_active_contracts(client_id: str) -> str:
    """Consulta o CRM de contratos ativos e clausulas de exclusividade."""
    cid = _normalize_client_id(client_id)
    crm_data = load_crm_data()

    active = [
        c
        for c in crm_data.get("contracts", [])
        if c.get("status") == "active"
    ]
    snapshot = {
        "client_id_consultado": cid,
        "total_contratos_ativos": len(active),
        "contratos": active,
    }
    output = json.dumps(snapshot, ensure_ascii=False)

    _session.record_crm_check(cid, snapshot)
    _session.record_observation("check_active_contracts", cid, output)
    return output


def aprovar_contrato(entrada: str) -> str:
    """
    Aprova o contrato de onboarding apos verificacao no CRM.
    Entrada: client_id (string), ex: 6002.
    """
    cid = _normalize_client_id(entrada)
    form = _ONBOARDING_FORMS.get(cid)
    if not form:
        reason = f"Formulario nao encontrado para cliente {cid}."
        _session.log_metric(cid, Decision.BLOCKED, reason)
        output = json.dumps({"status": "bloqueado", "reason": reason}, ensure_ascii=False)
        _session.record_observation("Aprovar_Contrato", cid, output)
        return output

    if not _session.crm_was_checked(cid):
        reason = (
            "Aprovacao bloqueada: check_active_contracts() nao foi executado. "
            "Consulte o CRM antes de decidir (etapa Observation obrigatoria)."
        )
        _session.log_metric(cid, Decision.BLOCKED, reason)
        output = json.dumps({"status": "bloqueado", "reason": reason}, ensure_ascii=False)
        _session.record_observation("Aprovar_Contrato", cid, output)
        return output

    crm_data = load_crm_data()
    decision, reason = evaluate_guardrails(
        cid,
        float(form["annual_value"]),
        form.get("clauses", {}),
        crm_data,
    )

    if decision == Decision.HUMAN_REVIEW:
        _session.log_metric(cid, Decision.HUMAN_REVIEW, reason)
        output = request_human_approval(cid, reason, form)
        _session.record_observation("Aprovar_Contrato", cid, output)
        return output

    _session.log_metric(cid, Decision.APPROVED, reason)
    output = json.dumps(
        {
            "status": "aprovado_automaticamente",
            "client_id": cid,
            "contract_id": f"CTR-NEW-{cid}",
            "reason": reason,
        },
        ensure_ascii=False,
    )
    _session.record_observation("Aprovar_Contrato", cid, output)
    return output


def build_tools():
    from langchain_core.tools import Tool

    return [
        Tool(
            name="Ler_Formulario_Onboarding",
            func=ler_formulario_onboarding,
            description=(
                "Le o formulario de onboarding pendente de um cliente corporativo. "
                "Entrada: client_id (string), ex: 6002."
            ),
        ),
        Tool(
            name="check_active_contracts",
            func=check_active_contracts,
            description=(
                "OBRIGATORIO antes de aprovar qualquer contrato. "
                "Consulta o CRM de contratos ativos e clausulas de exclusividade. "
                "Entrada: client_id (string) do cliente em onboarding, ex: 6002."
            ),
        ),
        Tool(
            name="Aprovar_Contrato",
            func=aprovar_contrato,
            description=(
                "Aprova o contrato de onboarding SOMENTE apos chamar check_active_contracts. "
                "Entrada: client_id (string), ex: 6002."
            ),
        ),
    ]


def print_session_report() -> None:
    print("\n--- Historico de Observations ---\n")
    for i, obs in enumerate(_session.observations, start=1):
        print(f"[{i}] {obs.tool} @ {obs.timestamp}")
        print(f"    Entrada: {obs.tool_input}")
        print(f"    Saida:   {obs.output[:200]}{'...' if len(obs.output) > 200 else ''}")

    print("\n--- Metricas de decisao ---\n")
    if not _session.metrics:
        print("(nenhuma decisao registrada)")
        return
    for m in _session.metrics:
        print(f"  client={m.client_id} | {m.decision.value} | {m.reason}")


def run_agent(pergunta: str) -> dict[str, Any]:
    if not os.getenv("OPENAI_API_KEY"):
        print("Crie o arquivo .env com OPENAI_API_KEY.")
        sys.exit(1)

    from langchain.agents import AgentType, initialize_agent
    from langchain_openai import ChatOpenAI

    modelo = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    llm = ChatOpenAI(model=modelo, temperature=0)

    executor = initialize_agent(
        build_tools(),
        llm,
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True,
        return_intermediate_steps=True,
        handle_parsing_errors=True,
        agent_kwargs={
            "prefix": (
                "Voce e um agente de onboarding de clientes corporativos. "
                "Siga SEMPRE esta ordem: "
                "1) Ler_Formulario_Onboarding para entender o pedido; "
                "2) check_active_contracts para verificar contratos ativos no CRM; "
                "3) registre mentalmente a Observation do CRM antes de decidir; "
                "4) Aprovar_Contrato somente se a verificacao foi feita. "
                "Nunca pule a consulta ao CRM."
            ),
        },
    )

    return executor.invoke({"input": pergunta})


def main() -> None:
    pergunta = " ".join(sys.argv[1:]).strip()
    if not pergunta:
        pergunta = input("\nPergunta: ").strip()
    if not pergunta:
        sys.exit(1)

    reset_session()
    resultado = run_agent(pergunta)

    passos = resultado.get("intermediate_steps", [])
    if passos:
        print("\n--- Rastro ReAct (intermediate_steps) ---\n")
        for i, (acao, observacao) in enumerate(passos, start=1):
            print(f"[{i}] {acao.tool}")
            print(f"    Entrada: {acao.tool_input}")
            print(f"    Saida:   {observacao}")

    print_session_report()

    print("\n--- Resposta ---\n")
    print(resultado["output"])


if __name__ == "__main__":
    main()
