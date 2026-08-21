import json

from app.process.import_.agent.state import ImportGraphState, create_default_state
from app.rag.import_.entry_service import resolve_input_file
from app.shared.runtime.logger import node_log, logger
from app.shared.utils.task_utils import add_running_task, add_done_task

@node_log("node_entry")
def node_entry(state:ImportGraphState) -> ImportGraphState:
    """
    节点: 入口节点 (node_entry)作为图的 Entry Point，负责接收外部输入并决定流程走向。
    """
    add_running_task(state["task_id"], "node_entry")
    # 这里仅负责识别文件类型和补齐基础状态，不承担重业务逻辑。
    state = resolve_input_file(state) # 调用业务
    add_done_task(state["task_id"], "node_entry")
    return state
    # 增量更新和返回 return{key:value} -->规避隐患 -> 并发节点同时修改会报错


if __name__ == '__main__':
    logger.info("===== 开始node_entry节点单元测试 =====")

    # 测试1: TXT文件
    test_state1 = create_default_state(
        task_id  = "task_task_001",
        local_file_path = "联想海豚用户手册.txt"
    )
    result_1 = node_entry(test_state1)
    logger.info(f"测试1结果: {test_state1}")
    print(f"第一次测试结果: \n {json.dumps(result_1, indent=4, ensure_ascii=False)}")

    # 测试2: MD文件
    test_state2 = create_default_state(
        task_id="test_task_002",
        local_file_path="小米用户手册.md"
    )
    result_2 = node_entry(test_state2)
    logger.info(f"测试2结果: {test_state2}")
    print(f"第二次测试结果: \n {json.dumps(result_2, indent=4, ensure_ascii=False)}")

    # 测试3: PDF文件
    test_state3 = create_default_state(
        task_id="test_task_003",
        local_file_path="万用表的使用.pdf"
    )
    result_3 = node_entry(test_state3)
    logger.info(f"测试3结果: {test_state3}")
    print(f"第三次测试结果: \n {json.dumps(result_3, indent=4, ensure_ascii=False)}")

    # 测试4: DOC文件
    test_state4 = create_default_state(
        task_id="test_task_004",
        local_file_path="联想海豚用户手册.doc"
    )
    result_4 = node_entry(test_state4)
    logger.info(f"测试4结果: {test_state4}")
    print(f"第四次测试结果: \n {json.dumps(result_4, indent=4, ensure_ascii=False)}")

    # 测试5: PPT文件
    test_state5 = create_default_state(
        task_id="test_task_005",
        local_file_path="联想海豚用户手册.ppt"
    )
    result_5 = node_entry(test_state5)
    logger.info(f"测试5结果: {test_state5}")
    print(f"第五次测试结果: \n {json.dumps(result_5, indent=4, ensure_ascii=False)}")


    # 测试6: 不支持的png类型
    test_state6 = create_default_state(
        task_id="test_task_006",
        local_file_path="万用表的使用.png"
    )
    result_6 = node_entry(test_state6)
    logger.info(f"测试6结果: {test_state6}")
    print(f"第六次测试结果: \n {json.dumps(result_6, indent=4, ensure_ascii=False)}")

    logger.info("===== 结束node_entry节点单元测试 =====")