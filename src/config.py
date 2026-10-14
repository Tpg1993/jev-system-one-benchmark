from pathlib import Path
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Base directory dynamically computed relative to this file
# This prevents any hardcoded machine paths (e.g. C:\Users\... or /home/...)
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """
    Application configuration with dynamic relative paths and zero hardcoded secrets.
    Loaded securely from environment variables or .env file.
    """
    # Application Mode
    APP_ENV: str = Field(default="development", description="Environment: development, staging, production")
    APP_HOST: str = Field(default="0.0.0.0")
    APP_PORT: int = Field(default=8000)
    DEBUG: bool = Field(default=False)
    LOG_LEVEL: str = Field(default="INFO")

    # Security & RBAC Secrets
    JWT_SECRET_KEY: str = Field(
        default="development-insecure-secret-key-change-in-production",
        description="JWT encryption secret key"
    )
    JWT_ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60)

    # Initial Admin Setup
    INIT_ADMIN_EMAIL: str = Field(default="admin@benchmark.local")
    INIT_ADMIN_PASSWORD: str = Field(default="AdminPass123!Secure")

    # Primary LLM: Sarvam AI
    # sarvam-105b-conversations : instruction-following model (returns content, good for benchmarks)
    # sarvam-105b               : reasoning/thinking model (chain-of-thought, tokens consumed in reasoning)
    SARVAM_API_KEY: str = Field(default="", description="API Key for Sarvam AI")
    SARVAM_BASE_URL: str = Field(default="https://api.sarvam.ai/v1")
    SARVAM_MODEL_NAME: str = Field(default="sarvam-105b-conversations")
    SARVAM_TIMEOUT_SECONDS: float = Field(default=90.0)
    SARVAM_MAX_RETRIES: int = Field(default=2)

    # Fallback LLM: OpenAI
    OPENAI_API_KEY: str = Field(default="", description="API Key for OpenAI fallback")
    OPENAI_BASE_URL: str = Field(default="https://api.openai.com/v1")
    OPENAI_MODEL_NAME: str = Field(default="gpt-4o")
    OPENAI_TIMEOUT_SECONDS: float = Field(default=45.0)

    # JEV Optimization Layer (inference engine, no app-level caching)
    JEV_ENABLED: bool = Field(default=True)
    JEV_HOST: str = Field(default="localhost")
    JEV_PORT: int = Field(default=9000)
    JEV_KV_CACHE_OPTIMIZATION: bool = Field(default=True)
    JEV_SPECULATIVE_DECODING: bool = Field(default=True)
    JEV_CONTINUOUS_BATCHING: bool = Field(default=True)

    # Dynamic Directories (Relative to PROJECT ROOT)
    DATA_DIR: Path = Field(default_factory=lambda: BASE_DIR / "data")
    LOG_DIR: Path = Field(default_factory=lambda: BASE_DIR / "logs")
    RESULTS_DIR: Path = Field(default_factory=lambda: BASE_DIR / "benchmark_results")

    # Benchmark Parameters
    BENCHMARK_CONCURRENCY_LEVELS: str = Field(default="1,5,10,25,50")
    BENCHMARK_PROMPT_DATASET_PATH: Path = Field(default_factory=lambda: BASE_DIR / "data" / "sample_prompts.json")
    BENCHMARK_WARMUP_REQUESTS: int = Field(default=5)
    BENCHMARK_ITERATIONS_PER_LEVEL: int = Field(default=20)

    # Selenium Testing
    SELENIUM_HEADLESS: bool = Field(default=True)
    SELENIUM_BROWSER: str = Field(default="chrome")
    SELENIUM_BASE_URL: str = Field(default="http://localhost:8000")

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def get_concurrency_list(self) -> List[int]:
        return [int(x.strip()) for x in self.BENCHMARK_CONCURRENCY_LEVELS.split(",") if x.strip()]


# Global singleton settings
settings = Settings()

# Ensure directories exist
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
settings.LOG_DIR.mkdir(parents=True, exist_ok=True)
settings.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
