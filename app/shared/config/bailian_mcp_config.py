"""
MCP 配置模块，负责读取联网检索相关环境变量。
统一读取 MCP 基础配置，避免在业务代码里直接散落读取环境变量，为后续 MCP 能力扩展保留统一配置出口
"""

from dataclasses import dataclass

from app.shared.config.common import env_str


@dataclass
class McpConfig:
    mcp_base_url: str
    api_key: str

mcp_config = McpConfig(
    mcp_base_url=env_str("MCP_DASHSCOPE_BASE_URL"),
    api_key=env_str("OPENAI_API_KEY"),
)
