
import asyncio

from contextdrop.sdk import ContextdropClient


async def main():

    async with ContextdropClient(
        base_url="http://localhost:8000",
        user_id="example-user",
    ) as client:

        # Write generated content
        result = await client.write_text(
            content="This is a generated summary.",
            filename="summary.txt",
            metadata={
                "type": "summary",
                "source": "llm-agent",
            },
        )

        file_id = result["file_id"]

        print("Created file:", file_id)

        # Read generated content
        content = await client.read(file_id)

        print("Content:", content)

        # Write JSON
        json_result = await client.write_json(
            data={
                "summary": content,
                "status": "completed",
            },
            filename="result.json",
        )

        # Read JSON
        data = await client.read_json(json_result["file_id"])

        print("JSON:", data)


if __name__ == "__main__":
    asyncio.run(main())
