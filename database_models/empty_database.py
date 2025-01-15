from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import asyncio

# Database connection details
DATABASE_URI = "postgresql+asyncpg://rsvpuser:123%40@localhost:5432/rsvp"

# Create an async engine
async_engine = create_async_engine(DATABASE_URI, echo=True)

# Create a session
async_session = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)

async def empty_database():
    async with async_engine.begin() as conn:
        # Fetch metadata
        metadata = MetaData()

        # Reflect all tables
        await conn.run_sync(metadata.reflect)

        # Drop all tables
        await conn.run_sync(metadata.drop_all)

        print("Database emptied successfully.")

async def main():
    await empty_database()

if __name__ == "__main__":
    asyncio.run(main())