from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    DB_HOST: str = 'localhost'
    DB_PORT: int = 5432
    DB_USER: str = 'ai_user'
    DB_PASS: str = 'ai_password'
    DB_NAME: str = 'ai_fastapi_db'

    secret_key: str = "your-secret-key-here"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # OAuth2
    google_client_id: Optional[str] = None
    google_client_secret: Optional[str] = None
    github_client_id: Optional[str] = None
    github_client_secret: Optional[str] = None
    oauth_redirect_uri: str = "http://localhost:8000/auth/callback"

    # Email settings
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    from_email: str = "noreply@yourapp.com"

    # Email confirmation
    email_confirmation_expire_minutes: int = 1440  # 24 hours

    # OpenAI
    openai_api_key: str = "your-openai-api-key"
    
    # App
    debug: bool = True
    app_url: str = "http://localhost:8000"

    class Config:
        env_file = ".env"

    @property
    def database_url(self):
        return f'postgresql+asyncpg://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}'

settings = Settings()
