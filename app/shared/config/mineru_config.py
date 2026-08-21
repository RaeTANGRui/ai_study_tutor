"""
MinerU 配置模块，负责读取文档解析服务相关环境变量。
"""
from dataclasses import dataclass

from app.shared.config.common import env_str


@dataclass
class MinerUConfig:
    base_url: str
    api_key: str


mineru_config = MinerUConfig(
    base_url=env_str("MINERU_BASE_URL"),
    api_key=env_str("MINERU_API_TOKEN"),
)
print(mineru_config)
