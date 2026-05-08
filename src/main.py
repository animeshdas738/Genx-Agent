from fastapi import FastAPI
from src.controllers.greeting_controller import router as greeting_router
from src.controllers.auth_controller import router as auth_router
from src.config import settings


app = FastAPI(title=settings.APP_TITLE)

app.include_router(greeting_router)
app.include_router(auth_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host=settings.HOST,
        port=settings.PORT,
        log_level="debug" if settings.DEBUG else "info",
    )
