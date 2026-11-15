
from contextdrop.config import settings
from contextdrop.storage.minio import MinIOStorage
from contextdrop.storage.filesystem import FileSystemStorage


def create_storage():
    provider = settings.STORAGE_PROVIDER.lower()

    if provider == "minio":
        return MinIOStorage()

    if provider == "filesystem":
        return FileSystemStorage()

    raise ValueError(
        f"Unsupported storage provider: {provider}"
    )
