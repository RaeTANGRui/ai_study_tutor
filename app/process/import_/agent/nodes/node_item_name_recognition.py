from app.shared.runtime.logger import node_log
from app.shared.utils.task_utils import add_done_task, add_running_task
from app.process.import_.agent.state import ImportGraphState
from app.rag.import_.item_name_service import recognize_and_index_item_name

@node_log("node_item_name_recognition")
def node_item_name_recognition(state: ImportGraphState) -> ImportGraphState:
    """
    节点: 主体识别 (node_item_name_recognition)
    为什么叫这个名字: 识别文档核心描述的物品/商品名称 (Item Name)。
    """
    add_running_task(state["task_id"], "node_item_name_recognition")
    state = recognize_and_index_item_name(state)
    add_done_task(state["task_id"], "node_item_name_recognition")
    return state