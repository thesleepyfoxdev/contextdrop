
from io import BytesIO
from typing import BinaryIO, Iterator

from minio import Minio
from minio.error import S3Error

from contextdrop.config import settings
from contextdrop.storage.base import StorageBackend


class MinIOStorage(StorageBackend):

    def __init__(self):
        self.client = Minio(
            endpoint=settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )

        self.default_bucket = settings.MINIO_BUCKET

    def initialize(self) -> None:
        if not self.client.bucket_exists(self.default_bucket):
            self.client.make_bucket(self.default_bucket)

    def upload(
        self,
        bucket: str,
        object_key: str,
        file_data: BinaryIO,
        length: int,
        content_type: str,
    ) -> None:

        self.client.put_object(
            bucket_name=bucket,
            object_name=object_key,
            data=file_data,
            length=length,
            content_type=content_type,
        )

    def download(
        self,
        bucket: str,
        object_key: str,
    ) -> bytes:

        response = self.client.get_object(
            bucket_name=bucket,
            object_name=object_key,
        )

        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def stream(
        self,
        bucket: str,
        object_key: str,
    ) -> Iterator[bytes]:

        response = self.client.get_object(
            bucket_name=bucket,
            object_name=object_key,
        )

        try:
            for chunk in response.stream(
                amt=1024 * 1024
            ):
                yield chunk
        finally:
            response.close()
            response.release_conn()

    def delete(
        self,
        bucket: str,
        object_key: str,
    ) -> None:

        self.client.remove_object(
            bucket_name=bucket,
            object_name=object_key,
        )

    def exists(
        self,
        bucket: str,
        object_key: str,
    ) -> bool:

        try:
            self.client.stat_object(
                bucket_name=bucket,
                object_name=object_key,
            )
            return True

        except S3Error as exc:
            if exc.code in ("NoSuchKey", "NoSuchObject", "NotFound"):
                return False
            raise

    def get_size(
        self,
        bucket: str,
        object_key: str,
    ) -> int:

        result = self.client.stat_object(
            bucket_name=bucket,
            object_name=object_key,
        )

        return result.size
