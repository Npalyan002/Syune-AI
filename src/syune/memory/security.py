"""Deterministic cognitive access control for memory resources."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class Sensitivity(str, Enum):
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    RESTRICTED = "RESTRICTED"


class DefaultAccessPolicy(str, Enum):
    SECURE_DENY = "SECURE_DENY"
    LEGACY_LOCAL_COMPATIBLE = "LEGACY_LOCAL_COMPATIBLE"


@dataclass(frozen=True, slots=True)
class Principal:
    user_id: str | None = None
    agent_id: str | None = None
    organization_id: str | None = None
    project_id: str | None = None
    department_id: str | None = None
    service_id: str | None = None

    def __post_init__(self) -> None:
        if not any((self.user_id, self.agent_id, self.service_id)):
            raise ValueError("principal requires user, agent, or service identity")
        for value in (self.user_id, self.agent_id, self.organization_id, self.project_id,
                      self.department_id, self.service_id):
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise ValueError("principal identifiers must be nonempty strings")

    @property
    def keys(self) -> frozenset[str]:
        return frozenset(f"{name}:{value}" for name, value in (
            ("user", self.user_id), ("agent", self.agent_id), ("organization", self.organization_id),
            ("project", self.project_id), ("department", self.department_id), ("service", self.service_id),
        ) if value is not None)


@dataclass(frozen=True, slots=True)
class AccessContext:
    principal: Principal | None
    purpose: str | None = None
    task_id: str | None = None
    legacy_local_compatible: bool = True


@dataclass(frozen=True, slots=True)
class SecurityEnvelope:
    owner: str | None = None
    organization_scope: str | None = None
    project_scope: str | None = None
    department_scope: str | None = None
    agent_scope: str | None = None
    allowed_principals: tuple[str, ...] = ()
    denied_principals: tuple[str, ...] = ()
    sensitivity: Sensitivity = Sensitivity.INTERNAL
    purpose_constraints: tuple[str, ...] = ()
    default_policy: DefaultAccessPolicy = DefaultAccessPolicy.SECURE_DENY
    schema_version: str = "1"

    def __post_init__(self) -> None:
        if not isinstance(self.sensitivity, Sensitivity) or not isinstance(self.default_policy, DefaultAccessPolicy):
            raise TypeError("typed security policy required")
        if set(self.allowed_principals) & set(self.denied_principals):
            # Representable conflict is intentional; evaluator applies deny precedence.
            pass


class AuthorizationDecisionCode(str, Enum):
    ALLOW_PUBLIC = "ALLOW_PUBLIC"
    ALLOW_OWNER = "ALLOW_OWNER"
    ALLOW_EXPLICIT_PRINCIPAL = "ALLOW_EXPLICIT_PRINCIPAL"
    ALLOW_SCOPE = "ALLOW_SCOPE"
    ALLOW_LEGACY_LOCAL = "ALLOW_LEGACY_LOCAL"
    DENY_EXPLICIT = "DENY_EXPLICIT"
    DENY_MISSING_PRINCIPAL = "DENY_MISSING_PRINCIPAL"
    DENY_AGENT_SCOPE = "DENY_AGENT_SCOPE"
    DENY_PROJECT_SCOPE = "DENY_PROJECT_SCOPE"
    DENY_ORGANIZATION_SCOPE = "DENY_ORGANIZATION_SCOPE"
    DENY_DEPARTMENT_SCOPE = "DENY_DEPARTMENT_SCOPE"
    DENY_PURPOSE = "DENY_PURPOSE"
    DENY_SENSITIVITY = "DENY_SENSITIVITY"
    DENY_DEFAULT = "DENY_DEFAULT"


@dataclass(frozen=True, slots=True)
class AuthorizationDecision:
    allowed: bool
    code: AuthorizationDecisionCode


@dataclass(frozen=True, slots=True)
class AccessAuditEvent:
    decision: AuthorizationDecisionCode
    principal_keys: tuple[str, ...]
    resource_id: object
    purpose: str | None
    occurred_at: datetime


def authorize(envelope: SecurityEnvelope | None, context: AccessContext | None) -> AuthorizationDecision:
    if envelope is None:
        if context is None or context.legacy_local_compatible:
            return AuthorizationDecision(True, AuthorizationDecisionCode.ALLOW_LEGACY_LOCAL)
        return AuthorizationDecision(False, AuthorizationDecisionCode.DENY_DEFAULT)
    if envelope.sensitivity is Sensitivity.PUBLIC and not envelope.purpose_constraints:
        return AuthorizationDecision(True, AuthorizationDecisionCode.ALLOW_PUBLIC)
    if context is None or context.principal is None:
        return AuthorizationDecision(False, AuthorizationDecisionCode.DENY_MISSING_PRINCIPAL)
    principal = context.principal
    keys = principal.keys
    if keys & set(envelope.denied_principals):
        return AuthorizationDecision(False, AuthorizationDecisionCode.DENY_EXPLICIT)
    if envelope.purpose_constraints and (context.purpose is None or context.purpose not in envelope.purpose_constraints):
        return AuthorizationDecision(False, AuthorizationDecisionCode.DENY_PURPOSE)
    for expected, actual, code in (
        (envelope.organization_scope, principal.organization_id, AuthorizationDecisionCode.DENY_ORGANIZATION_SCOPE),
        (envelope.project_scope, principal.project_id, AuthorizationDecisionCode.DENY_PROJECT_SCOPE),
        (envelope.department_scope, principal.department_id, AuthorizationDecisionCode.DENY_DEPARTMENT_SCOPE),
        (envelope.agent_scope, principal.agent_id, AuthorizationDecisionCode.DENY_AGENT_SCOPE),
    ):
        if expected is not None and expected != actual: return AuthorizationDecision(False, code)
    if envelope.owner in keys: return AuthorizationDecision(True, AuthorizationDecisionCode.ALLOW_OWNER)
    if keys & set(envelope.allowed_principals):
        return AuthorizationDecision(True, AuthorizationDecisionCode.ALLOW_EXPLICIT_PRINCIPAL)
    if envelope.owner is not None:
        return AuthorizationDecision(False, AuthorizationDecisionCode.DENY_DEFAULT)
    if envelope.sensitivity is Sensitivity.RESTRICTED:
        return AuthorizationDecision(False, AuthorizationDecisionCode.DENY_SENSITIVITY)
    if any((envelope.organization_scope, envelope.project_scope, envelope.department_scope, envelope.agent_scope)):
        return AuthorizationDecision(True, AuthorizationDecisionCode.ALLOW_SCOPE)
    return AuthorizationDecision(False, AuthorizationDecisionCode.DENY_DEFAULT)
