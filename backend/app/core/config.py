from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    APP_NAME: str = "Enterprise AI Assistant"
    APP_VERSION: str = "0.1.0"

    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    HOST: str = "0.0.0.0"
    PORT: int = 8000

    DATABASE_URL: str

    # LLM
    LLM_PROVIDER: str = "ollama"
    LLM_MODEL: str = "qwen2.5:1.5b"   #"deepseek-r1:latest"
    LLM_FALLBACK_PROVIDERS: str = ""
    LLM_FALLBACK_MODEL: str = ""
    LLM_MAX_TOKENS: int = 4096

    #OpenAI
    OPENAI_API_KEY: str = ""

    # Gemini
    GEMINI_API_KEY: str = ""

    #OpenRouter
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"

    # Ollama
    OLLAMA_URL: str = ""
    # OLLAMA_URL: str = "http://localhost:11434"

    # Vector DB
    QDRANT_URL: str
    QDRANT_HOST: str = "localhost"
    # QDRANT_HOST: str = "qdrant" # when use inside docker
    QDRANT_PORT: int = 6333

    QDRANT_COLLECTION: str = "documents"
    QDRANT_MEMORY_COLLECTION: str = "memory_vectors"

    VECTOR_DIMENSION: int = 384    # 1536 when use openai
    VECTOR_DISTANCE: str = "COSINE"

    # Embeddings
    # EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_BATCH_SIZE: int = 100
    EMBEDDING_PROVIDER: str = "local"

    # Redis
    REDIS_URL: str
    
    # Search
    SEARCH_PROVIDER: str = "tavily"
    TAVILY_API_KEY: str

    # Security
    JWT_SECRET_KEY: str = "CHANGE_ME_IN_ENV"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    CORS_ORIGINS: str = "http://localhost:3000"

    # ==================================================
    # PR-28 Reliability — centralized timeouts
    #
    # Never call an external service without a timeout.
    # Each dependency class gets its own budget — a single
    # giant timeout makes every path as slow as the worst one.
    # ==================================================

    LLM_TIMEOUT_SECONDS: float = 60.0
    RAG_TIMEOUT_SECONDS: float = 5.0
    DATABASE_TIMEOUT_SECONDS: float = 5.0
    WEB_SEARCH_TIMEOUT_SECONDS: float = 10.0
    REDIS_TIMEOUT_SECONDS: float = 2.0
    AGENT_TOTAL_TIMEOUT_SECONDS: float = 120.0

    # HTTP client (connection pooling + per-phase timeouts)
    HTTP_CONNECT_TIMEOUT_SECONDS: float = 5.0
    HTTP_WRITE_TIMEOUT_SECONDS: float = 5.0
    HTTP_POOL_TIMEOUT_SECONDS: float = 5.0
    HTTP_MAX_CONNECTIONS: int = 50
    HTTP_MAX_KEEPALIVE_CONNECTIONS: int = 20

    # ==================================================
    # PR-28 Retry policy
    # ==================================================

    RETRY_MAX_ATTEMPTS: int = 3
    RETRY_BASE_DELAY_SECONDS: float = 0.5
    RETRY_MAX_DELAY_SECONDS: float = 8.0

    # ==================================================
    # PR-28 Circuit breaker
    # ==================================================

    CIRCUIT_FAIL_MAX: int = 5
    CIRCUIT_RECOVERY_TIMEOUT_SECONDS: float = 30.0

    # ==================================================
    # PR-28 Agent safety limits
    # ==================================================

    MAX_AGENT_STEPS: int = 6
    MAX_TOOL_CALLS: int = 10
    MAX_INPUT_TOKENS: int = 12_000
    MAX_OUTPUT_TOKENS: int = 3_000
    MAX_TOTAL_TOKENS: int = 15_000
    MAX_CONTEXT_CHARS: int = 30_000
    MAX_QUERY_ROWS: int = 100

    # ==================================================
    # PR-28 Concurrency (backpressure)
    # ==================================================

    AGENT_CONCURRENCY: int = 3

    # ==================================================
    # PR-28 Response caching
    # ==================================================

    REDIS_CACHE_TTL_SECONDS: int = 300
    KNOWLEDGE_VERSION: int = 1

    @property
    def cors_origin_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.CORS_ORIGINS.split(",")
            if origin.strip()
        ]

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
    )

settings = Settings()   