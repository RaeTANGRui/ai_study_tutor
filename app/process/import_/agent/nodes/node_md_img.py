import os

from app.shared.runtime.logger import node_log, logger
from app.shared.utils.task_utils import add_done_task, add_running_task
from app.process.import_.agent.state import ImportGraphState, create_default_state
from app.rag.import_.enrich_markdown_images import enrich_markdown_images


# 【图片处理】：处理 Markdown 中的图片资源 (Image)。
@node_log("node_md_img")
def node_md_img(state: ImportGraphState) -> ImportGraphState:
    add_running_task(state["task_id"], "node_md_img")
    state = enrich_markdown_images(state)
    add_done_task(state["task_id"], "node_md_img")
    return state

# 测试
if __name__ == "__main__":
    from app.shared.utils.path_util import PROJECT_ROOT
    logger.info(f"本地测试 - 项目根目录：{PROJECT_ROOT}")

    test_md_name1 = os.path.join(r"output/大模型的 RAG 主要用来解决什么问题？", "大模型的 RAG 主要用来解决什么问题？.md")
    test_md_name2 = os.path.join(r"output/尚硅谷大模型技术之大模型概述v1.1.7", "尚硅谷大模型技术之大模型概述v1.1.7.md")
    test_md_name3 = os.path.join(r"output/什么是 RAG？详细描述一个完整 RAG 系统的详细工作流程？", "什么是 RAG？详细描述一个完整 RAG 系统的详细工作流程？.md")
    test_md_path1 = os.path.join(PROJECT_ROOT, test_md_name1)
    test_md_path2 = os.path.join(PROJECT_ROOT, test_md_name2)
    test_md_path3 = os.path.join(PROJECT_ROOT, test_md_name3)

    test_md_paths = [test_md_path1, test_md_path2, test_md_path3]

    for test_md_path in test_md_paths:
        if not os.path.exists(test_md_path):
            logger.error(f"本地测试 - 测试文件不存在：{test_md_path}")
            continue

        test_state = create_default_state(
            md_paths=[test_md_path],
            task_id=f"test_task_{os.path.basename(test_md_path)}",
        )
        logger.info(f"开始本地测试 - MD图片处理: {test_md_path}")
        result_state = node_md_img(test_state)
        logger.info(f"本地测试完成 - 处理结果状态：{result_state}")