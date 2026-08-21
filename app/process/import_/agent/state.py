from typing import TypedDict
import copy

# 【定义状态 (State)】
# 所有节点共享同一个状态对象。我们需要定义它来存储处理过程中的数据（如 PDF 路径、MD 内容、切片列表、向量等）。


class ImportGraphState(TypedDict):
    task_id:str                 # 任务唯一ID，用于追踪日志
    # --- 流程控制标记 ---        # LangGraph 图中的流程控制开关（路由标记），用于决定导入流程走哪条分支路径
    is_md_read_enabled: bool    # 是否启用 Markdown 读取路径
    is_pdf_read_enabled:bool    # 是否启用 PDF 读取路径
    is_word_read_enabled:bool   # 是否启用 Word 读取路径
    is_ppt_read_enabled:bool    # 是否启用 PPT 读取路径
    is_txt_read_enabled:bool    # 是否启用 TXT 读取路径
    # --- 路径相关 ---
    local_dir: str              # 输出目录（输出文件的文件夹地址）
    local_file_path:str         # 原始输入文件路径（不确定类型）
    file_title:str              # 文件标题（文件名去后缀）
    md_paths: list[str]         # Markdown文件路径列表（单文件也是列表）
    pdf_path: str | None        # 明确的pdf的地址
    word_path: str | None       # 明确的word的地址
    ppt_path: str | None        # 明确的ppt的地址
    txt_path: str | None        # 明确的txt的地址
    # --- 内容数据 ---
    md_content: str             # Markdown 的全文内容
    chunks:list[dict]           # 切片后的文本列表，包含 metadata
    item_name: str              # 识别出的主体名称 (如: "万用表")，用于增强检索
    # --- 数据库相关 ---
    embeddings_content: list[dict]     # 包含向量数据的列表，准备写入 Milvus


# 定义图状态的默认初始值/默认对象  模版
graph_default_state: ImportGraphState = {
    "task_id": "",
    "is_md_read_enabled": False,
    "is_pdf_read_enabled": False,
    "is_word_read_enabled": False,
    "is_ppt_read_enabled": False,
    "is_txt_read_enabled": False,
    "local_dir": "",
    "local_file_path": "",
    "pdf_path": "",
    "md_paths": [],
    "word_path": "",
    "ppt_path": "",
    "txt_path": "",
    "file_title": "",
    "md_content": "",
    "chunks": [],
    "item_name": "",
    "embeddings_content": []
}


# 创建指定参数的对象，支持覆盖 --> Returns:新的状态实例
def create_default_state(**kwargs) -> ImportGraphState:
    # Examples: state = create_default_state(task_id="task_001", local_file_path="doc.pdf")
    # Python会把所有关键字参数自动打包成一个字典：kwargs = {"task_id": "task_001", "local_file_path": "doc.pdf"}
    # 默认状态
    state = copy.deepcopy(graph_default_state) #把 kwargs 中的键值对合并到 state 中
    # 用 kwargs 覆盖默认值（逐键赋值，避免 TypedDict.update() 的类型窄化问题）
    for key, value in kwargs.items():
        state[key] = value
    # 返回创建好的状态字典实例
    return state


# 创建一个默认对象,返回一个新的状态实例，避免全局变量污染。
def get_default_state() -> ImportGraphState:
    # graph_default_state 是模块级的全局字典。如果 create_default_state() 直接返回它,所有调用方拿到的都是同一个对象，任何一处修改都会"穿透"回全局
    state = copy.deepcopy(graph_default_state)
    return state


if __name__ == "__main__":
    state1 = get_default_state()
    state2 = create_default_state(task_id = "0001")
    
'''
----------------- Note -----------------
 @dataclass -> 初始化方法 配置类和实体类。
 BaseModel -> 初始化方法 严格模式 json处理 -> fastapi。
 TypedDict -> 为 LangGraph 图的状态定义结构化的字典类型。 --> return {} TypedDict 让我们在代码中能有自动补全和类型检查。
 本质是一个类型注解工具，运行时仍然是普通 dict。作用是约束字典的键名和每个键的值类型。
 LangGraph 的状态必须是 dict，TypedDict 是唯一既能满足 dict 要求、又能提供类型提示的方案。
 与 dataclass / BaseModel 的核心区别:
    dataclass：生成 __init__ 等方法，实例用 . 访问属性（obj.task_id）
    BaseModel（Pydantic）：运行时严格校验，实例用 . 访问属性（obj.task_id）
    TypedDict：不生成任何方法，实例就是普通 dict，用 [] 访问（state["task_id"]），只在类型检查时生效

# 类式语法（推荐，更直观）
class ImportGraphState(TypedDict):
    task_id: str
    is_md_read_enabled: bool
# 函数式语法（旧式写法）
ImportGraphState = TypedDict('ImportGraphState', {
    'task_id': str,
    'is_md_read_enabled': bool
})

ImportGraphState 是"规矩"——规定状态字典长什么样；graph_default_state 是"模板"——提供一份可以复制的默认数据。
只有类型没有模板 → 每次创建状态都要手写全部字段，容易遗漏
只有模板没有类型 → IDE 无法补全，类型检查器无法校验，容易写错键名
# 类型定义（蓝图）。IDE 无法补全，类型检查器无法校验，容易写错键名class ImportGraphState(TypedDict):
'''