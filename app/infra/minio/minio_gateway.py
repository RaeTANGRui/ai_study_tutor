"""
MinIO 门面模块，封装minio的公共模块类! 方便统一调用!
"""
from app.infra.config.providers import infra_config
from app.shared.clients.minio_utils import get_minio_client
from app.shared.runtime.logger import logger

class MinIOGateway:
    # ======== 1. 返回桶名bucket_name ========
    @property
    def bucket_name(self) -> str:
        """获取 MinIO 存储桶名称（从全局配置读取）"""
        return infra_config.minio_config.bucket_name

    # ======== 2. 暴露图片目录前缀 `image_dir` ========
    @property
    def images_prefix(self) -> str:
        """获取 MinIO 中存放图片的目录路径（从全局配置读取）"""
        return infra_config.minio_config.minio_img_dir

    # ======== 3. 提供客户端对象 `client()` ========
    @property
    def minio(self) :
        """获取 MinIO 客户端实例，用于上传、下载、查询文件等操作"""
        return get_minio_client()

    # ======== 4. 拼接图片公开地址 `build_image_url()` ========
    def build_image_url(self, object_name: str) -> str: # object_name: /upload-images/文件名/图片名.jpg
        # 根据配置决定使用 http 还是 https
        prefix = "https://" if infra_config.minio_config.minio_secure else "http://"
        image_url = f"{prefix}{infra_config.minio_config.endpoint}/{infra_config.minio_config.bucket_name}{object_name}"
        logger.info(f"为:{object_name}拼接minio的访问地址为:{image_url}")
        return image_url

# 创建全局唯一的 MinIO 网关实例，全项目复用
minio_gateway = MinIOGateway()