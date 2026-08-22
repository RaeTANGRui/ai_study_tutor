import os
from app.shared.runtime.logger import node_log
from app.shared.utils.task_utils import add_done_task, add_running_task
from app.process.import_.agent.state import ImportGraphState, create_default_state
from app.rag.import_.file_parse_service import parse_file_to_markdown
from app.shared.runtime.logger import logger, PROJECT_ROOT

@node_log("node_file_to_md")
def node_file_to_md(state: ImportGraphState) -> ImportGraphState:
    add_running_task(state["task_id"], "node_file_to_md")
    state = parse_file_to_markdown(state)
    add_done_task(state["task_id"], "node_file_to_md")
    return state


if __name__ == "__main__":
    logger.info("===== 开始 node_file_to_md 节点联调测试（多文件批量上传）=====")

    test_pdf_path = os.path.join(PROJECT_ROOT, "docs", "pdf", "什么是 RAG？详细描述一个完整 RAG 系统的详细工作流程？.pdf")
    test_state = create_default_state(
        task_id="test_file2md_task_001",
        is_pdf_read_enabled=True,
        pdf_path=test_pdf_path,
        local_dir=os.path.join(PROJECT_ROOT, "output"),
    )

    result = node_file_to_md(test_state)
    logger.info(f"md_paths: {result['md_paths']}")
    logger.info(f"md_content长度: {len(result['md_content'])}")
    
    logger.info("===== 结束 node_file_to_md 节点联调测试 =====")