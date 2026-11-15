from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import BinaryIO, Iterator
from uuid import uuid4

from contextdrop.config import settings
from contextdrop.storage.base import StorageBackend


class FileSystemStorage(StorageBackend):

    def __init__(self):
        self.root = Path(settings.FILESYSTEM_ROOT).resolve()

    def _get_path(self, bucket: str, object_key: str) -> Path:
        """
        Convert bucket + object_key into a safe filesystem path.
        Prevent paths from escaping the configured storage root.
        """
        if not bucket or not object_key:
            raise ValueError("Bucket and object_key are required")

        if "\\" in bucket or "\\" in object_key:
            raise ValueError("Backslashes are not allowed in storage paths")

        path = (self.root / bucket / object_key).resolve()

        try:
            path.relative_to(self.root)
        except ValueError:
            raise ValueError("Invalid storage path")

        return path

    def initialize(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)

    def upload(
        self,
        bucket: str,
        object_key: str,
        file_data: BinaryIO,
        length: int,
        content_type: str,
    ) -> None:

        path = self._get_path(bucket, object_key)
        path.parent.mkdir(parents=True, exist_ok=True)

        # Write to a temporary file first, then atomically replace the target.
        temp_path = path.parent / f".{path.name}.{uuid4().hex}.tmp"

        try:
            bytes_written = 0

            with open(temp_path, "wb") as output:
                while True:
                    chunk = file_data.read(1024 * 1024)

                    if not chunk:
                        break

                    output.write(chunk)
                    bytes_written += len(chunk)

            if bytes_written != length:
                raise ValueError(
                    f"Expected {length} bytes but received {bytes_written}"
                )

            temp_path.replace(path)

        finally:
            if temp_path.exists():
                temp_path.unlink()

    def download(
        self,
        bucket: str,
        object_key: str,
    ) -> bytes:

        path = self._get_path(bucket, object_key)

        return path.read_bytes()

    def stream(
        self,
        bucket: str,
        object_key: str,
    ) -> Iterator[bytes]:

        path = self._get_path(bucket, object_key)

        with open(path, "rb") as file:
            while True:
                chunk = file.read(1024 * 1024)

                if not chunk:
                    break

                yield chunk

    def delete(
        self,
        bucket: str,
        object_key: str,
    ) -> None:

        path = self._get_path(bucket, object_key)
        path.unlink()

    def exists(
        self,
        bucket: str,
        object_key: str,
    ) -> bool:

        path = self._get_path(bucket, object_key)

        return path.is_file()

    def get_size(
        self,
        bucket: str,
        object_key: str,
    ) -> int:

        path = self._get_path(bucket, object_key)

        return path.stat().st_size