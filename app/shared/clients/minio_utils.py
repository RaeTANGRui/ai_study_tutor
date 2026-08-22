"""
工具模块，负责提供 minio 相关的辅助能力。
"""
import json
from minio import Minio

from app.shared.config.minio_config import minio_config  # MinIO相关配置（端点、密钥、桶名等）
from app.shared.runtime.logger import logger            # 项目统一日志工具


# 全局MinIO客户端实例（单例模式，避免重复创建连接，提升性能）
_minio_client: Minio | None = None


# 1. 创建并返回MinIO客户端连接（私有函数，仅内部调用）读取配置文件中的MinIO参数，初始化客户端连接
def _create_minio_client() -> Minio:
    return Minio(
        endpoint=minio_config.endpoint,        # MinIO服务端点（IP:端口）
        access_key=minio_config.access_key,    # MinIO访问密钥
        secret_key=minio_config.secret_key,    # MinIO秘密密钥
        secure=minio_config.minio_secure       # 是否启用HTTPS（True/False）
    )


# 2. 生成MinIO桶的访问策略字符串（JSON格式）（私有函数，仅内部调用）
# 允许所有用户（Principal: "*"）对桶内所有对象执行读取操作（s3:GetObject）
# 图片上传后需公开访问（如MD中图片在线URL）
def _set_bucket_policy(bucket_name: str) -> str:
    # 策略模板（遵循AWS S3策略规范，MinIO兼容该规范）
    policy = {
        "Version": "2012-10-17",  # 策略版本（固定值，兼容S3标准）
        "Statement": [
            {
                "Effect": "Allow",  # 策略效果：允许访问
                "Principal": {"AWS": ["*"]},  # 授权对象：所有用户
                "Action": ["s3:GetObject"],  # 授权操作：读取桶内对象
                "Resource": [f"arn:aws:s3:::{bucket_name}/*"],  # 授权范围：桶内所有对象
            }
        ],
    }
    # 将字典策略序列化为JSON字符串，供MinIO设置使用
    return json.dumps(policy)


# 3. 定义桶初始化函数（私有函数，仅内部调用）
# 检查MinIO桶是否存在，不存在则创建，并设置访问策略,确保图片上传所需的桶已就绪，避免上传失败
def _create_bucket_ready(client: Minio):
    bucket_name = minio_config.bucket_name  # 从配置中获取目标桶名
    # 检查桶是否存在
    if not client.bucket_exists(bucket_name):
        client.make_bucket(bucket_name)  # 不存在则创建桶
        # 为新桶设置访问策略（允许公开读取，适配图片在线访问需求）
        client.set_bucket_policy(bucket_name, _set_bucket_policy(bucket_name))
        logger.info(f"MinIO桶 {bucket_name} 已创建，并设置访问策略")
    else:
        # 桶已存在，仅打印日志，不重复操作
        logger.info(f"MinIO桶 {bucket_name} 已存在，无需重复创建")


# 获取全局MinIO客户端（懒加载模式，无锁版本，适配单线程场景）
# 1. 首次调用：初始化客户端 + 检查/创建桶 + 设置策略，将客户端实例赋值给全局变量
# 2. 后续调用：直接复用全局客户端实例，避免重复创建连接（提升性能、节省资源）
def get_minio_client() -> Minio:
    # 声明使用全局变量（修改全局变量需显式声明）
    # global修改全局!
    global _minio_client

    # 懒加载：仅在客户端未初始化时执行创建逻辑
    if _minio_client is None:
        logger.info("开始初始化MinIO客户端（首次调用，执行懒加载）")
        client = _create_minio_client()          # 创建客户端连接
        _create_bucket_ready(client)             # 检查并初始化桶
        _minio_client = client                   # 赋值给全局变量，供后续复用
        logger.info("MinIO客户端初始化完成，已就绪可使用")

    # 复用全局客户端实例，直接返回
    return _minio_client
