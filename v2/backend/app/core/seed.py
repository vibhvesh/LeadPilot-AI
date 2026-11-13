from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import Role, Permission

PERMISSIONS = [
    "users.view", "users.approve", "users.suspend", "roles.manage",
    "teams.manage", "leads.view", "leads.create", "leads.edit",
    "leads.assign", "leads.export", "discovery.run", "discovery.configure",
    "ai.execute", "ai.configure", "agents.execute", "reports.view",
    "audit.view", "settings.manage",
]

def seed_access_control(db: Session):
    roles = {}
    for name in ["Super Admin", "Admin", "Manager", "Member", "Viewer"]:
        role = db.scalar(select(Role).where(Role.name == name))
        if not role:
            role = Role(name=name, description=f"Built-in {name} role")
            db.add(role)
            db.flush()
        roles[name] = role
    permissions = {}
    for code in PERMISSIONS:
        permission = db.scalar(select(Permission).where(Permission.code == code))
        if not permission:
            permission = Permission(code=code, description=code.replace(".", " ").title())
            db.add(permission)
            db.flush()
        permissions[code] = permission
    roles["Super Admin"].permissions = list(permissions.values())
    roles["Admin"].permissions = [permissions[x] for x in PERMISSIONS if x not in {"users.approve", "roles.manage", "settings.manage"}]
    roles["Manager"].permissions = [permissions[x] for x in ["leads.view", "leads.create", "leads.edit", "leads.assign", "discovery.run", "reports.view"]]
    roles["Member"].permissions = [permissions[x] for x in ["leads.view", "leads.create", "leads.edit", "discovery.run", "ai.execute", "agents.execute"]]
    roles["Viewer"].permissions = [permissions[x] for x in ["leads.view", "reports.view"]]
    db.commit()
