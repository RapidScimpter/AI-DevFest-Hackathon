from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    """All deployment settings come from environment variables (or a local .env)."""
    model_config = SettingsConfigDict(env_file=ROOT / '.env', env_prefix='SUROKKHA_', extra='ignore')

    database_url: str = f"sqlite:///{ROOT / 'data/surokkha.sqlite3'}"
    secret_key: str = 'dev-only-change-me-before-any-real-deployment'          # set a long random value outside local development
    token_minutes: int = 60
    cookie_secure: bool = False                     # set true behind HTTPS
    environment: str = 'development'                # 'production' refuses the default secret key
    demo_mode: bool = True                          # enables presenter overrides for device/location
    timezone: str = 'Asia/Dhaka'
    opening_balance: int = 50_000                   # BDT, virtual money for newly registered wallets
    review_threshold: float = 0.30                  # calibrated fraud probability that routes to review
    high_threshold: float = 0.70
    max_failed_logins: int = 5
    lockout_minutes: int = 15
    cors_origins: str = ''                          # comma separated; empty = same-origin only


settings = Settings()
if settings.environment == 'production' and settings.secret_key == 'dev-only-change-me-before-any-real-deployment':
    raise RuntimeError('Set SUROKKHA_SECRET_KEY before running in production.')
