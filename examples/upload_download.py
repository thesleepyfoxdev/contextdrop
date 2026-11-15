
import asyncio
import sys

from pathlib import Path

from contextdrop.sdk import ContextdropClient


async def main(file_path: str):

    file_path = Path(file_path)

    async with ContextdropClient(
        base_url="http://localhost:8000",
        user_id="example-user",
    ) as client:

        # Upload
        result = await client.upload(file_path)

        file_id = result["file_id"]

        print("Uploaded:", file_id)

        # Metadata
        metadata = await client.get_metadata(file_id)

        print("Metadata:", metadata)

        # Download
        destination = Path("./downloads") / file_path.name

        await client.download(
            file_id,
            destination,
        )

        print("Downloaded:", destination)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python upload_download.py <file_path>")
        sys.exit(1)

    asyncio.run(main(sys.argv[1]))
