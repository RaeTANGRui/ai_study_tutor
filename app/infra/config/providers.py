from app.shared.config.embedding_config import embedding_config, EmbeddingConfig
from app.shared.config.lm_config import lm_config, LLMConfig
from app.shared.config.bailian_mcp_config import mcp_config, McpConfig
from app.shared.config.milvus_config import milvus_config, MilvusConfig
from app.shared.config.mineru_config import mineru_config, MinerUConfig
from app.shared.config.minio_config import minio_config, MinIOConfig
from app.shared.config.reranker_config import reranker_config, RerankerConfig
from app.shared.config.settings_config import settings, AppSettings
from dataclasses import dataclass , field

"""
配置聚合模块，负责将旧配置对象统一收口到新的基础设施出口。
"""

# todo: 意义, 体现infra的汇总作用!  之前: 使用哪个配置文件 -> shared/config  之后: 使用哪个配置 -> infra/config...


# class User1(BaseModel):
#     username:str
# @dataclass
# class User2:
#     username:str
#
# class User3:
#     username:str
#
# user3 =User3(username="xxx")
# user1 = User1(username="xxx")
# # 前端 -> "{username:xxx,password:xxx}" -> python -> class User(BaseModel): username:str , password:str
# # BaseModel 基础方法简化实例化 参数校验  以及json转换的方法 -> fastapi -> 接口函数(json "{}" -> 定义一个类型 BaseModel)
#
# User2 = User2(username="jjj")
# @dataclass 基础方法简化实例化 -> 简化实体类的使用 -> 配置类..

# todo:  --- 看视频 ---
@dataclass
class InfrastructureConfig:
    embedding_config:EmbeddingConfig = field(default_factory=lambda : embedding_config)
    lm_config:LLMConfig = field(default_factory=lambda : lm_config)
    mcp_config:McpConfig = field(default_factory=lambda : mcp_config)
    milvus_config:MilvusConfig = field(default_factory= lambda :milvus_config)
    mineru_config:MinerUConfig = field(default_factory=lambda :mineru_config)
    minio_config:MinIOConfig = field(default_factory=lambda :minio_config)
    reranker_config:RerankerConfig = field(default_factory=lambda :reranker_config)
    settings:AppSettings = field(default_factory= lambda : settings)


infra_config = InfrastructureConfig()
print(f"模型的参数:{infra_config.lm_config.base_url}")

"""
 实体类/数据类 -> 属性 -> 数据值 
   1. 实体类(TypedDict) : langgraph的state (scheme/input/output) -> node -> return {} -> 对象
   2. 实体类(BaseModel) : 简化方法 - 参数校验 - json转化 -> fastapi接口json处理
   3. 实体类 -> @dataclass : 简化方法 -> 普通的配置类实体类 
 for field embedding_config is not allowed: use default_factory 
 @dataclass / BaseModel 认为变量不安全! 一旦一方修改,另一方直接受影响!!
    infra_config -> embedding_config 
                                         -> embedding_config
    embedding_config -> embedding_config   

 解决: xxx:xxx = field(default_factory=lambda : 对象)   逃过了检查,但事实上还是同一个对象(配置文件没有修改) | 修改 copy.deepcopy()
 settings: 引用类型: 自定义类 字典 列表  值类型: 字符串 数字 bool  = field(default_factory= lambda : settings)
"""