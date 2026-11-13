from sqlalchemy import select
from app.core.config import settings
from app.core.database import SessionLocal
from app.core.seed import seed_access_control
from app.models import User, Role

def main():
    db = SessionLocal()
    try:
        seed_access_control(db)
        email = settings.super_admin_email.strip().lower()
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(email=email, status="active", is_super_admin=True)
            db.add(user)
        else:
            user.is_super_admin = True
            user.status = "active"
        role = db.scalar(select(Role).where(Role.name == "Super Admin"))
        if role and role not in user.roles:
            user.roles.append(role)
        db.commit()
    finally:
        db.close()

if __name__ == "__main__":
    main()
