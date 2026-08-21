import json

from app.process.import_.agent.main_graph import import_graph_app
from app.process.import_.agent.state import create_default_state
from app.shared.runtime.logger import logger

logger.info("===== 开始测试 =====")

initial_state = create_default_state(local_file_path="万用表RS-12的使用.pdf")
final_state = None

for event in import_graph_app.stream(initial_state):
    for key, value in event.items():
        logger.info(f"节点: {key}")
        final_state = value

logger.info(f"最终状态: {json.dumps(final_state, indent=4, ensure_ascii=False)}")

logger.info("图结构:")
import_graph_app.get_graph().print_ascii()

logger.info("===== 测试结束 =====")