
import uvicorn

from contextdrop.config import settings


def main():
    uvicorn.run(
        "contextdrop.api.api:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.DEBUG,
    )


if __name__ == "__main__":
    main()
