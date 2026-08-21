from app.process.import_.agent.state import ImportGraphState


def parse_txt_to_markdown(state: ImportGraphState) -> ImportGraphState:
    """
    TXT 解析服务：
    1. 调用 MinerU
    2. 下载并解压解析结果
    3. 获取 Markdown 路径和正文内容
    4. 回写 md_path / md_content / local_dir
    """
    return state