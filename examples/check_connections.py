
import asyncio

from sqlalchemy import text

from contextdrop.database.connection import (
    engine,
    close_database,
)

from contextdrop.storage.factory import create_storage


async def main():

    # SQLite connection test
    async with engine.begin() as conn:
        await conn.execute(text("SELECT 1"))

    print("SQLite connection successful")

    # MinIO connection test
    storage = create_storage()

    storage.initialize()

    if storage.health_check():
        print("MinIO connection successful")
    else:
        print("MinIO connection failed")

    await close_database()


if __name__ == "__main__":
    asyncio.run(main())
