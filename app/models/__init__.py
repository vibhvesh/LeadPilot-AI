"""Import every model so metadata.create_all sees the full schema."""

from app.models.agents import AgentRun
from app.models.audit import AuditEvent
from app.models.bot import BotConnection, BotMessage, BotToken, DeepSearchRequest
from app.models.identity import RolePermission, SessionToken, User, UserPermission
from app.models.leads import LEAD_STATUSES, Comment, FollowUp, Lead
from app.models.outreach import LeadEvent, OutreachMessage, OutreachTemplate
from app.models.perf import AppErrorEvent, AppErrorGroup, PerfSample
from app.models.social import SOCIAL_BUCKETS, SOCIAL_STATUSES, SocialComment, SocialItem
from app.models.providers import LLMConfig, ProviderAccess, ProviderKey, ProviderUsage
from app.models.pulse import PULSE_SOURCES, PULSE_STATUSES, PULSE_URGENCIES, PulseComment, PulseItem
from app.models.search import AiSearchRun, SearchCriteria, SearchPreset, SearchRun
from app.models.workspace import WorkspaceSettings

__all__ = [
    "AgentRun",
    "AppErrorEvent",
    "AppErrorGroup",
    "AiSearchRun",
    "AuditEvent",
    "BotConnection",
    "BotMessage",
    "BotToken",
    "DeepSearchRequest",
    "Comment",
    "FollowUp",
    "LEAD_STATUSES",
    "LLMConfig",
    "Lead",
    "ProviderAccess",
    "ProviderKey",
    "ProviderUsage",
    "PerfSample",
    "PULSE_SOURCES",
    "PULSE_STATUSES",
    "PULSE_URGENCIES",
    "PulseComment",
    "PulseItem",
    "RolePermission",
    "SOCIAL_BUCKETS",
    "SOCIAL_STATUSES",
    "SearchCriteria",
    "SearchPreset",
    "SearchRun",
    "SocialComment",
    "SocialItem",
    "SessionToken",
    "User",
    "UserPermission",
    "WorkspaceSettings",
]
