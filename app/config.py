import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    MOCK_MODE = os.getenv("MOCK_MODE", "true").lower() == "true"

    UPS_CLIENT_ID = os.getenv("UPS_CLIENT_ID", "")
    UPS_CLIENT_SECRET = os.getenv("UPS_CLIENT_SECRET", "")
    UPS_BASE_URL = "https://onlinetools.ups.com/api"

    DHL_API_KEY = os.getenv("DHL_API_KEY", "")
    DHL_API_SECRET = os.getenv("DHL_API_SECRET", "")
    DHL_BASE_URL = "https://express.api.dhl.com/mydhlapi"

    FEDEX_CLIENT_ID = os.getenv("FEDEX_CLIENT_ID", "")
    FEDEX_CLIENT_SECRET = os.getenv("FEDEX_CLIENT_SECRET", "")
    FEDEX_BASE_URL = "https://apis.fedex.com"

    USD_BRL_FALLBACK = 5.40

    # Autenticação por link mágico
    JWT_SECRET = os.getenv("JWT_SECRET", "troque-esta-chave-em-producao")
    JWT_ALGO = "HS256"
    JWT_EXPIRE_DAYS = 30
    LIMITE_SIMULACOES_POR_USUARIO = 30

    # Envio de email (Resend)
    RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
    RESEND_FROM_EMAIL = os.getenv("RESEND_FROM_EMAIL", "onboarding@resend.dev")
    SITE_URL = (os.getenv("SITE_URL") or "http://localhost:8000").strip().rstrip("/")

    # Banco de dados
    DATABASE_URL = os.getenv("DATABASE_URL") or "sqlite:///./local.db"

settings = Settings()
