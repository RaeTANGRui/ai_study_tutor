"""
JSON 格式化工具模块

提供统一的 JSON 序列化和格式化功能，确保项目中 JSON 输出的一致性
"""

import json
from typing import Any, Dict


def format_state(state: Dict[str, Any], indent: int = 4) -> str:
    """
    专门用于格式化工作流状态（ImportGraphState）

    Args:
        state: ImportGraphState 工作流状态字典
        indent: JSON 缩进空格数，默认 4

    Returns:
        格式化后的 JSON 字符串

    Example:
        >>> state = {"task_id": "001", "pdf_path": "test.pdf"}
        >>> print(format_state(state))
        {
            "task_id": "001",
            "pdf_path": "test.pdf"
        }
    """

    return json.dumps(state, indent=indent, ensure_ascii=False)


def format_json(data: Any, indent: int = 4, ensure_ascii: bool = False) -> str:
    """
    通用 JSON 格式化函数

    Args:
        data: 需要格式化的数据（字典、列表等可序列化对象）
        indent: JSON 缩进空格数，默认 4
        ensure_ascii: 是否转义非 ASCII 字符，默认 False（保留中文等字符）

    Returns:
        格式化后的 JSON 字符串

    Example:
        >>> data = {"name": "测试", "value": 123}
        >>> print(format_json(data))
        {
            "name": "测试",
            "value": 123
        }
    """
    return json.dumps(data, indent=indent, ensure_ascii=ensure_ascii)

