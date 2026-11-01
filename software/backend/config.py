"""설정 파일. 비밀번호와 키는 코드에 적지 않고 .env 에서 읽는다."""
import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent

# 어느 환경인지는 터미널에서 정한다.  예) APP_ENV=production python app.py
# (.env 안에 적으면 안 된다. .env 를 고르기 전에 읽기 때문이다.)
APP_ENV = os.getenv("APP_ENV", "development")

# .env.development 같은 파일이 있으면 그걸, 없으면 .env 를 읽는다.
_env_file = BASE_DIR / f".env.{APP_ENV}"
load_dotenv(_env_file if _env_file.exists() else BASE_DIR / ".env")


def _require(name):
    """꼭 있어야 하는 값. 비어 있으면 임시값으로 때우지 않고 서버를 멈춘다."""
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"환경변수 {name} 가 비어 있어요. .env 파일에 추가해 주세요.")
    return value


class Config:
    APP_ENV = APP_ENV

    JWT_SECRET_KEY = _require("JWT_SECRET_KEY")        # 로그인 토큰 서명용
    ENCRYPTION_KEY = _require("ENCRYPTION_KEY")        # 일기 암호화용. 잃어버리면 일기를 복구할 수 없다.
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=7)

    DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
    DB_PORT = int(os.getenv("DB_PORT", "3306"))
    DB_USER = _require("DB_USER")
    DB_PASSWORD = _require("DB_PASSWORD")
    DB_NAME = os.getenv("DB_NAME", "moodnote")

    CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if o.strip()]
    MAX_CONTENT_LENGTH = 1 * 1024 * 1024               # 요청 본문 최대 1MB
