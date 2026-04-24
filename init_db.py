"""Run once to create all tables."""
import asyncio
from app.core.database import engine, Base
from app.models.user import User
from app.models.recording import Recording, Feedback


async def init():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✓ Tables created")


if __name__ == "__main__":
    asyncio.run(init())
