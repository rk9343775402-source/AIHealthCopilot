from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    omniroute_base_url: str = "https://api.omniroute.ai/v1"
    omniroute_api_key: str = ""
    omniroute_model: str = "gpt-4o-mini"
    allowed_origins: str = "http://localhost:5173,https://aihealthcopilot.onrender.com"
    app_env: str = "development"
    max_upload_size: int = 10 * 1024 * 1024
    upload_dir: str = "data/uploads"
    demo_mode: bool = False

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)


settings = Settings()
