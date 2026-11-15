# contextdrop

**Drop context, hand over an ID, pick it up anywhere.**

contextdrop is a small, backend-independent context storage service with an async Python SDK. It is built for AI agents that need to pass context to each other without stuffing it into a prompt: one agent stores a file (text, JSON, or any binary) and gets back a file ID. It hands that ID to another agent, which fetches the content when it needs it.

```
Agent A ──write──► contextdrop ──► file_id ──► Agent B ──read──► content
```

> **Status:** early development. Local use only. See [Security](#security) before exposing it on a network.

## Features

- **Simple handoff model**: store anything, get an ID, fetch it later.
- **API server + async SDK**: a FastAPI server and an `httpx`-based Python client.
- **Pluggable storage**: files can live on any file system today, with adapters planned or available for S3-compatible object stores (MinIO, SeaweedFS, AWS S3).
- **Pluggable metadata**: metadata is stored in SQLite by default and is designed to be swapped for PostgreSQL or another database.
- **Any content type**: text, JSON, and binary files, with metadata attached as a JSON object.
- **Streaming**: large files are streamed in chunks instead of loaded into memory.
- **Automatic expiry (TTL)**: files can be deleted automatically after a set time.

## Installation

Requires Python 3.11 or newer.

```bash
# From a local checkout
pip install -e ".[sdk]"       # SDK only (just httpx)
pip install -e ".[server]"    # API server
pip install -e ".[server,sdk]"

# Optional storage backends
pip install -e ".[storage-minio]"   # MinIO
pip install -e ".[storage-s3]"      # S3 via boto3
```

The base install has no dependencies, so you only pull in what you use: the SDK on the agent side, the server on the service side.

## Quick start

### 1. Start the server

```bash
contextdrop-server
```

By default the server listens locally. Check your configuration for the exact host and port.

### 2. Use the SDK

```python
import asyncio
from contextdrop.sdk import ContextdropClient


async def main():
    async with ContextdropClient("http://localhost:8000", user_id="agent-a") as client:
        # Agent A stores some context and gets back an ID
        record = await client.write_text(
            "Research notes: the three main competitors are ...",
            filename="notes.txt",
            metadata={"task": "market-research", "agent": "researcher"},
        )
        file_id = record["file_id"]
        print("Hand this to the next agent:", file_id)

    # Agent B fetches it using only the ID
    async with ContextdropClient("http://localhost:8000", user_id="agent-a") as client:
        notes = await client.read(file_id)
        print(notes)


asyncio.run(main())
```

> The import path above is illustrative. Adjust it to match where the client lives in your package.

## SDK reference

`ContextdropClient(base_url, user_id=None, timeout=300.0, headers=None)` is an async client and works as an async context manager (`async with`) or with an explicit `await client.close()`.

### Writing

| Method | Description |
|---|---|
| `write(content: bytes, filename, content_type, metadata)` | Create a file from bytes |
| `write_text(content: str, filename, metadata, encoding)` | Create a text file from a string |
| `write_json(data, filename, metadata)` | Serialize and store JSON |
| `upload(file, filename, content_type, metadata)` | Upload from a path or a binary file object |

### Reading

| Method | Description |
|---|---|
| `read(file_id)` | Returns `str` for text-like content types, `bytes` otherwise |
| `read_text(file_id)` | Always decode as text |
| `read_json(file_id)` | Parse a stored JSON file |
| `download_bytes(file_id)` | Download into memory as `bytes` |
| `download(file_id, destination)` | Stream to a file on disk |
| `stream(file_id, chunk_size)` | Async iterator over chunks |

### Managing

| Method | Description |
|---|---|
| `get_metadata(file_id)` | Filename, content type, size, storage info, custom metadata, timestamps |
| `list_files(limit=100, offset=0)` | List your files (paginated) |
| `delete(file_id)` | Delete a file and its metadata |

Errors raised by the server are surfaced as `ContextdropError`, which carries `status_code` and the raw `response`.

## HTTP API

The SDK is a thin wrapper over a plain HTTP API, so any language can use it.

| Method | Path | Description |
|---|---|---|
| `POST` | `/files` | Upload a file (multipart form: `file`, optional `metadata` JSON string) |
| `GET` | `/files` | List files (`limit` 1-500, `offset`) |
| `GET` | `/files/{file_id}` | Download / stream a file |
| `GET` | `/files/{file_id}/metadata` | Get file metadata |
| `DELETE` | `/files/{file_id}` | Delete a file |

Example with curl:

```bash
# Upload
curl -X POST http://localhost:8000/files \
  -H "X-User-ID: agent-a" \
  -F "file=@notes.txt" \
  -F 'metadata={"task": "market-research"}'

# Fetch by ID
curl -H "X-User-ID: agent-a" http://localhost:8000/files/<file_id>
```

Uploads larger than the configured `MAX_FILE_SIZE_MB` are rejected with `413`.

## Architecture

```
            ┌──────────────┐
 SDK / HTTP │  API server  │
 ──────────►│  (FastAPI)   │
            └──────┬───────┘
                   │
            ┌──────▼───────┐
            │ FileManager  │
            └───┬──────┬───┘
                │      │
      ┌─────────▼──┐ ┌─▼──────────────┐
      │  Storage   │ │ Metadata repo  │
      │  backend   │ │ (SQLAlchemy)   │
      └────────────┘ └────────────────┘
   file system, MinIO,     SQLite by default,
   SeaweedFS, S3, ...      PostgreSQL, ...
```

The core `FileManager` talks to two interfaces, a **storage backend** for file bytes and a **metadata repository** for records. Swapping either one does not change the API or the SDK.

## Use cases

- Pass large tool outputs (scrapes, query results) between agents by ID instead of through the context window.
- Hand intermediate artifacts (drafts, notes, JSON) from one stage of a multi-agent pipeline to the next.
- Checkpoint agent state so a run can resume or be picked up by another process.
- Keep short-lived scratch data that cleans itself up with a TTL.
- Replay and debug runs by storing prompts, responses, and tool calls with searchable metadata.

## Security

contextdrop is currently intended for **local use only**.

- Requests are identified by an `X-User-ID` header. This is a **temporary identity mechanism for internal testing and is not authentication**. Anyone who can reach the server can claim any user ID.
- Do not expose the server on a public or shared network until real authentication is added.
- Files are scoped per `user_id`, but this scoping is only as strong as the identity check in front of it.

## Roadmap

- [ ] Validated authentication
- [ ] Network-ready deployment
- [ ] Additional storage adapters (MinIO, SeaweedFS, S3) hardened and documented
- [ ] PostgreSQL metadata backend
- [ ] MCP server wrapper so LLM agents can call read/write as tools
- [ ] Metadata queries and tags
- [ ] Content hashing and deduplication

## Development

```bash
pip install -e ".[server,sdk,dev]"
pytest
ruff check .
```

## License

MIT