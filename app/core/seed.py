"""Idempotent startup seed: Super Admin, role permissions, quotas, workspace."""

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.permissions import DEFAULT_ROLE_PERMISSIONS, MODULE_KEYS
from app.models import LLMConfig, ProviderAccess, RolePermission, User, WorkspaceSettings
from app.search.presets import IDEAL_CUSTOMER, apply_icp_defaults, seed_presets

PROVIDERS = ("xai", "gemini", "openai", "search", "ai_search")


def seed(db: Session, settings: Settings) -> None:
    ensure_super_admin(db, settings)
    ensure_role_permissions(db)
    ensure_provider_access(db)
    ensure_workspace(db)
    ensure_llm_config(db)
    seed_presets(db)
    db.commit()


def ensure_super_admin(db: Session, settings: Settings) -> User:
    email = settings.super_admin
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(email=email, display_name="Vibhvesh", role="super_admin", status="approved")
        db.add(user)
        db.flush()
    else:
        user.role = "super_admin"
        user.status = "approved"
    return user


def ensure_role_permissions(db: Session) -> None:
    existing = db.scalars(select(RolePermission)).all()
    if not existing:
        for role, modules in DEFAULT_ROLE_PERMISSIONS.items():
            for module, flags in modules.items():
                db.add(
                    RolePermission(
                        role=role,
                        module=module,
                        can_view=flags["view"],
                        can_manage=flags["manage"],
                    )
                )
        db.flush()
        return
    for module in MODULE_KEYS:
        row = db.scalar(select(RolePermission).where(RolePermission.role == "super_admin", RolePermission.module == module))
        if row is None:
            db.add(RolePermission(role="super_admin", module=module, can_view=True, can_manage=True))
        else:
            row.can_view = True
            row.can_manage = True


def ensure_provider_access(db: Session) -> None:
    db.execute(delete(ProviderAccess).where(ProviderAccess.provider == "mock"))
    quotas = {
        "super_admin": (1000, 10000),
        "admin": (500, 5000),
        "member": (25, 250),
    }
    for role, (daily, monthly) in quotas.items():
        for provider in PROVIDERS:
            daily_quota, monthly_quota = daily, monthly
            if provider == "ai_search" and role == "member":
                daily_quota, monthly_quota = 10, 100
            row = db.scalar(
                select(ProviderAccess).where(
                    ProviderAccess.provider == provider,
                    ProviderAccess.role == role,
                    ProviderAccess.user_id.is_(None),
                )
            )
            if row is None:
                db.add(
                    ProviderAccess(
                        provider=provider,
                        role=role,
                        enabled=True,
                        daily_quota=daily_quota,
                        monthly_quota=monthly_quota,
                    )
                )


def ensure_workspace(db: Session) -> None:
    row = db.get(WorkspaceSettings, 1)
    if row is None:
        row = WorkspaceSettings(
            id=1,
            workspace_name="LinkTMS",
            product_name="CanberraAI LeadPilot",
            seller_name="LinkTMS",
            offering="We help companies staff critical roles without a long search cycle.",
            ideal_customer=IDEAL_CUSTOMER,
        )
        db.add(row)
        db.flush()
    apply_icp_defaults(row)


def ensure_llm_config(db: Session) -> None:
    config = db.get(LLMConfig, 1)
    if config is None:
        db.add(LLMConfig(id=1, primary_provider="auto", fallback_provider=""))
        return
    if config.primary_provider == "mock":
        config.primary_provider = "auto"
    if config.fallback_provider == "mock":
        config.fallback_provider = ""
