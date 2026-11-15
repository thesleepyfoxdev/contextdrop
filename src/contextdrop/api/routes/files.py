
import json
import logging
from datetime import datetime
from urllib.parse import quote

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict

from contextdrop.config import settings
from contextdrop.core.file_manager import FileManager
from contextdrop.database.connection import SessionLocal
from contextdrop.database.repository import FileRepository


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/files", tags=["Files"])


# --------------------------------------------------
# Response schemas
# --------------------------------------------------

class FileMetadataResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    file_id: str
    user_id: str
    filename: str
    content_type: str
    size: int
    storage_provider: str
    bucket: str
    object_key: str
    custom_metadata: dict
    created_at: datetime
    updated_at: datetime


# --------------------------------------------------
# Dependencies
# --------------------------------------------------

async def get_file_manager(request: Request):
    storage = request.app.state.storage

    async with SessionLocal() as session:
        repository = FileRepository(session)

        manager = FileManager(
            repository=repository,
            storage=storage,
        )

        yield manager


def get_user_id(
    x_user_id: str = Header(..., alias="X-User-ID"),
) -> str:
    # Replace with validated authentication later.
    return x_user_id


# --------------------------------------------------
# Helpers
# --------------------------------------------------

async def get_upload_size(upload: UploadFile) -> int:
    if upload.size is not None:
        return upload.size

    current_position = upload.file.tell()
    upload.file.seek(0, 2)
    size = upload.file.tell()
    upload.file.seek(current_position)

    return size


# --------------------------------------------------
# Upload
# --------------------------------------------------

@router.post("", response_model=FileMetadataResponse)
async def upload_file(
    file: UploadFile = File(...),
    metadata: str = Form("{}"),
    user_id: str = Depends(get_user_id),
    manager: FileManager = Depends(get_file_manager),
):

    try:
        custom_metadata = json.loads(metadata)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=400,
            detail="Metadata must be valid JSON",
        )

    if not isinstance(custom_metadata, dict):
        raise HTTPException(
            status_code=400,
            detail="Metadata must be a JSON object",
        )

    try:
        size = await get_upload_size(file)

        max_size = settings.MAX_FILE_SIZE_MB * 1024 * 1024

        if size > max_size:
            raise HTTPException(
                status_code=413,
                detail="File exceeds the maximum allowed size",
            )

        record = await manager.upload(
            file_data=file.file,
            filename=file.filename or "upload",
            content_type=file.content_type or "application/octet-stream",
            size=size,
            user_id=user_id,
            custom_metadata=custom_metadata,
        )

        return record

    except HTTPException:
        raise

    except Exception:
        logger.exception("File upload failed")

        raise HTTPException(
            status_code=500,
            detail="File upload failed",
        )

    finally:
        await file.close()


# --------------------------------------------------
# List files
# --------------------------------------------------

@router.get("", response_model=list[FileMetadataResponse])
async def list_files(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user_id: str = Depends(get_user_id),
    manager: FileManager = Depends(get_file_manager),
):

    return await manager.repository.list_files(
        user_id=user_id,
        limit=limit,
        offset=offset,
    )


# --------------------------------------------------
# Get metadata
# --------------------------------------------------

@router.get(
    "/{file_id}/metadata",
    response_model=FileMetadataResponse,
)
async def get_file_metadata(
    file_id: str,
    user_id: str = Depends(get_user_id),
    manager: FileManager = Depends(get_file_manager),
):

    record = await manager.get_metadata(
        file_id=file_id,
        user_id=user_id,
    )

    if record is None:
        raise HTTPException(
            status_code=404,
            detail="File not found",
        )

    return record


# --------------------------------------------------
# Download / Stream
# --------------------------------------------------

@router.get("/{file_id}")
async def download_file(
    file_id: str,
    user_id: str = Depends(get_user_id),
    manager: FileManager = Depends(get_file_manager),
):

    record = await manager.get_metadata(
        file_id=file_id,
        user_id=user_id,
    )

    if record is None:
        raise HTTPException(
            status_code=404,
            detail="File not found",
        )

    encoded_filename = quote(record.filename, safe="")

    headers = {
        "Content-Disposition": (
            f"attachment; filename*=UTF-8''{encoded_filename}"
        ),
        "Content-Length": str(record.size),
        "X-File-ID": record.file_id,
    }

    return StreamingResponse(
        manager.stream(record),
        media_type=record.content_type,
        headers=headers,
    )


# --------------------------------------------------
# Delete
# --------------------------------------------------

@router.delete("/{file_id}")
async def delete_file(
    file_id: str,
    user_id: str = Depends(get_user_id),
    manager: FileManager = Depends(get_file_manager),
):

    try:
        deleted = await manager.delete(
            file_id=file_id,
            user_id=user_id,
        )

    except Exception:
        logger.exception("File deletion failed")

        raise HTTPException(
            status_code=500,
            detail="File deletion failed",
        )

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="File not found",
        )

    return {
        "success": True,
        "file_id": file_id,
        "message": "File deleted successfully",
    }
