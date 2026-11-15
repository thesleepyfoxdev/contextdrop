
import asyncio
import io
import json
import mimetypes

from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any, BinaryIO
from urllib.parse import quote

import httpx


class ContextdropError(Exception):
    """Error returned by the contextdrop API."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response: Any = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class ContextdropClient:
    """
    Async client for the contextdrop API.

    read() returns:
        - str for recognized text content types
        - bytes for binary content types

    write() accepts bytes.
    write_text() accepts str.
    """

    TEXT_CONTENT_TYPES = {
        "application/json",
        "application/xml",
        "application/javascript",
        "application/x-yaml",
    }

    def __init__(
        self,
        base_url: str,
        user_id: str | None = None,
        timeout: float = 300.0,
        headers: dict[str, str] | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.user_id = user_id

        self.headers = headers.copy() if headers else {}

        # Temporary internal/testing identity header.
        # Replace with validated authentication before public exposure.
        if user_id:
            self.headers["X-User-ID"] = user_id

        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self.headers,
            timeout=httpx.Timeout(timeout),
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

    @staticmethod
    def _file_url(file_id: str) -> str:
        return f"/files/{quote(file_id, safe='')}"

    def _handle_error(self, response: httpx.Response) -> None:
        if response.is_success:
            return

        try:
            body = response.json()
            message = (
                body.get("detail", body)
                if isinstance(body, dict)
                else body
            )
        except ValueError:
            body = response.text
            message = body

        raise ContextdropError(
            message=str(message),
            status_code=response.status_code,
            response=body,
        )

    # --------------------------------------------------
    # Upload
    # --------------------------------------------------

    async def upload(
        self,
        file: str | Path | BinaryIO,
        filename: str | None = None,
        content_type: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:

        opened_file = None

        if isinstance(file, (str, Path)):
            file_path = Path(file)

            if not file_path.is_file():
                raise FileNotFoundError(file_path)

            filename = filename or file_path.name
            opened_file = file_path.open("rb")
            file_object = opened_file

        else:
            file_object = file
            filename = filename or getattr(file, "name", "upload")
            filename = Path(str(filename)).name

            if not hasattr(file_object, "read"):
                raise TypeError("file must be a path or binary file object")

        content_type = (
            content_type
            or mimetypes.guess_type(filename)[0]
            or "application/octet-stream"
        )

        try:
            response = await self._client.post(
                "/files",
                files={
                    "file": (filename, file_object, content_type)
                },
                data={
                    "metadata": json.dumps(metadata or {})
                },
            )

            self._handle_error(response)
            return response.json()

        finally:
            if opened_file:
                opened_file.close()

    # --------------------------------------------------
    # List files
    # --------------------------------------------------

    async def list_files(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> Any:

        response = await self._client.get(
            "/files",
            params={
                "limit": limit,
                "offset": offset,
            },
        )

        self._handle_error(response)
        return response.json()

    # --------------------------------------------------
    # Metadata
    # --------------------------------------------------

    async def get_metadata(
        self,
        file_id: str,
    ) -> dict[str, Any]:

        response = await self._client.get(
            f"{self._file_url(file_id)}/metadata"
        )

        self._handle_error(response)
        return response.json()

    # --------------------------------------------------
    # Download to disk
    # --------------------------------------------------

    async def download(
        self,
        file_id: str,
        destination: str | Path,
    ) -> Path:

        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)

        async with self._client.stream(
            "GET",
            self._file_url(file_id),
        ) as response:

            self._handle_error(response)

            with destination.open("wb") as output:
                async for chunk in response.aiter_bytes(
                    chunk_size=1024 * 1024
                ):
                    await asyncio.to_thread(output.write, chunk)

        return destination

    # --------------------------------------------------
    # Download into memory
    # --------------------------------------------------

    async def download_bytes(
        self,
        file_id: str,
    ) -> bytes:

        response = await self._client.get(
            self._file_url(file_id)
        )

        self._handle_error(response)
        return response.content

    # --------------------------------------------------
    # Stream chunks
    # --------------------------------------------------

    async def stream(
        self,
        file_id: str,
        chunk_size: int = 1024 * 1024,
    ) -> AsyncIterator[bytes]:

        async with self._client.stream(
            "GET",
            self._file_url(file_id),
        ) as response:

            self._handle_error(response)

            async for chunk in response.aiter_bytes(
                chunk_size=chunk_size
            ):
                yield chunk

    # --------------------------------------------------
    # Delete
    # --------------------------------------------------

    async def delete(
        self,
        file_id: str,
    ) -> dict[str, Any]:

        response = await self._client.delete(
            self._file_url(file_id)
        )

        self._handle_error(response)
        return response.json()

    # --------------------------------------------------
    # High-level read operations
    # --------------------------------------------------

    async def read(
        self,
        file_id: str,
        encoding: str = "utf-8",
    ) -> str | bytes:
        """
        Read a file.

        Returns str for recognized text formats,
        otherwise returns bytes.
        """

        metadata = await self.get_metadata(file_id)
        content = await self.download_bytes(file_id)

        content_type = (
            metadata.get("content_type") or ""
        ).lower().split(";")[0].strip()

        is_text = (
            content_type.startswith("text/")
            or content_type in self.TEXT_CONTENT_TYPES
        )

        if is_text:
            return content.decode(encoding)

        return content

    async def read_text(
        self,
        file_id: str,
        encoding: str = "utf-8",
    ) -> str:
        """Explicitly read and decode a file as text."""

        content = await self.download_bytes(file_id)
        return content.decode(encoding)

    async def read_json(
        self,
        file_id: str,
        encoding: str = "utf-8",
    ) -> Any:
        """Read and parse a JSON file."""

        content = await self.read_text(file_id, encoding)
        return json.loads(content)

    # --------------------------------------------------
    # High-level write operations
    # --------------------------------------------------

    async def write(
        self,
        content: bytes,
        filename: str,
        content_type: str = "application/octet-stream",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a file directly from bytes."""

        if not isinstance(content, bytes):
            raise TypeError("content must be bytes; use write_text() for strings")

        file_object = io.BytesIO(content)

        return await self.upload(
            file=file_object,
            filename=filename,
            content_type=content_type,
            metadata=metadata,
        )

    async def write_text(
        self,
        content: str,
        filename: str,
        metadata: dict[str, Any] | None = None,
        encoding: str = "utf-8",
    ) -> dict[str, Any]:
        """Create a text file directly from a string."""

        return await self.write(
            content=content.encode(encoding),
            filename=filename,
            content_type="text/plain; charset=utf-8",
            metadata=metadata,
        )

    async def write_json(
        self,
        data: Any,
        filename: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Serialize and create a JSON file."""

        content = json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        )

        return await self.write(
            content=content.encode("utf-8"),
            filename=filename,
            content_type="application/json",
            metadata=metadata,
        )
