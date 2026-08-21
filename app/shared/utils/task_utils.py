"""
工具模块，负责提供 task 相关的辅助能力。【任务追踪】
"""
from typing import Dict, List
from .sse_utils import push_to_session

# 【负责维护任务状态和节点进度】

'''
1.  **内存管理**: 使用简单的内存字典 `_tasks_running_list` 和 `_tasks_done_list` 记录任务状态，轻量高效。
2.  **状态映射**: 维护 `_NODE_NAME_TO_CN` 字典，将技术性的节点名称（如 `node_entry`）映射为用户友好的中文名称（如 `检查文件`），方便前端展示。
3.  **懒初始化**: 通过 `_ensure_task()` 保证任务字典在首次使用时自动初始化，不要求入口节点手动提前创建。
4.  **SSE 集成**: 集成 SSE 推送机制，在需要时可以实时把任务进度推送到前端。
5.  **操作封装**: 提供 `add_running_task` 和 `add_done_task` 接口，方便各节点调用，屏蔽底层状态管理细节。
'''

# ---------------------------
# 内存态任务追踪（单进程）
# ---------------------------
# key: task_id
# value: 节点名列表（原始英文/节点ID）
_tasks_running_list: Dict[str, List[str]] = {}
_tasks_done_list: Dict[str, List[str]] = {}

# key: task_id
# value: status 字符串（如 pending/processing/completed/failed）
_tasks_status: Dict[str, str] = {}

# key: task_id
# value: 任务结果（例如 query 的 answer）
_tasks_result: Dict[str, Dict[str, str]] = {}

TASK_STATUS_PENDING = "pending"
TASK_STATUS_PROCESSING = "processing"
TASK_STATUS_COMPLETED = "completed"
TASK_STATUS_FAILED = "failed"

# 节点名 -> 中文名映射（用于前端展示）
# 说明：这里的 key 应与 LangGraph 的 add_node("xxx", ...) 中的节点名一致。
_NODE_NAME_TO_CN: Dict[str, str] = {
    "upload_file": "开始上传文件",
    "node_entry": "检查文件",
    "node_file_to_md": "文件转Markdown",
    "node_md_img": "Markdown图片处理",
    "node_item_name_recognition": "主体名称识别",
    "node_document_split": "文档切分",
    "node_bge_embedding": "向量生成",
    "node_import_kg": "导入知识图谱",
    "node_import_milvus": "导入向量库",
    "__end__": "处理完成",
    "END": "处理完成",
    # --- Query 流程节点（kb/process/query/main_graph.py）---
    "node_item_name_confirm": "确认问题产品",
    "node_answer_output": "生成答案",
    "node_rerank": "重排序",
    "node_rrf": "倒排融合",
    "node_web_search_mcp": "网络搜索",
    "node_search_embedding": "切片搜索",
    "node_search_embedding_hyde": "切片搜索(假设性文档)",
    "node_multi_search": "多路搜索",
    "node_query_kg": "查询知识图谱",
    "node_join": "多路搜索合并",
}


def _ensure_task(task_id: str) -> None:
    """确保 task_id 对应的数据结构已初始化。"""
    if task_id not in _tasks_running_list:
        _tasks_running_list[task_id] = []
    if task_id not in _tasks_done_list:
        _tasks_done_list[task_id] = []
    if task_id not in _tasks_result:
        _tasks_result[task_id] = {}


def _to_cn(node_name: str) -> str:
    """将节点名转换为中文展示名；若无映射则返回原名。"""
    return _NODE_NAME_TO_CN.get(node_name, node_name)


# 添加“正在运行”的节点任务。
def add_running_task(task_id: str, node_name: str, is_stream: bool = False) -> None:
    # - task_id: 任务ID
    # - node_name: 节点名称(节点ID)

    _ensure_task(task_id)
    running = _tasks_running_list[task_id]
    # 避免重复追加
    if node_name not in running:
        running.append(node_name)

    if is_stream:
        task_push_queue(task_id)

# 添加“已完成”的节点任务，并会把同名的“正在运行”任务删除。
def add_done_task(task_id: str, node_name: str, is_stream: bool = False) -> None:
    # - task_id: 任务ID
    # - node_name: 节点名称(节点ID)

    _ensure_task(task_id)

    # 1) 从 running 中移除同名节点（可能出现重复，移除所有）
    running = _tasks_running_list[task_id]
    _tasks_running_list[task_id] = [n for n in running if n != node_name]

    # 2) 追加到 done（保持完成顺序），避免重复
    done = _tasks_done_list[task_id]
    if node_name not in done:
        done.append(node_name)

    if is_stream:
        task_push_queue(task_id)


# 存储任务结果字段（如 answer / error）。
def set_task_result(task_id: str, key: str, value: str) -> None:
    _ensure_task(task_id)
    _tasks_result[task_id][key] = value


# 获取任务结果字段（如 answer / error）。
def get_task_result(task_id: str, key: str, default: str = "") -> str:
    _ensure_task(task_id)
    return _tasks_result.get(task_id, {}).get(key, default)


# 获取当前任务状态。
def get_task_status(task_id: str) -> str:
    # 参数：task_id: 任务ID
    # 返回：str: 状态名称；如果未设置过则返回空字符串
    return _tasks_status.get(task_id, "")


# 获取已完成节点列表（中文展示）。
def get_done_task_list(task_id: str) -> List[str]:
    _ensure_task(task_id)
    done = _tasks_done_list.get(task_id, [])
    return [_to_cn(n) for n in done]


# 获取正在运行节点列表（中文展示）。
def get_running_task_list(task_id: str) -> List[str]:
    _ensure_task(task_id)
    running = _tasks_running_list.get(task_id, [])
    return [_to_cn(n) for n in running]

# 更新任务状态。
def update_task_status(task_id: str, status_name: str, push_queue: bool = False) -> None:
    # - task_id: 任务ID
    # - status_name: 状态名称（字符串）
    
    _tasks_status[task_id] = status_name
    if push_queue:
        task_push_queue(task_id)


def task_push_queue(task_id: str):
    push_to_session(task_id, "progress", {
        "status": get_task_status(task_id),
        "done_list": get_done_task_list(task_id),
        "running_list": get_running_task_list(task_id),
    })


def clear_task(task_id: str):
    _tasks_running_list.pop(task_id, None)
    _tasks_done_list.pop(task_id, None)
    _tasks_status.pop(task_id, None)
    _tasks_result.pop(task_id, None)