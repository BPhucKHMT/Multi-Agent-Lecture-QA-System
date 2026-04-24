import os
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from backend.app.models.user import User
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

with Session(engine) as session:
    users = session.execute(select(User)).scalars().all()
    print(f"Total users in DB: {len(users)}")
    for user in users:
        print(f"- {user.username} ({user.email})")
