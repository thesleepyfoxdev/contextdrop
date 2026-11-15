
import asyncio
from typing import BinaryIO
from uuid import uuid4
from collections.abc import AsyncIterator
from contextdrop.config import settings
from contextdrop.database.repository import FileRepository
from contextdrop.storage.base import StorageBackend
from contextdrop.storage.paths import generate_object_key


class FileManager:

    def __init__(
        self,
        repository: FileRepository,
        storage: StorageBackend,
    ):
        self.repository = repository
        self.storage = storage
        self.bucket = settings.MINIO_BUCKET

    async def initialize(self):
        await asyncio.to_thread(self.storage.initialize)

    async def upload(
        self,
        *,
        file_data: BinaryIO,
        filename: str,
        content_type: str,
        size: int,
        user_id: str,
        custom_metadata: dict | None = None,
    ):

        file_id = str(uuid4())

        object_key = generate_object_key(
            user_id=user_id,
            file_id=file_id,
        )

        # 1. Upload actual file to object storage
        await asyncio.to_thread(
            self.storage.upload,
            self.bucket,
            object_key,
            file_data,
            size,
            content_type,
        )

        try:
            # 2. Save file metadata in SQLite
            record = await self.repository.create(
                file_id=file_id,
                user_id=user_id,
                filename=filename,
                content_type=content_type,
                size=size,
                storage_provider=settings.STORAGE_PROVIDER,
                bucket=self.bucket,
                object_key=object_key,
                custom_metadata=custom_metadata,
            )

            return record

        except Exception:
            # If database insertion fails, remove the uploaded object
            await asyncio.to_thread(
                self.storage.delete,
                self.bucket,
                object_key,
            )
            raise

    async def get_metadata(
        self,
        file_id: str,
        user_id: str | None = None,
    ):

        return await self.repository.get_by_id(
            file_id=file_id,
            user_id=user_id,
        )

    async def read(
        self,
        file_id: str,
        user_id: str | None = None,
    ):

        record = await self.get_metadata(file_id, user_id)

        if record is None:
            return None

        data = await asyncio.to_thread(
            self.storage.download,
            record.bucket,
            record.object_key,
        )

        return {
            "data": data,
            "metadata": record,
        }

    async def delete(
        self,
        file_id: str,
        user_id: str | None = None,
    ) -> bool:

        record = await self.get_metadata(file_id, user_id)

        if record is None:
            return False

        # Delete object first
        await asyncio.to_thread(
            self.storage.delete,
            record.bucket,
            record.object_key,
        )

        # Then delete database record
        return await self.repository.delete(
            file_id=file_id,
            user_id=user_id,
        )

    async def stream(self, record) -> AsyncIterator[bytes]:

        iterator = self.storage.stream(
            record.bucket,
            record.object_key,
        )

        sentinel = object()

        def get_next():
            return next(iterator, sentinel)

        try:
            while True:
                chunk = await asyncio.to_thread(get_next)

                if chunk is sentinel:
                    break

                yield chunk

        finally:
            await asyncio.to_thread(iterator.close)