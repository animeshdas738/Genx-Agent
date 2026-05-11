from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')

    # App
    APP_TITLE: str = 'Genx-Agent API'
    HOST: str = '127.0.0.1'
    PORT: int = 8000
    DEBUG: bool = False

    # JWT
    JWT_SECRET_KEY: str = 'change-me-in-production'
    JWT_ALGORITHM: str = 'HS256'
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Demo credentials (development only)
    DEMO_USERNAME: str = 'testuser'
    DEMO_PASSWORD: str = 'testpass'

    # OpenAI / LLM settings
    OPENAI_API_KEY: str | None = None
    OPENAI_MODEL: str = 'gpt-3.5-turbo'
    OPENAI_TEMPERATURE: float = 0.2
    # Database
    DATABASE_URL: str | None = None
    # If your case_vectors table lives in a schema (for example 'Agent'), set it here.
    CASE_VECTOR_SCHEMA: str = "Agent"
    # Similarity threshold for returning vector DB matches (cosine similarity)
    CASE_SIMILARITY_THRESHOLD: float = 0.5


settings = Settings()
