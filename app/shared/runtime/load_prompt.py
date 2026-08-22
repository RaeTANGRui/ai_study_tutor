from app.shared.runtime.logger import logger, PROJECT_ROOT

# 加载提示词并渲染变量占位符
def load_prompt(name: str, **kwargs) -> str:
    # 1. 拼接提示词路径
    prompt_path = PROJECT_ROOT / 'app'  / 'resources' / 'prompts' / f'{name}.prompt'
    # 2. 校验文件是否存在
    if not prompt_path.exists():
        raise FileNotFoundError(f"提示词文件不存在：{prompt_path.absolute()}")
    # 3. 读取纯文本提示词
    raw_prompt = prompt_path.read_text(encoding='utf-8')
    # 4. 核心：如果传了参数，渲染占位符；没传参，直接返回原文本
    if kwargs:
        rendered_prompt = raw_prompt.format(**kwargs)
        logger.debug(f"提示词渲染成功，替换变量：{list(kwargs.keys())}")
        return rendered_prompt
    return raw_prompt


if __name__ == '__main__':
    # 测试：传入参数渲染占位符（和业务代码中实际使用方式一致）
    root_folder = "hl3070使用说明书"                          # 要替换的文件名称
    image_content = ("这是图片的上文内容", "这是图片的下文内容")  # 要替换的上下文
    # 调用时传入所有需要渲染的变量（键名必须和.prompt中的占位符完全一致）
    final_prompt = load_prompt(
        name='image_summary',
        root_folder=root_folder,  # 对应{root_folder}
        image_content=image_content  # 对应{image_content[0]}、{image_content[1]}
    )
    print("渲染后的最终提示词：")
    print(final_prompt)