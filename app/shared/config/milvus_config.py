"""
Milvus 配置模块，负责读取向量库相关环境变量。
"""
from dataclasses import dataclass

from app.shared.config.common import env_str


@dataclass
class MilvusConfig:
    milvus_url: str
    chunks_collection: str
    entity_name_collection: str
    item_name_collection: str

milvus_config = MilvusConfig(
    milvus_url=env_str("MILVUS_URL"),
    chunks_collection=env_str("CHUNKS_COLLECTION"),
    entity_name_collection=env_str("ENTITY_NAME_COLLECTION"),
    item_name_collection=env_str("ITEM_NAME_COLLECTION"),
)