import asyncio

from contextdrop.database.connection import (
    SessionLocal,
    init_database,
)
from contextdrop.database.repository import FileRepository

async def test_repository():

    await init_database()

    async with SessionLocal() as session:

        repo = FileRepository(session)

        # Create a record
        file_record = await repo.create(
            user_id="user_123",
            filename="report.pdf",
            content_type="application/pdf",
            size=102400,
            storage_provider="minio",
            bucket="contextdrop",
            object_key="user_123/file_123",
            custom_metadata={
                "category": "report",
                "chat_id": "chat_123",
            },
        )

        print("Created:", file_record.file_id)

        # Retrieve
        retrieved = await repo.get_by_id(
            file_record.file_id,
            user_id="user_123",
        )

        print("Retrieved:", retrieved.filename)
        print("Metadata:", retrieved.custom_metadata)

        # Merge metadata
        updated = await repo.merge_metadata(
            file_record.file_id,
            {"project": "finance"},
            user_id="user_123",
        )

        print("Updated:", updated.custom_metadata)

        # List
        files = await repo.list_files(user_id="user_123")

        print("Files:", len(files))

        # Count
        count = await repo.count(user_id="user_123")

        print("Count:", count)

        # Delete
        deleted = await repo.delete(
            file_record.file_id,
            user_id="user_123",
        )

        print("Deleted:", deleted)


if __name__ == "__main__":
    asyncio.run(test_repository())