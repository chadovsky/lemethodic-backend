"""Run once to create admin account: python create_admin.py admin@example.com yourpassword"""
import sys
from app.database import SessionLocal, engine, Base
from app.models.models import User
from app.services.auth import hash_password

Base.metadata.create_all(bind=engine)
db = SessionLocal()

email = sys.argv[1] if len(sys.argv) > 1 else input("Admin email: ")
password = sys.argv[2] if len(sys.argv) > 2 else input("Admin password: ")

if db.query(User).filter(User.email == email).first():
    print(f"User {email} already exists — setting admin flag")
    db.query(User).filter(User.email == email).update({"is_admin": True})
else:
    user = User(email=email, hashed_password=hash_password(password), full_name="Admin", is_admin=True)
    db.add(user)

db.commit()
print(f"Admin account ready: {email}")
