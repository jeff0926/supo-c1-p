from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-6"
    whisper_model: str = "base"

    redis_url: str = "redis://localhost:6379/0"
    database_url: str = "sqlite:///./omniclip.db"

    media_root: str = "./media"
    cors_origins: str = "http://localhost:5173"

    chunk_seconds: int = 150
    chunk_overlap_seconds: int = 30
    smoothing_window: int = 24
    reframe_fps: int = 5
    output_width: int = 1080
    output_height: int = 1920

    @property
    def media_path(self) -> Path:
        p = Path(self.media_root).resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
