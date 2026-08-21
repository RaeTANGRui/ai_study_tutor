"""
MinIO 配置模块，负责读取对象存储相关环境变量。
"""
from dataclasses import dataclass

from app.shared.config.common import env_bool, env_str


@dataclass
class MinIOConfig:
    endpoint: str
    access_key: str
    secret_key: str
    bucket_name: str
    minio_img_dir: str
    minio_secure: bool


minio_config = MinIOConfig(
    endpoint=env_str("MINIO_ENDPOINT"),
    access_key=env_str("MINIO_ACCESS_KEY"),
    secret_key=env_str("MINIO_SECRET_KEY"),
    bucket_name=env_str("MINIO_BUCKET_NAME"),
    minio_img_dir=env_str("MINIO_IMG_DIR"),
    minio_secure=env_bool("MINIO_SECURE"),
)
