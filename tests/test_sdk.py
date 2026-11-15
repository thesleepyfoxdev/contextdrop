
import os
import io

import pytest

from contextdrop.sdk import ContextdropClient, ContextdropError


contextdrop_URL = os.getenv(
    "contextdrop_URL",
    "http://localhost:8000",
)

TEST_USER_ID = os.getenv(
    "contextdrop_TEST_USER_ID",
    "sdk-test-user",
)


@pytest.mark.asyncio
async def test_sdk_workflow(tmp_path):

    async with ContextdropClient(
        base_url=contextdrop_URL,
        user_id=TEST_USER_ID,
    ) as client:

        created_file_ids = []

        try:
            # ------------------------------------------
            # 1. Write text
            # ------------------------------------------

            text_result = await client.write_text(
                content="Hello from contextdrop SDK",
                filename="test.txt",
                metadata={"test": True},
            )

            text_file_id = text_result["file_id"]
            created_file_ids.append(text_file_id)

            # ------------------------------------------
            # 2. Read text
            # ------------------------------------------

            text_content = await client.read(text_file_id)

            assert isinstance(text_content, str)
            assert text_content == "Hello from contextdrop SDK"

            # Explicit text read
            explicit_text = await client.read_text(text_file_id)

            assert explicit_text == text_content

            # ------------------------------------------
            # 3. Write and read JSON
            # ------------------------------------------

            json_data = {
                "name": "contextdrop",
                "version": 1,
                "active": True,
            }

            json_result = await client.write_json(
                data=json_data,
                filename="test.json",
            )

            json_file_id = json_result["file_id"]
            created_file_ids.append(json_file_id)

            json_content = await client.read_json(json_file_id)

            assert json_content == json_data

            # ------------------------------------------
            # 4. Upload binary content
            # ------------------------------------------

            binary_content = b"\x00\x01\x02\x03binary-test-content"

            binary_result = await client.write(
                content=binary_content,
                filename="test.bin",
                content_type="application/octet-stream",
            )

            binary_file_id = binary_result["file_id"]
            created_file_ids.append(binary_file_id)

            # read() should return bytes for binary files
            binary_read = await client.read(binary_file_id)

            assert isinstance(binary_read, bytes)
            assert binary_read == binary_content

            # Explicit bytes read
            binary_bytes = await client.download_bytes(binary_file_id)

            assert binary_bytes == binary_content

            # ------------------------------------------
            # 5. Get metadata
            # ------------------------------------------

            metadata = await client.get_metadata(binary_file_id)

            assert metadata["file_id"] == binary_file_id
            assert metadata["filename"] == "test.bin"
            assert metadata["size"] == len(binary_content)

            # ------------------------------------------
            # 6. Download to disk
            # ------------------------------------------

            destination = tmp_path / "downloaded.bin"

            downloaded_path = await client.download(
                binary_file_id,
                destination,
            )

            assert downloaded_path.exists()
            assert downloaded_path.read_bytes() == binary_content

            # ------------------------------------------
            # 7. Stream file
            # ------------------------------------------

            streamed_content = bytearray()

            async for chunk in client.stream(
                binary_file_id,
                chunk_size=4,
            ):
                streamed_content.extend(chunk)

            assert bytes(streamed_content) == binary_content

            # ------------------------------------------
            # 8. List files
            # ------------------------------------------

            files = await client.list_files(
                limit=100,
                offset=0,
            )

            assert files is not None

            # ------------------------------------------
            # 9. Delete files
            # ------------------------------------------

            for file_id in created_file_ids:
                result = await client.delete(file_id)
                assert result is not None

            created_file_ids.clear()

            # Verify deletion
            with pytest.raises(ContextdropError) as exc:
                await client.get_metadata(text_file_id)

            assert exc.value.status_code == 404

        finally:
            # Clean up even when an assertion fails
            for file_id in created_file_ids:
                try:
                    await client.delete(file_id)
                except ContextdropError:
                    pass


@pytest.mark.asyncio
async def test_upload_file_object():

    async with ContextdropClient(
        base_url=contextdrop_URL,
        user_id=TEST_USER_ID,
    ) as client:

        file_id = None

        try:
            content = b"Uploaded using BytesIO"

            file_object = io.BytesIO(content)

            result = await client.upload(
                file=file_object,
                filename="memory-upload.txt",
                content_type="text/plain",
            )

            file_id = result["file_id"]

            read_content = await client.read(file_id)

            assert read_content == content.decode("utf-8")

        finally:
            if file_id:
                try:
                    await client.delete(file_id)
                except ContextdropError:
                    pass
