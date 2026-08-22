import re
from pathlib import Path

from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import StrOutputParser
from minio import Minio
from minio.datatypes import Object
from minio.deleteobjects import DeleteObject

from app.process.import_.agent.state import ImportGraphState
from app.rag.import_.config import SUPPORTED_IMAGE_EXTENSIONS, SUB_MD_CONTENT_CONTEXT_LENGTH
from app.shared.runtime.logger import logger, step_log
from app.infra.llm.model_providers import model_provider
from app.infra.config.providers import infra_config
from app.shared.runtime.load_prompt import load_prompt
import base64
from mimetypes import guess_type

from app.shared.utils.rate_limit_utils import apply_api_rate_limit
from app.infra.minio.minio_gateway import minio_gateway


'''
3. 调用视觉模型生成图片文字摘要
4. 将图片上传至 MinIO 对象存储
5. 用`![图片摘要](在线地址)`替换原有本地图片引用
6. 生成新 Markdown 并更新流程状态
'''

# ========== 1. 读取 Markdown 与图片目录 ==========
@step_log("load_markdown_and_image_dir")
def load_markdown_and_image_dir(state: ImportGraphState) -> list[tuple[str, Path, Path]]:
    # 1.1 获取请求参数 md_paths 和 非空校验
    md_paths: list[str] = state.get("md_paths")
    if not md_paths:
        logger.error(f"md_paths值为空,无法读取文档内容,业务无法继续,提前终止!!")
        raise ValueError(f"md_paths值为空,无法读取文档内容,业务无法继续,提前终止!!")

    # 1.2 批量md_path转成md_path_obj:Path 和 文件存在性校验 -> is_file()
    result: list[tuple[str, Path, Path]] = []
    for md_path in md_paths:
        md_path_obj: Path = Path(md_path)
        if not md_path_obj.is_file():
            logger.error(f"md_path不存在: {md_path},业务无法继续,提前终止!!")
            raise FileNotFoundError(f"md_path不存在: {md_path},业务无法继续,提前终止!!")

        # 1.3 基于md_path_obj读取文件内容、获取images_path_obj对象
        md_content = md_path_obj.read_text(encoding="utf-8")
        images_dir_obj: Path = md_path_obj.parent / "images"
        result.append((md_content, md_path_obj, images_dir_obj))

    # 1.4 返回结果列表
    return result


# ========== 2. 扫描图片与提取上下文 ==========
# 通用图片正则：匹配所有 Markdown 图片语法，用于连续图片场景下跳过图片引用
IMAGE_RE = re.compile(r"!\[.*?\]\(.*?\)")

# 获取上文，跳过连续图片引用，确保截取到足够的纯文本上下文。
# 向前取 context_length 个字符，如果窗口内包含其他图片引用，则继续向前扩展，直到去除图片后的纯文本长度 >= context_length。
def _get_pre_context(md_content: str, start: int, context_length: int) -> str:
    window_start = max(start - context_length, 0)        # 初始窗口：从 start 往前取 context_length 个字符
    window = md_content[window_start:start]              # 截取窗口内容
    text_only = IMAGE_RE.sub("", window)                 # 去掉窗口内的图片引用，只留纯文本
    shortage = context_length - len(text_only)           # 计算缺口：还差多少字符
    while shortage > 0 and window_start > 0:             # 如果缺口>0且还能往前，继续扩展
        window_start = max(window_start - shortage, 0)   # 窗口起点再往前挪 shortage 个字符
        window = md_content[window_start:start]
        text_only = IMAGE_RE.sub("", window)
        shortage = context_length - len(text_only)
    return window

#     获取下文，跳过连续图片引用，确保截取到足够的纯文本上下文。
def _get_post_context(md_content: str, end: int, context_length: int) -> str:
    window_end = min(end + context_length, len(md_content))
    window = md_content[end:window_end]
    text_only = IMAGE_RE.sub("", window)
    shortage = context_length - len(text_only)
    while shortage > 0 and window_end < len(md_content):
        window_end = min(window_end + shortage, len(md_content))
        window = md_content[end:window_end]
        text_only = IMAGE_RE.sub("", window)
        shortage = context_length - len(text_only)
    return window

# 扫描图片与提取上下文
@step_log("extract_image_context_info")
def extract_image_context_info(images_dir_obj: Path, md_content: str) -> \
                                                list[tuple[str, Path, tuple[str, str]]]:
    image_context_list: list[tuple[str, Path, tuple[str, str]]] = []

    # 2.1 遍历循环images_dir_obj每个文件
    for file_obj in images_dir_obj.iterdir():

        # 2.2 检查是不是图片(后缀名判断)
        if file_obj.suffix not in SUPPORTED_IMAGE_EXTENSIONS:
            logger.debug(f"本次处理的:{file_obj}不是一张图片,所以跳过!进行下一次处理!")
            continue

        # 2.3 定义图片对应的正则编译对象
        image_name = file_obj.name                                                     # file_obj.name 文件的完整文件名（含后缀）screenshot.png
        image_re = re.compile(f"\!\[.*?\]\(.*?" + re.escape(image_name) + r".*?\)")    # ![xxx](...screenshot.png...)

        # 2.4 调用正则编译对象image_re 去md_content找到匹配内容
        image_match: re.Match[str] | None = image_re.search(md_content)

        # 2.5 对Match对象进行非空检查
        if not image_match:
            logger.debug(f"本次处理的:{file_obj}是一张图片,但是没有被md_content引用,所以跳过!进行下一次处理!")
            continue

        # 2.6 根据Match获取图片的定位信息
        start = image_match.start()
        end = image_match.end()

        # 2.7 上文 = md_content[start-100:start]  [  : )] 下文 = md_content(end,end+100)
        # 图片处理：跳过上下文中的其他图片引用，扩展窗口截取真正的文本（包括连续图片）
        pre_context = _get_pre_context(md_content, start, SUB_MD_CONTENT_CONTEXT_LENGTH)
        post_context = _get_post_context(md_content, end, SUB_MD_CONTENT_CONTEXT_LENGTH)

        # 2.8 拼接个单个元素的原则 (图片名,图片的完整地址,(上,下))
        image_context_list.append(( image_name, file_obj, (pre_context, post_context) ))

    # 2.8 跳出循环,打印日志,返回结果 list
    logger.info(
        f"图片上下文识别结束,识别图片的长度:{len(image_context_list)},{'images文件夹都是非图片文件!' if len(image_context_list) == 0 else '参考示例:' + str(image_context_list[0])}")
    return image_context_list


# ========== 3. 调用视觉模型进行图片内容识别 ==========
# ([(图片名.name,图片的完整地址:str/Path,(上文,下文)),2,3,4] , 文件名 md_path_obj.stem) -> {图片名:语义 ....}
@step_log("call_vision_summary_images")
def call_vision_summary_images(images_context_list: list[tuple[str, Path, tuple[str, str]]], file_name: str) \
                                                                                        -> dict[str, str]:

    images_summaries: dict[str, str] = {}

    # 4.1 获取视觉模型对象
    lv_model = model_provider.vision_model(model_name=infra_config.lm_config.lv_model)

    # 4.2 循环每张图片对应的上下文信息 (图片名,完成地址,(上,下文))
    for image_name, image_path_obj, image_content in images_context_list:
        # 访问限制 不能超过模型每分钟数量 3000
        # https://help.aliyun.com/zh/model-studio/rate-limit?spm=a2c4g.11186623.help-menu-2400256.d_0_0_4.5740d355MgCFPC
        apply_api_rate_limit(max_requests=3000, window_seconds=60)

        # 4.3 加载和拼接对应的提示词 load_prompts("image_summary",root_folder=stem,image_content=(上,下文))
        summary_prompt_text: str = load_prompt("image_summary", root_folder=file_name, image_content=image_content)
        # 4.4 提示词封装成Message HumanMessage(content=提示词)
        image_base64_data: str = base64.b64encode(image_path_obj.read_bytes()).decode(encoding="utf-8")
        image_mimetype: str | None = guess_type(image_name)[0]
        message = HumanMessage(
            content=[
                {"type": "text", "text": summary_prompt_text},
                {"type": "image_url", "image_url": {"url": f"data:{image_mimetype};base64,{image_base64_data}"}}
            ]
        )

        # 4.5 封装一个调用 chains
        chains = lv_model | StrOutputParser()
        # 4.6 调用模型的链 chains.invoke([human_message]) -> 结果要的字符串     模型.invoke([]) -> response . content
        image_summary: str = chains.invoke([message])
        # 4.7 存储图片的函数  字典[图片名] = summary 结果要的字符串
        images_summaries[image_name] = image_summary
        logger.debug(f"本次识别的图片名:{image_name},识别的语义为:{image_summary}")

    # 4.8 打印日志 返回结果 return 字典
    logger.info(f"完成图片的语义识别,本次识别的数量为:{len(images_summaries)}")
    return images_summaries


# ========== 4. 调用minio将图片传递到文件服务器 ==========
# ([(图片名.name,图片的完整地址:str/Path,(上文,上文)),2,3,4]) -> {图片名:http...}
@step_log("upload_to_minio_return_url")
def upload_to_minio_return_url(images_context_list: list[tuple[str, Path, tuple[str, str]]], file_name: str) -> dict[
    str, str]:
    images_url: dict[str, str] = {}
    # 1 获取minio的客户端对象 infra.函数
    minio_client: Minio = minio_gateway.minio

    # ===================== 2. 清空该文档在MinIO中的旧图片 =====================
    # 先根据固定的前缀查询存不存在图片  list_objects(桶名,前缀="图片固定的前缀infra/文件夹名") []
    # https://www.minio.org.cn/docs/minio/linux/developers/python/API.html#list_objects
    select_object_list: list[Object] = list(minio_client.list_objects(
        bucket_name=minio_gateway.bucket_name,
        #  images_prefix = / 所以查不到!  prefix = 不能使用 /  后面+不+都行
        prefix=minio_gateway.images_prefix[1:] + "/" + file_name,
        recursive=True
    ))
    # 构造批量删除对象列表
    delete_object_list: list[DeleteObject] = [
        DeleteObject(obj.object_name) for obj in select_object_list if obj.object_name is not None
    ]
    # 执行批量删除
    if delete_object_list:
        logger.info(f"{file_name}对应的文件之前存储过图片!数量:{len(delete_object_list)},先清空!再上传!!")
        # 5.3 如果当前文件夹存在图片,先删除 remove_objects(桶名,DeleteOject)
        # https://www.minio.org.cn/docs/minio/linux/developers/python/API.html#remove_objects
        errors = minio_client.remove_objects(
            bucket_name=minio_gateway.bucket_name,
            delete_object_list=delete_object_list
        )
        for error in errors:
            logger.debug(f"图片处理异常:{error}")

    # ===================== 3. 上传所有新图片到 MinIO =====================
    # 循环处理上下文件列表,获取每张图片信息 (图片名,地址,_)
    for image_name, image_path_obj, _ in images_context_list:
        try:
            # 5.5 minio中上传文件 fput_object [考虑上传minio报错的问题,不能因为一张图片的报错,影响整个业务]  for try...
            object_name: str = minio_gateway.images_prefix + "/" + file_name + "/" + image_name
            minio_client.fput_object(
            bucket_name=minio_gateway.bucket_name,    # 桶名
            object_name=object_name,                  # 对象路径：/upload-images/文件名/图片名
            file_path=str(image_path_obj),            # 本地图片的绝对路径
            content_type=guess_type(image_name)[0] or "application/octet-stream"  # MIME类型
        )
            
            # https://www.minio.org.cn/docs/minio/linux/developers/python/API.html#fput_object
            # 5.6 拼接每张图片对应的在线地址 infra (object_name -> /固定的图片前缀/文件夹名/文件名) -> url
            image_url: str = minio_gateway.build_image_url(object_name=object_name)
            # 5.7 记录当前图片的在线地址 {[图片名],图片地址}
            images_url[image_name] = image_url
            logger.debug(f"{image_name}已经完成上传,对应地址为:{image_url}")
        except Exception as e:
            logger.warning(f"{image_name}上传失败,跳过,继续下一张图片处理!")
            continue
    # 5.8 返回字典
    return images_url


# ========== 5. 使用正则进行md_content内容的替换 ==========
def replace_old_md_content(md_content: str, images_summaries: dict[str, str], images_url: dict[str, str]) -> str:
    # md_content         "这是内容...![](./images/screenshot.png)"
    # images_summaries   AI生成的语义摘要
    # images_url         在线地址

    # 6.1 循环 图片名,网络地址
    for image_name, image_summary in images_summaries.items():
        # 6.2 根据 图片名获取语义描述 key 是图片名，value 是该图片的在线URL
        image_url: str | None = images_url.get(image_name)
        # 6.3 编译一个替换正则对象
        image_re = re.compile(r"\!\[.*?\]\(.*?" + re.escape(image_name) + r".*?\)")
        # 6.4 进行正则对象
        md_content = image_re.sub(lambda _: f"![{image_summary}]({image_url})", md_content)
    # 6.5 替换完毕
    return md_content

# ========== 6. 备份新的md_content ==========
@step_log("backup_new_md_content")
def backup_new_md_content(new_md_content: str, md_path_obj: Path) -> Path:
    # 7.1 获取新的md_path的目标地址
    new_md_path_obj: Path = md_path_obj.with_name(f"{md_path_obj.stem}_new.md")
    # 7.2 将内容写到新的地址
    new_md_path_obj.write_text(data=new_md_content, encoding="utf-8")
    # 7.3 返回新的地址 return
    return new_md_path_obj


@step_log("enrich_markdown_images")
def enrich_markdown_images(state: ImportGraphState) -> ImportGraphState:
    # 1. 获取参数并且校验(state)
    file_list: list[tuple[str, Path, Path]] = load_markdown_and_image_dir(state)
    all_new_md_contents: list[str] = []
    all_new_md_paths: list[str] = []

    for md_content, md_path_obj, images_dir_obj in file_list:
        # 2. 图片的非空内容校验,为空提前终止,进行下一个文件
        if (not images_dir_obj.is_dir()) or (not list(images_dir_obj.iterdir())):
            logger.info(f"{md_path_obj}:md文件,没有图片,无需图片处理,直接跳过!")
            all_new_md_contents.append(md_content)
            all_new_md_paths.append(str(md_path_obj))
            continue

        # 3. 查找images_path_obj每张图片对应的上下文信息
        images_context_list: list[tuple[str, Path, tuple[str, str]]] = extract_image_context_info(images_dir_obj,
                                                                                                  md_content)
        if not images_context_list:
            logger.info(f"{md_path_obj}:md文件,images文件夹不为空,但是没有图片,无需图片处理,直接跳过!")
            all_new_md_contents.append(md_content)
            all_new_md_paths.append(str(md_path_obj))
            continue

        # 4. 调用视觉模型进行图片内容识别
        images_summaries: dict[str, str] = call_vision_summary_images(images_context_list, md_path_obj.stem)

        # 5. 调用minio将图片传递到文件服务器
        images_url: dict[str, str] = upload_to_minio_return_url(images_context_list, md_path_obj.stem)

        # 6. 使用正则进行md_content内容的替换
        new_md_content: str = replace_old_md_content(md_content, images_summaries, images_url)

        # 7. 进行new_md_content备份
        new_md_path_obj: Path = backup_new_md_content(new_md_content, md_path_obj)

        all_new_md_contents.append(new_md_content)
        all_new_md_paths.append(str(new_md_path_obj))

    # 8. 更新state 并且返回即可
    state['md_content'] = "\n\n".join(all_new_md_contents)
    state['md_paths'] = all_new_md_paths
    return state