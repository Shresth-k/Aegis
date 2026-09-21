from typing import Dict, Any, Literal
from aegis.core.state import PolicyEvaluation

class PolicyEngine:
    """
    Deterministic Safety & Policy Engine.
    Enforces that high-risk production actions require human approval
    and strictly forbids dangerous/unauthorized operations.
    """

    FORBIDDEN_ACTIONS = {
        "delete_incident",
        "modify_audit_log",
        "drop_database",
        "bypass_approval",
    }

    HIGH_RISK_ACTIONS = {
        "rollback_deployment",
        "scale_down",
        "force_restart_cluster",
        "drain_node",
    }

    MEDIUM_RISK_ACTIONS = {
        "restart_service",
        "scale_up",
        "clear_cache",
    }

    READ_ONLY_ACTIONS = {
        "get_metrics",
        "get_logs",
        "get_cmdb",
        "get_service_health",
        "get_deployment_history",
    }

    @classmethod
    def evaluate(
        cls,
        action: str,
        target_service: str,
        environment: str = "production",
        severity: str = "P1",
        has_approval: bool = False
    ) -> PolicyEvaluation:
        # 1. Check for Forbidden Actions
        if action in cls.FORBIDDEN_ACTIONS:
            return PolicyEvaluation(
                action=action,
                risk_level="FORBIDDEN",
                decision="DENY",
                requires_approval=False,
                reason=f"Action '{action}' is strictly forbidden by platform security policy."
            )

        # 2. Check for Read-Only Actions
        if action in cls.READ_ONLY_ACTIONS:
            return PolicyEvaluation(
                action=action,
                risk_level="READ_ONLY",
                decision="ALLOW",
                requires_approval=False,
                reason=f"Action '{action}' is read-only and pre-approved."
            )

        # 3. Check High Risk Actions (e.g. Production Rollback)
        if action in cls.HIGH_RISK_ACTIONS or (environment == "production" and severity == "P1"):
            if not has_approval:
                return PolicyEvaluation(
                    action=action,
                    risk_level="HIGH",
                    decision="REQUIRE_APPROVAL",
                    requires_approval=True,
                    reason=f"Action '{action}' in {environment} for {target_service} is classified as HIGH risk and requires human operator approval."
                )
            else:
                return PolicyEvaluation(
                    action=action,
                    risk_level="HIGH",
                    decision="ALLOW",
                    requires_approval=True,
                    reason=f"Action '{action}' in {environment} for {target_service} was approved by a human operator."
                )

        # 4. Check Medium Risk Actions
        if action in cls.MEDIUM_RISK_ACTIONS:
            if environment == "production" and not has_approval:
                return PolicyEvaluation(
                    action=action,
                    risk_level="MEDIUM",
                    decision="REQUIRE_APPROVAL",
                    requires_approval=True,
                    reason=f"Action '{action}' in production requires operator confirmation."
                )
            return PolicyEvaluation(
                action=action,
                risk_level="MEDIUM",
                decision="ALLOW",
                requires_approval=False,
                reason=f"Action '{action}' is within automated operational tolerance."
            )

        # Default fallback: Require approval for unclassified write actions
        return PolicyEvaluation(
            action=action,
            risk_level="MEDIUM",
            decision="REQUIRE_APPROVAL" if not has_approval else "ALLOW",
            requires_approval=True,
            reason=f"Action '{action}' is unclassified and requires human sign-off."
        )

policy_engine = PolicyEngine()
