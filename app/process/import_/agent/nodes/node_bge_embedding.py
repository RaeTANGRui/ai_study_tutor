from app.shared.runtime.logger import node_log
from app.shared.utils.task_utils import add_done_task, add_running_task
from app.process.import_.agent.state import ImportGraphState, create_default_state
from app.rag.import_.embedding_service import generate_chunk_embeddings

# 向量化--使用 BGE-M3 模型将文本转换为向量 (Embedding)。
@node_log("node_bge_embedding")
def node_bge_embedding(state: ImportGraphState) -> ImportGraphState:
    add_running_task(state["task_id"], "node_bge_embedding")
    state = generate_chunk_embeddings(state)
    add_done_task(state["task_id"], "node_bge_embedding")
    return state
