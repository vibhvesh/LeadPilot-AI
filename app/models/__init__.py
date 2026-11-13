"""Import every model so metadata.create_all sees the full schema."""

from app.models.agents import AgentRun
from app.models.audit import AuditEvent
from app.models.identity import RolePermission, SessionToken, User, UserPermission
from app.models.leads import LEAD_STATUSES, Comment, FollowUp, Lead
from app.models.providers import LLMConfig, ProviderAccess, ProviderKey, ProviderUsage
from app.models.search import SearchCriteria, SearchRun
from app.models.workspace import WorkspaceSettings

__all__ = [
    "AgentRun",
    "AuditEvent",
    "Comment",
    "FollowUp",
    "LEAD_STATUSES",
    "LLMConfig",
    "Lead",
    "ProviderAccess",
    "ProviderKey",
    "ProviderUsage",
    "RolePermission",
    "SearchCriteria",
    "SearchRun",
    "SessionToken",
    "User",
    "UserPermission",
    "WorkspaceSettings",
]
