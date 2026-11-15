import asyncio
from io import BytesIO

from contextdrop.database.connection import (
    SessionLocal,
    init_database,
)
from contextdrop.database.repository import FileRepository
from contextdrop.storage.factory import create_storage
from contextdrop.core.file_manager import FileManager


async def test_file_manager():

    await init_database()

    storage = create_storage()

    # Initialize storage bucket
    await asyncio.to_thread(storage.initialize)

    async with SessionLocal() as session:

        repository = FileRepository(session)

        manager = FileManager(
            repository=repository,
            storage=storage,
        )

        # Upload
        content = b"Hello from contextdrop"

        record = await manager.upload(
            file_data=BytesIO(content),
            filename="hello.txt",
            content_type="text/plain",
            size=len(content),
            user_id="user_123",
            custom_metadata={
                "category": "test",
                "chat_id": "chat_123",
            },
        )

        print("Uploaded:", record.file_id)

        # Read
        result = await manager.read(
            record.file_id,
            user_id="user_123",
        )

        print("Content:", result["data"].decode())
        print("Metadata:", result["metadata"].custom_metadata)

        # Stream
        print("Streaming:")

        async for chunk in manager.stream(
            record.file_id,
            user_id="user_123",
        ):
            print(chunk)

        # Delete
        deleted = await manager.delete(
            record.file_id,
            user_id="user_123",
        )

        print("Deleted:", deleted)


if __name__ == "__main__":
    asyncio.run(test_file_manager())