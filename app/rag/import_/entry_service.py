from pathlib import Path

from app.process.import_.agent.state import ImportGraphState
from app.shared.runtime.logger import logger, step_log

# 【文件类型识别与状态初始化节点（导入流程入口）】

# 记录 service 步骤开始、完成、异常
@step_log("resolve_input_file")
def resolve_input_file(state: ImportGraphState) -> ImportGraphState :
    # ================= 1. state中获取参数 local_file_path =================
    local_file_path:str = state.get("local_file_path") # -> 没有属性key也不报错

    # ================= 2. 校验文件路径是否为空，为空则直接输出警告并返回原状态 =================
    # [每个节点参数校验工作->健壮性->鲁棒性] local_file_path非空判断即可
    if not local_file_path:
        # BaseException -> Exception -> Error
        logger.error(f"local_file_path没有赋值,没有文件可以解析,业务无法继续进行,提前终止!")
        raise ValueError(f"local_file_path没有赋值,没有文件可以解析,业务无法继续进行,提前终止!")

    # ================= 3. 统一重置所有路由标记和路径 =================
    state["is_md_read_enabled"] = False
    state["is_pdf_read_enabled"] = False
    state["is_word_read_enabled"] = False
    state["is_ppt_read_enabled"] = False
    state["is_txt_read_enabled"] = False
    state["md_paths"] = []
    state["pdf_path"] = None
    state["word_path"] = None
    state["ppt_path"] = None
    state["txt_path"] = None

    # ================= 4. 根据后缀名精准命中 =================
    suffix_map = {
        ".md":   ("is_md_read_enabled",   "md_paths"),
        ".pdf":  ("is_pdf_read_enabled",  "pdf_path"),
        ".docx": ("is_word_read_enabled", "word_path"),
        ".doc":  ("is_word_read_enabled", "word_path"),
        ".ppt":  ("is_ppt_read_enabled",  "ppt_path"),
        ".pptx": ("is_ppt_read_enabled",  "ppt_path"),
        ".txt":  ("is_txt_read_enabled",  "txt_path"),
    }
    file_lower = local_file_path.lower()
    for suffix, (flag_key, path_key) in suffix_map.items():
        if file_lower.endswith(suffix):
            state[flag_key] = True
            state[path_key] = local_file_path
            break

    # ================= 6. 提取文件标题：提取 file_title =================
    local_file_path_obj:Path = Path(local_file_path) # # 类型从 str 变成了 Path对象
    file_title = local_file_path_obj.stem   # stem -> 没有后缀的名字  name -> 全名称带后缀  suffix 后缀
    state['file_title'] = file_title

    # ================= 7. 返回补全后的状态 =================
    return state