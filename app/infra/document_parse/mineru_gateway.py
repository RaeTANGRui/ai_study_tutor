from dataclasses import dataclass
from app.infra.config.providers import infra_config

@dataclass(frozen=True)  # 自动生成 __init__ 方法， frozen=True 代表只读，更安全
class MinerUGateway:
    # 直接声明属性 + 默认值从配置读取
    base_url: str = infra_config.mineru_config.base_url
    api_key: str = infra_config.mineru_config.api_key

mineru_gateway = MinerUGateway()
