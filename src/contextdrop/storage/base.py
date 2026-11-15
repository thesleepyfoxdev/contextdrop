
from abc import ABC, abstractmethod
from typing import BinaryIO, Iterator


class StorageBackend(ABC):

    @abstractmethod
    def upload(
        self,
        bucket: str,
        object_key: str,
        file_data: BinaryIO,
        length: int,
        content_type: str,
    ) -> None:
        pass

    @abstractmethod
    def download(
        self,
        bucket: str,
        object_key: str,
    ) -> bytes:
        pass

    @abstractmethod
    def stream(
        self,
        bucket: str,
        object_key: str,
    ) -> Iterator[bytes]:
        pass

    @abstractmethod
    def delete(
        self,
        bucket: str,
        object_key: str,
    ) -> None:
        pass

    @abstractmethod
    def exists(
        self,
        bucket: str,
        object_key: str,
    ) -> bool:
        pass

    @abstractmethod
    def get_size(
        self,
        bucket: str,
        object_key: str,
    ) -> int:
        pass

    @abstractmethod
    def initialize(self) -> None:
        pass
