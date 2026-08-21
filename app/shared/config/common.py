"""
配置读取公共工具，统一处理 `.env` 加载与环境变量类型转换。
"""
from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv(override=True)

_TRUE_VALUES = {"1", "true", "yes", "on"}
_FALSE_VALUES = {"0", "false", "no", "off"}


def env_str(name: str, default: str = "") -> str:
    """
    读取字符串配置。

    Args:
        name: 环境变量名称。
        default: 变量不存在时的默认值。

    Returns:
        str: 读取到的字符串值。
    """
    value = os.getenv(name)
    return value if value is not None else default


def env_bool(name: str, default: bool = False) -> bool:
    """
    读取布尔配置，兼容常见的真假值写法。

    Args:
        name: 环境变量名称。
        default: 变量不存在或为空时的默认值。

    Returns:
        bool: 转换后的布尔值。
    """
    value = os.getenv(name)
    if value is None or value == "":
        return default

    normalized = value.strip().lower()
    if normalized in _TRUE_VALUES:
        return True
    if normalized in _FALSE_VALUES:
        return False
    return default


def env_float(name: str, default: float = 0.0) -> float:
    """
    读取浮点数配置。

    Args:
        name: 环境变量名称。
        default: 变量不存在、为空或格式非法时的默认值。

    Returns:
        float: 转换后的浮点数值。
    """
    value = os.getenv(name)
    if value is None or value == "":
        return default

    try:
        return float(value)
    except ValueError:
        return default
