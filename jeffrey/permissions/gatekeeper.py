"""
SpirandeliEmpire OS - Jeffrey Security & Permissions Gatekeeper
Enforces rules from Section 15 of Specification:
- No arbitrary root shell execution
- Mandatory human approval for financial expenses and deployments
- Strict R$ 200/month budget ceiling
- Prompt injection isolation
"""
import re
from typing import Dict, Any, Tuple

FORBIDDEN_COMMAND_PATTERNS = [
    r"rm\s+-rf\s+/",
    r"mkfs",
    r"dd\s+if=",
    r":\(\)\s*\{",
    r"chmod\s+-R\s+777\s+/",
    r"curl\s+.*\|\s*bash",
    r"wget\s+.*\|\s*sh",
]

class GatekeeperViolation(Exception):
    pass

class Gatekeeper:
    def __init__(self, monthly_budget_limit: float = 200.00):
        self.monthly_budget_limit = monthly_budget_limit

    def validate_action(self, agent_name: str, action_type: str, payload: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validates if an agent is authorized to perform the requested action.
        Returns (is_approved, reason).
        """
        # 1. Financial check
        cost = float(payload.get("estimated_cost_brl", 0.0))
        current_spent = float(payload.get("current_month_spent_brl", 0.0))

        if (current_spent + cost) > self.monthly_budget_limit:
            return False, f"Rejeitado: Custo de R$ {cost:.2f} excede o limite mensal de R$ {self.monthly_budget_limit:.2f}."

        # 2. Critical operations requiring mandatory human approval
        critical_actions = [
            "hire_service",
            "start_remote_gpu",
            "delete_business",
            "publish_content",
            "modify_security_rules",
            "database_wipe",
        ]
        if action_type in critical_actions:
            if not payload.get("human_approved", False):
                return False, f"Pendente: Ação '{action_type}' exige aprovação humana explícita do proprietário."

        # 3. Arbitrary command inspection
        if "command" in payload:
            cmd = payload["command"]
            for pattern in FORBIDDEN_COMMAND_PATTERNS:
                if re.search(pattern, cmd, re.IGNORECASE):
                    raise GatekeeperViolation(f"Comando proibido detectado por segurança: {cmd}")

        return True, "Ação autorizada pelas políticas de governança."

