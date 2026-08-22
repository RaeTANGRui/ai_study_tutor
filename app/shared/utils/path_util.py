"""
应用主包 / 工具模块中的 path_util 模块，负责承载对应场景的具体实现逻辑。
"""
# app/shared/utils/path_util.py
from pathlib import Path
from dotenv import load_dotenv
import os
from pathlib import Path

def get_path_dir(ps:int = 0)->Path:
    """
    pathlib.Path 提供了 parents 属性，这是一个有序的路径上级目录迭代器，直接通过索引取值就能快速获取「上 N 级目录」
    核心规则：parents[N] 索引对应「向上的层级数」
    parents[0] → 等价于 .parent（当前路径的上 1 级目录）
    parents[1] → 等价于 .parent.parent（当前路径的上 2 级目录）
    以此类推，parents[N] → 直接获取上 N+1 级目录，索引越⼤，层级越靠上
    """
    dir_path = Path(__file__).parents[ps]
    return dir_path


def get_project_root(identifier: str = ".env") -> Path:
    # 第一步：优先读取环境变量（生产环境用）
    env_root = os.getenv("PROJECT_ROOT")
    if env_root and Path(env_root).absolute().exists():
        return Path(env_root).absolute()

    # 第二步：加载根目录的.env文件（为了后续逻辑，也可省略）
    current_dir = Path(__file__).absolute().parent
    while current_dir != current_dir.parent:
        if (current_dir / identifier).exists():
            load_dotenv(dotenv_path=current_dir / identifier)
            break
        current_dir = current_dir.parent

    # 第三步：递归查找标识（兜底，开发环境用）
    current_dir = Path(__file__).absolute().parent
    while current_dir != current_dir.parent:
        if (current_dir / identifier).exists():
            return current_dir
        current_dir = current_dir.parent

    raise FileNotFoundError(f"未找到项目根目录标识「{identifier}」，且环境变量PROJECT_ROOT未配置")


PROJECT_ROOT = get_project_root(".env")
