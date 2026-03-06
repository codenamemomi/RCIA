from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    # API
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "RCIA API"
    VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "postgresql+asyncpg://user:password@localhost/rcia_db"
    )
    DATABASE_SYNC_URL: str = os.getenv(
        "DATABASE_SYNC_URL",
        "postgresql://user:password@localhost/rcia_db"
    )
    
    # CORS
    BACKEND_CORS_ORIGINS: list = ["http://localhost:3000", "http://localhost:8000", "http://localhost:5173"]
    
    # MCP Security
    MCP_ENABLE_SECURITY: bool = os.getenv("MCP_ENABLE_SECURITY", "True").lower() == "true"
    MCP_ALLOWED_HOSTS: list = ["localhost", "127.0.0.1", "api.konasalti.com"]
    
    # Alchemy & Gasless Transactions (ERC-4337)
    ALCHEMY_API_KEY: Optional[str] = os.getenv("ALCHEMY_API_KEY")
    ALCHEMY_POLICY_ID: Optional[str] = os.getenv("ALCHEMY_POLICY_ID")
    ALCHEMY_BUNDLER_URL: str = os.getenv("ALCHEMY_BUNDLER_URL", "https://base-sepolia.g.alchemy.com/v2/")
    USE_GASLESS_TX: bool = os.getenv("USE_GASLESS_TX", "True").lower() == "true"
    ERC4337_ENTRY_POINT: str = os.getenv("ERC4337_ENTRY_POINT", "0x5FF137D4b0FDCD49DcA30c7CF57E578a026d2789")
    ERC4337_ACCOUNT_SALT: int = int(os.getenv("ERC4337_ACCOUNT_SALT", "0"))
    ERC4337_ACCOUNT_PREFIX: str = os.getenv("ERC4337_ACCOUNT_PREFIX", "RCIA_SMART_ACCOUNT")
    
    # Redis & Celery
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", REDIS_URL)
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", REDIS_URL)
    
    # Refresh Token
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # State Machine Thresholds (Demo Responsive)
    SM_DRAWDOWN_THRESHOLD: float = 0.10 # Increased from 0.03 to allow more breathing room
    SM_VOLATILITY_HIGH: float = 0.20 # Increased from 0.12
    SM_VOLATILITY_MEDIUM: float = 0.15 # Increased from 0.08
    SM_MOMENTUM_GROWTH: float = 0.005 # Decreased from 0.02 to trigger GROWTH easier
    SM_VOLATILITY_LOW: float = 0.10 # Increased from 0.05
    
    # Market Data
    DEFAULT_EXCHANGE: str = "binance"
    CCXT_RETRY_ATTEMPTS: int = 3
    CRYPTOCOMPARE_API_URL: str = "https://min-api.cryptocompare.com/data"
    MOCK_MARKET_DATA: bool = os.getenv("MOCK_MARKET_DATA", "True").lower() == "true" or True # Forced True for demo
    
    # Trading Parameters
    MA_FAST_PERIOD: int = 7
    MA_SLOW_PERIOD: int = 25
    
    # Risk Management (Conservative)
    RISK_MAX_DRAWDOWN: float = 0.08
    RISK_DAILY_LOSS_LIMIT: float = 0.015
    RISK_MAX_EXPOSURE: float = 0.60
    
    # Phase 3: Specialized Modules
    YIELD_TARGET_APY: float = 0.05
    HEDGE_RATIO: float = 0.5
    
    # Phase 4: Blockchain & Trust Layer (ERC-8004)
    WEB3_RPC_URL: str = os.getenv("WEB3_RPC_URL", "http://localhost:8545")
    AGENT_PRIVATE_KEY: str = os.getenv("AGENT_PRIVATE_KEY", "0x9c73ddee1b22c1e0a2d90f652b43dddcc9d80600402c7a1719982c2cc2c693b7")
    AGENT_NAME: str = os.getenv("AGENT_NAME", "RCIA")
    AGENT_OWNER_ADDRESS: str = os.getenv("AGENT_OWNER_ADDRESS", "0x685655099852fDe97D59A7f93E62b069d1a3c613")
    AGENT_METADATA_URI: str = os.getenv("AGENT_METADATA_URI", "https://api.konasalti.com/rcia/agent_registration.json")
    BLOCKCHAIN_NETWORK_NAME: str = os.getenv("BLOCKCHAIN_NETWORK_NAME", "Base Sepolia")
    BLOCKCHAIN_CHAIN_ID: int = int(os.getenv("BLOCKCHAIN_CHAIN_ID", "84532"))
    SIMULATE_ON_CHAIN: bool = os.getenv("SIMULATE_ON_CHAIN", "True").lower() == "true"
    ERC8004_IDENTITY_REGISTRY: str = os.getenv("ERC8004_IDENTITY_REGISTRY", "0x0000000000000000000000000000000000000001")
    ERC8004_VALIDATION_REGISTRY: str = os.getenv("ERC8004_VALIDATION_REGISTRY", "0x0000000000000000000000000000000000000002")
    ERC8004_REPUTATION_REGISTRY: str = os.getenv("ERC8004_REPUTATION_REGISTRY", "0x0000000000000000000000000000000000000003")
    ERC8004_CAPITAL_VAULT: str = os.getenv("ERC8004_CAPITAL_VAULT", "0x0000000000000000000000000000000000000004")
    ERC8004_RISK_ROUTER: str = os.getenv("ERC8004_RISK_ROUTER", "0x0000000000000000000000000000000000000005")
    AGENT_ID: int = int(os.getenv("AGENT_ID", "1"))
    
    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
