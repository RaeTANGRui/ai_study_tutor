"""
应用基础配置模块，负责读取导入服务与查询服务的启动配置。
"""
import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass
class AppSettings:
    import_app_name: str = os.getenv("IMPORT_APP_NAME", "Enterprise RAG Import Service")
    query_app_name: str = os.getenv("QUERY_APP_NAME", "Enterprise RAG Query Service")
    app_env: str = os.getenv("APP_ENV", "dev")
    app_host: str = os.getenv("APP_HOST", "0.0.0.0")
    import_app_port: int = int(os.getenv("IMPORT_APP_PORT", "8000"))
    query_app_port: int = int(os.getenv("QUERY_APP_PORT", "8001"))
    cors_origins: tuple[str, ...] = tuple(
        item.strip() for item in os.getenv("CORS_ORIGINS", "*").split(",") if item.strip()
    )

settings = AppSettings()