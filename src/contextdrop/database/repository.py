from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from contextdrop.database.models import File

class FileRepository:

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        *,
        user_id: str,
        filename: str,
        content_type: str,
        size: int,
        storage_provider: str,
        bucket: str,
        object_key: str,
        custom_metadata: dict | None = None,
        file_id: str | None = None,
    ) -> File:

        file_record = File(
            file_id=file_id or str(uuid4()),
            user_id=user_id,
            filename=filename,
            content_type=content_type,
            size=size,
            storage_provider=storage_provider,
            bucket=bucket,
            object_key=object_key,
            custom_metadata=custom_metadata or {},
        )

        self.session.add(file_record)

        await self.session.commit()
        await self.session.refresh(file_record)

        return file_record

    async def get_by_id(
        self,
        file_id: str,
        user_id: str | None = None,
    ) -> File | None:

        query = select(File).where(File.file_id == file_id)

        if user_id is not None:
            query = query.where(File.user_id == user_id)

        result = await self.session.execute(query)

        return result.scalar_one_or_none()

    async def list_files(
        self,
        user_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[File]:

        query = select(File)

        if user_id is not None:
            query = query.where(File.user_id == user_id)

        query = (
            query
            .order_by(File.created_at.desc())
            .limit(limit)
            .offset(offset)
        )

        result = await self.session.execute(query)

        return list(result.scalars().all())

    async def count(
        self,
        user_id: str | None = None,
    ) -> int:

        query = select(func.count()).select_from(File)

        if user_id is not None:
            query = query.where(File.user_id == user_id)

        result = await self.session.execute(query)

        return result.scalar_one()

    # replace custom metadata with new metadata
    async def update_metadata(
        self,
        file_id: str,
        custom_metadata: dict,
        user_id: str | None = None,
    ) -> File | None:

        file_record = await self.get_by_id(file_id, user_id)

        if file_record is None:
            return None

        file_record.custom_metadata = custom_metadata
        file_record.updated_at = datetime.now(timezone.utc)

        await self.session.commit()
        await self.session.refresh(file_record)

        return file_record

    # only merge the provided metadata with existing metadata, do not overwrite the entire metadata
    async def merge_metadata(
        self,
        file_id: str,
        custom_metadata: dict,
        user_id: str | None = None,
    ) -> File | None:

        file_record = await self.get_by_id(file_id, user_id)

        if file_record is None:
            return None

        file_record.custom_metadata = {
            **(file_record.custom_metadata or {}),
            **custom_metadata,
        }
        file_record.updated_at = datetime.now(timezone.utc)

        await self.session.commit()
        await self.session.refresh(file_record)

        return file_record

    async def delete(
        self,
        file_id: str,
        user_id: str | None = None,
    ) -> bool:

        query = delete(File).where(File.file_id == file_id)

        if user_id is not None:
            query = query.where(File.user_id == user_id)

        result = await self.session.execute(query)

        await self.session.commit()

        return result.rowcount > 0