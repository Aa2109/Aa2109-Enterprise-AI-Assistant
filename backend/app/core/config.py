from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    APP_NAME: str = "Enterprise AI Assistant"

    APP_VERSION: str = "0.1.0"

    ENVIRONMENT: str = "development"

    DEBUG: bool = True

    HOST: str = "0.0.0.0"

    PORT: int = 8000

    DATABASE_URL: str

    LLM_PROVIDER: str = "ollama"

    LLM_MODEL: str = "qwen2.5:1.5b"   #"deepseek-r1:latest"

    OPENAI_API_KEY: str = ""

    QDRANT_URL: str

    REDIS_URL: str

    # EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

    OLLAMA_URL: str = "http://localhost:11434"

    EMBEDDING_BATCH_SIZE: int = 100

    QDRANT_HOST: str = "localhost"
    # QDRANT_HOST: str = "qdrant" # when use inside docker

    QDRANT_PORT: int = 6333

    QDRANT_COLLECTION: str = "documents"

    VECTOR_DIMENSION: int = 384   # 1536, when use openai

    VECTOR_DISTANCE: str = "COSINE"

    EMBEDDING_PROVIDER: str = "local"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
    )

settings = Settings()   