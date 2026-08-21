from langgraph.graph import END, StateGraph
from app.shared.runtime.logger import logger

from app.process.import_.agent.nodes import node_bge_embedding, node_document_split, node_entry, node_import_milvus, node_item_name_recognition, node_md_img, node_file_to_md
from app.process.import_.agent.state import ImportGraphState


# 1. 创建图的构建对象 StateGraph(state)
import_graph_builder = StateGraph(ImportGraphState)


# 2. 添加图节点
import_graph_builder.add_node(node_entry)
import_graph_builder.add_node(node_file_to_md)
import_graph_builder.add_node(node_md_img)
import_graph_builder.add_node(node_document_split)
import_graph_builder.add_node(node_item_name_recognition)
import_graph_builder.add_node(node_bge_embedding)
import_graph_builder.add_node(node_import_milvus)


# 3. 添加图的边
import_graph_builder.set_entry_point("node_entry")

# 条件边的路由函数,允许我们使用全局state
def after_node_entry(state: ImportGraphState):
    route_map = {
        "is_pdf_read_enabled": "pdf",
        "is_word_read_enabled": "word",
        "is_ppt_read_enabled": "ppt",
        "is_txt_read_enabled": "txt",
        "is_md_read_enabled": "md",
    }
    for key, file_type in route_map.items():
        if state.get(key, False):
            if key == "is_md_read_enabled":
                logger.info(f"传入的文件地址:{state.get('local_file_path')},文件类型为{file_type},跳转到node_md_img节点!")
                return "node_md_img"
            logger.info(f"传入的文件地址:{state.get('local_file_path')},文件类型为{file_type},跳转到node_file_to_md节点!")
            return "node_file_to_md"
    logger.info(f"传入的文件地址:{state.get('local_file_path')},文件既不是md又不是pdf/word/ppt/txt,无法处理,直接跳到END节点!")
    return END


'''
条件边添加:
    参数1:起始节点
    参数2:路由函数(state ->判断 ->目标节点名)
    参数3:path_map ->dict->场景1:静态测试必须显示说明条件路由函数返回值对应的目标节点
'''
import_graph_builder.add_conditional_edges(
    "node_entry",                 # 参数1：从哪个节点出发
    after_node_entry,             # 参数2：路由函数（决定走哪条边）
    {                             # 参数3：路由映射表
        "node_file_to_md":"node_file_to_md",
        "node_md_img":"node_md_img",
        END:END
    }
)

# 静态边
import_graph_builder.add_edge("node_file_to_md","node_md_img")
import_graph_builder.add_edge("node_md_img", "node_document_split")
import_graph_builder.add_edge("node_document_split","node_item_name_recognition")
import_graph_builder.add_edge("node_item_name_recognition","node_bge_embedding")
import_graph_builder.add_edge("node_bge_embedding","node_import_milvus")
import_graph_builder.add_edge("node_import_milvus",END)

# 4. 编译对象即可
import_graph_app = import_graph_builder.compile()