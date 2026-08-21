"""
LLM 配置模块，负责读取对话模型与视觉模型相关环境变量。
"""
from dataclasses import dataclass

from app.shared.config.common import env_float, env_str


@dataclass
class LLMConfig:
    base_url: str
    api_key: str
    lv_model: str
    llm_model: str
    llm_temperature: float


lm_config = LLMConfig(
    base_url=env_str("OPENAI_BASE_URL"),
    api_key=env_str("OPENAI_API_KEY"),
    lv_model=env_str("VL_MODEL"),
    llm_model=env_str("LLM_DEFAULT_MODEL"),
    llm_temperature=env_float("LLM_DEFAULT_TEMPERATURE"),
)
