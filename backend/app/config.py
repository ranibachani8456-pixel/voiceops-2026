from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    gemini_api_key: str = ''
    gnani_api_key: str = ''
    gemini_model: str = 'gemini-3-flash-preview'
    gemini_thinking_level: str = 'low'
    dataset_dir: Path = PROJECT_ROOT / 'dataset'
    runtime_dir: Path = PROJECT_ROOT / 'runtime'
    embedding_model: str = 'sentence-transformers/all-MiniLM-L6-v2'
    tts_model: str = 'timbre-v2.5'
    tts_voice: str = 'Nalini'
    language: str = 'en-IN'
    top_k: int = 5
    max_audio_bytes: int = 15 * 1024 * 1024
    max_audio_seconds: int = 60
    model_config = SettingsConfigDict(env_file=PROJECT_ROOT / '.env', extra='ignore')

    @field_validator('dataset_dir', 'runtime_dir', mode='before')
    @classmethod
    def resolve_project_path(cls, value):
        path = Path(value).expanduser()
        return (path if path.is_absolute() else PROJECT_ROOT / path).resolve()


settings = Settings()
