"""
Testes do agente de onboarding — cenario de contrato conflitante (cliente 6002).

Reproduz a falha original: exclusividade fintech/brasil ja existe no CRM (cliente 5001).
Apos a refatoracao, o agente NAO auto-aprova — envia para human-in-the-loop.

Rodar:
    python -m unittest test_onboarding_agent -v
"""

import json
import unittest

from onboarding_agent_demo import (
    Decision,
    aprovar_contrato,
    check_active_contracts,
    evaluate_guardrails,
    find_exclusivity_conflicts,
    load_crm_data,
    reset_session,
    get_session,
)


class TestExclusivityGuardrails(unittest.TestCase):
    def setUp(self) -> None:
        reset_session()

    def test_detecta_conflito_fintech_brasil(self) -> None:
        crm = load_crm_data()
        new_exclusivity = {"sector": "fintech", "region": "brasil"}
        conflicts = find_exclusivity_conflicts(new_exclusivity, crm)
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]["client_id"], "5001")
        self.assertEqual(conflicts[0]["client_name"], "FinTech Alpha Ltda")

    def test_sem_conflito_setor_diferente(self) -> None:
        crm = load_crm_data()
        new_exclusivity = {"sector": "retail", "region": "brasil"}
        conflicts = find_exclusivity_conflicts(new_exclusivity, crm)
        self.assertEqual(conflicts, [])


class TestGuardrailEvaluation(unittest.TestCase):
    def setUp(self) -> None:
        reset_session()

    def test_cliente_6002_dispara_human_review_por_exclusividade(self) -> None:
        """Cenario da aula: Nova FinTech Beta conflita com FinTech Alpha."""
        crm = load_crm_data()
        clauses = {
            "exclusivity_sector": "fintech",
            "exclusivity_region": "brasil",
        }
        decision, reason = evaluate_guardrails("6002", 180_000, clauses, crm)
        self.assertEqual(decision, Decision.HUMAN_REVIEW)
        self.assertIn("FinTech Alpha", reason)
        self.assertIn("exclusividade", reason.lower())

    def test_valor_acima_limite_dispara_human_review(self) -> None:
        crm = load_crm_data()
        clauses = {"exclusivity_sector": None, "exclusivity_region": None}
        decision, reason = evaluate_guardrails("7001", 350_000, clauses, crm)
        self.assertEqual(decision, Decision.HUMAN_REVIEW)
        self.assertIn("limite", reason.lower())


class TestApprovalFlow(unittest.TestCase):
    def setUp(self) -> None:
        reset_session()

    def test_bloqueia_aprovacao_sem_consulta_crm(self) -> None:
        resultado = json.loads(aprovar_contrato("6002"))
        self.assertEqual(resultado["status"], "bloqueado")
        self.assertIn("check_active_contracts", resultado["reason"])

        session = get_session()
        self.assertEqual(len(session.metrics), 1)
        self.assertEqual(session.metrics[0].decision, Decision.BLOCKED)

    def test_cliente_6002_nao_auto_aprova_apos_crm(self) -> None:
        """
        Fluxo completo do cenario conflitante:
        CRM consultado -> guardrail detecta conflito -> HITL (nao auto-aprovacao).
        """
        check_active_contracts("6002")
        resultado = json.loads(aprovar_contrato("6002"))

        self.assertNotEqual(resultado["status"], "aprovado_automaticamente")
        self.assertIn(
            resultado["status"],
            {"pendente_aprovacao_humana", "rejeitado_por_humano", "aprovado_por_humano"},
        )

        session = get_session()
        self.assertTrue(session.crm_was_checked("6002"))
        self.assertGreaterEqual(len(session.observations), 2)

        crm_obs = [o for o in session.observations if o.tool == "check_active_contracts"]
        approve_obs = [o for o in session.observations if o.tool == "Aprovar_Contrato"]
        self.assertEqual(len(crm_obs), 1)
        self.assertEqual(len(approve_obs), 1)
        self.assertLess(
            session.observations.index(crm_obs[0]),
            session.observations.index(approve_obs[0]),
            "Observation do CRM deve preceder a decisao de aprovacao",
        )

        self.assertEqual(session.metrics[-1].decision, Decision.HUMAN_REVIEW)
        self.assertIn("FinTech Alpha", session.metrics[-1].reason)


if __name__ == "__main__":
    unittest.main()
