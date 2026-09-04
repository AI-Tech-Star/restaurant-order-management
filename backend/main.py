from fastapi import FastAPI

from src import settings


def create_app() -> FastAPI:
    app = FastAPI(title=settings.APP_NAME)
    return app


app = create_app()