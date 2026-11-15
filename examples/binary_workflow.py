
import asyncio

from contextdrop.sdk import ContextdropClient


async def main():

    async with ContextdropClient(
        base_url="http://localhost:8000",
        user_id="example-user",
    ) as client:

        # Example binary content
        binary_content = b"\x00\x01\x02\x03\x04"

        # Write binary content
        result = await client.write(
            content=binary_content,
            filename="sample.bin",
            content_type="application/octet-stream",
        )

        file_id = result["file_id"]

        # Read returns bytes for binary files
        content = await client.read(file_id)

        print("Returned type:", type(content))
        print("Content:", content)

        # Stream content
        received = bytearray()

        async for chunk in client.stream(file_id):
            received.extend(chunk)

        print("Stream matches:", bytes(received) == binary_content)

        # Delete
        await client.delete(file_id)

        print("File deleted")


if __name__ == "__main__":
    asyncio.run(main())
