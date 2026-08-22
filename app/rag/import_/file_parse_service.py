import shutil
import time
from pathlib import Path
import requests

from app.infra.config.providers import infra_config
from app.infra.document_parse.mineru_gateway import mineru_gateway
from app.process.import_.agent.state import ImportGraphState
from app.rag.import_.config import PARSE_PDF_OUTPUT_DIR, MINERU_MODEL_VERSION, MINERU_DOWNLOAD_TIMEOUT_SECONDS, \
    MINERU_POLL_INTERVAL_SECONDS, MINERU_POLL_TIMEOUT_SECONDS
from app.shared.runtime.logger import logger, PROJECT_ROOT, step_log


FILE_TYPE_PATH_MAP = {
    "is_pdf_read_enabled": "pdf_path",
    "is_word_read_enabled": "word_path",
    "is_ppt_read_enabled": "ppt_path",
    "is_txt_read_enabled": "txt_path",
}


# 校验文件路径与输出目录，确保文件存在、目录可用并自动补全目录
# path_key: 指定从state中读取文件路径的key（如"pdf_path"、"word_path"等）
@step_log("validate_data_and_paths")
def validate_data_and_paths(state:ImportGraphState, path_key: str) -> tuple[Path,Path]:
    # 步骤1: 获取参数
    file_path:str | None = state.get(path_key)
    local_dir:str | None = state.get("local_dir")
    # 步骤2: 非空校验
    if not file_path:
        logger.error(f"file_path为空,没有文件可以解析,业务无法继续,提前终止!")
        raise ValueError(f"file_path为空,没有文件可以解析,业务无法继续,提前终止!")
    if not local_dir:
        local_dir = str(PROJECT_ROOT / PARSE_PDF_OUTPUT_DIR)
        logger.warning(f"local_dir为空,为了业务继续进行,给与默认值:{local_dir}")
    # 步骤3: 将字符串转成Path
    file_path_obj:Path = Path(file_path)
    # Path( | str | __file__ | Path)
    local_dir_obj:Path = Path(local_dir)
    # 步骤4: 存在性校验
    if not file_path_obj.is_file():
        logger.error(f"{str(file_path_obj)}有地址,但是没有具体的文件,业务无法继续,提前终止!!")
        raise FileNotFoundError(f"{str(file_path_obj)}有地址,但是没有具体的文件,业务无法继续,提前终止!!")
    if not local_dir_obj.is_dir():
        logger.warning(f"{str(local_dir_obj)}地址没有对应的文件夹,我们提前创建!!")
        local_dir_obj.mkdir(parents=True, exist_ok=True)
    # 步骤5: 返回结果
    return file_path_obj, local_dir_obj


# 上传文件到MinerU服务，并轮询等待解析完成，最终返回解析结果的下载地址
@step_log("upload_file_and_poll")
def upload_file_and_poll(file_paths: Path | list[Path]) -> str | list[str]:
    # 1. 统一成列表，方便后续统一处理
    if isinstance(file_paths, Path):
        file_path_list = [file_paths]
    else:
        file_path_list = file_paths
    if not file_path_list:
        logger.error("file_paths为空,没有文件可以解析,业务无法继续,提前终止!")
        raise ValueError("file_paths为空,没有文件可以解析,业务无法继续,提前终止!")

    # 2. 校验MinerU服务配置（base_url和api_key必须存在）
    if not mineru_gateway.api_key or not mineru_gateway.base_url:
        logger.error("minerU配置错误,请检查minerU配置!")
        raise ValueError("minerU配置错误,请检查minerU配置!")

    # 3. 向minerU申请文件上传地址（批量接口原生支持传多个文件名）
    # https://mineru.net/doc/docs/index.html?theme=light&v=1.0
    token = mineru_gateway.api_key
    url = f"{mineru_gateway.base_url}/file-urls/batch"
    # 构造请求头
    header = {
        "content-Type" : "application/json",
        "Authorization" : f"Bearer {token}"
    }
    # 构造请求参数：文件名 + 使用的模型版本
    data = {
        "files" : [{"name" : p.name} for p in file_path_list],
        "model_version" : MINERU_MODEL_VERSION
    }
    # 发送POST请求
    response = requests.post(url=url, headers=header, json=data, timeout=MINERU_DOWNLOAD_TIMEOUT_SECONDS)
    # 判断状态成功: 1. 标准的接口 先判断响应状态码 status_code 再判断接口的业务状态 code 2. 非标准接口http地址 直接判断状态码
    status_code = response.status_code
    if status_code != 200:
        logger.error(f"向minerU申请文件解析地址,网络状态错误:{status_code},业务无法继续,提前终止!!")
        raise RuntimeError(f"向minerU申请文件解析地址,网络状态错误:{status_code},业务无法继续,提前终止!!")
    # 响应体的json字符串  .content .text .json() -> json - dict
    response_json_dict = response.json()
    code = response_json_dict.get("code", -1)
    if code != 0:
        logger.error(f"向minerU申请文件解析地址,业务状态错误:{code},业务无法继续,提前终止!!")
        raise RuntimeError(f"向minerU申请文件解析地址,业务状态错误:{code},业务无法继续,提前终止!!")
    # 获取上传地址/batch_id
    batch_id:str = response_json_dict.get("data", {}).get("batch_id")
    file_urls:list[str] = response_json_dict.get("data", {}).get("file_urls")
    # 非空校验
    if not batch_id:
        logger.error(f"向minerU申请文件解析地址,结果中batch_id为空,业务无法继续,提前终止!!")
        raise RuntimeError(f"向minerU申请文件解析地址,结果中batch_id为空,业务无法继续,提前终止!!")
    if not file_urls:
        logger.error(f"向minerU申请文件解析地址,结果中file_urls为空,业务无法继续,提前终止!!")
        raise RuntimeError(f"向minerU申请文件解析地址,结果中file_urls为空,业务无法继续,提前终止!!")
    file_url:str = file_urls[0] #单文件上传，所以我们只取第一个
    logger.info(f"成功向minerU申请到文件解析地址,batch_id:{batch_id},file_url:{file_url}")

    # 4. 逐个上传文件到对应的预签名URL
    # requests.Session()创建一个持久化会话，with 确保用完后自动关闭。
    with requests.Session() as session:
         # 直接使用put函数指定的参数，忽略系统环境变量中的代理配置
        session.trust_env = False
        for file_path_obj, file_url in zip(file_path_list, file_urls):
            data = file_path_obj.read_bytes()   # Path.read_bytes() 一次性把文件全部读入内存，返回 bytes 类型。put 上传需要的是二进制数据。
            upload_response = session.put(url=file_url, data=data)   # PUT 上传二进制数据
            upload_status_code = upload_response.status_code
            if upload_status_code != 200:
                logger.error(f"向指定地址:{file_url}上传文件失败!状态码为:{upload_status_code},业务无法继续,提前终止!")
                raise RuntimeError(f"向指定地址:{file_url}上传文件失败!状态码为:{upload_status_code},业务无法继续,提前终止!")
            logger.info(f"文件{file_path_obj.name}上传成功!")
    logger.info(f"共{len(file_path_list)}个文件上传完成!")

    # 5. 使用batch_id轮询获取解析结果,提取zip_url
    url = f"{infra_config.mineru_config.base_url}/extract-results/batch/{batch_id}"
    interval_time = MINERU_POLL_INTERVAL_SECONDS    # 3秒   -> 自己试
    timeout_time = MINERU_POLL_TIMEOUT_SECONDS  # 600秒 -> 每页pdf预估1秒
    current_time = time.time()

    # 轮询
    while True:
        # 5.1 # 超时判断
        if time.time() - current_time >timeout_time:
            logger.error(f"轮询获取解析结果超时,提前终止业务!")
            raise TimeoutError(f"轮询获取解析结果超时,提前终止业务!")
        # 5.2 没有申请状态请求,请求轮询接口
        try:
            # 发 GET 请求查询解析状态
            poll_response = requests.get(url,headers=header, timeout=MINERU_DOWNLOAD_TIMEOUT_SECONDS)
        except requests.RequestException as e:
            logger.warning(f"请求出现异常:{e},稍后重试!")
            time.sleep(interval_time)
            continue
        # 5.3 判断网络状态码，三种结果：5xx可重试，其他直接报错
        if poll_response.status_code != 200:
            if 500 <= poll_response.status_code < 600:
                # 可以给机会
                logger.warning(f"轮询获取解析结果,状态码为:{poll_response.status_code},给与机会,再次尝试!")
                time.sleep(interval_time)  # 线程 【本项目都是线程级别】
                # asyncio.sleep() 协程
                continue
            else:
                logger.error(f"轮询获取解析结果,状态码为:{poll_response.status_code},业务无法继续,提前终止!!")
                raise RuntimeError(f"轮询获取解析结果,状态码为:{poll_response.status_code},业务无法继续,提前终止!!")
        # 5.4 判断业务状态码
        poll_response_dict:dict = poll_response.json()
        poll_code = poll_response_dict.get("code", -1)
        # 不等于0抛出异常
        if poll_code != 0:
            logger.error(f"向minerU获取文件解析结果,业务状态错误:{poll_code},业务无法继续,提前终止!!")
            raise RuntimeError(f"向minerU获取文件解析结果,业务状态错误:{poll_code},业务无法继续,提前终止!!")

        # 5.5 解析获取结果
        extract_result: list[dict] = poll_response_dict.get("data", {}).get("extract_result", [])
        if not extract_result:
            logger.error("轮询获取解析结果,extract_result为空,业务无法继续,提前终止!")
            raise RuntimeError("轮询获取解析结果,extract_result为空,业务无法继续,提前终止!")
        
        # 遍历所有文件的解析状态
        all_done = True
        zip_urls:list[str] = []
        for i, result_dict in enumerate(extract_result):
            poll_state = result_dict.get("state")
            if poll_state == "failed":
                logger.error(f"第{i+1}个文件解析失败,业务无法继续,提前终止!!")
                raise RuntimeError(f"第{i+1}个文件解析失败,业务无法继续,提前终止!!")
            elif poll_state != "done":
                all_done = False
                logger.info(f"第{i+1}个文件解析状态:{poll_state},正在解析中...")
            else:
                full_zip_url: str | None = result_dict.get("full_zip_url")
                if not full_zip_url:
                    logger.error(f"第{i+1}个文件解析状态为done但full_zip_url为空,业务无法继续,提前终止!")
                    raise RuntimeError(f"第{i+1}个文件解析状态为done但full_zip_url为空,业务无法继续,提前终止!")
                zip_urls.append(full_zip_url)
                logger.info(f"第{i+1}个文件解析状态:成功,下载地址:{full_zip_url},结束方法!")

        if all_done:
            logger.info(f"全部{len(zip_urls)}个文件解析完成!")
            # 单文件返回str，批量返回list[str]
            return zip_urls[0] if isinstance(file_paths, Path) else zip_urls
        else:
            logger.info(f"部分文件仍在解析中,稍后再试!")
            time.sleep(interval_time)
            continue


# 下载 MinerU 解析完成的 ZIP 压缩包，解压并提取出标准的 MD 文件
def download_zip_and_extract_md(zip_urls: str | list[str], local_dir_obj:Path,  file_names: str | list[str]) -> Path | list[Path]:
    # ---------------------- 1. # 统一成列表 ----------------------
    if isinstance(zip_urls, str):
        # 单个：zip_urls是str时，file_names也一定是str
        zip_url_list: list[str] = [zip_urls]
        file_name_list: list[str] = [file_names]  # type: ignore[list-item]
    else:
        # 列表
        zip_url_list: list[str] = zip_urls  # type: ignore[arg-type]
        file_name_list: list[str] = file_names if isinstance(file_names, list) else [file_names]  # type: ignore[arg-type]

    md_path_list: list[Path] = []
    # ---------------------- 2. 从 zip_url 下载解析结果压缩包 ----------------------
    # 1. 下载文件到output中,名称为 文件名.zip
    for zip_url, file_name in zip(zip_url_list, file_name_list):
        response = requests.get(url=zip_url, timeout=MINERU_DOWNLOAD_TIMEOUT_SECONDS)
        status_code = response.status_code
        if status_code != 200:
            logger.error(f"向minerU返回的下载文件地址:{zip_url}请求,出现响应状态错误:{status_code},业务无法继续,提前终止!")
            raise RuntimeError(f"向minerU返回的下载文件地址:{zip_url}请求,出现响应状态错误:{status_code},业务无法继续,提前终止!")

        zip_file_obj: Path = local_dir_obj / f"{file_name}.zip"
        zip_file_obj.write_bytes(data=response.content)

    # ---------------------- 3. 解压 ZIP 文件到指定目录 ----------------------
        zip_file_dir_obj: Path = local_dir_obj / file_name
        # 检查是否存在解压的文件夹 (/output/文件名)
        if zip_file_dir_obj.is_dir():
            # 递归清空文件夹内容 + 文件夹本身
            # 确保每次解析都是"干净环境"，避免新旧文件混在一起，导致后续读取到过期数据。
            shutil.rmtree(zip_file_dir_obj)
        zip_file_dir_obj.mkdir(parents=True, exist_ok=True)
        # filename 要解压的压缩包路径，extract_dir 解压到哪个目录
        shutil.unpack_archive(filename=zip_file_obj, extract_dir=zip_file_dir_obj)

    # ---------------------- 4. 自动查找最合适的 MD 文件 ------------------------
        # 递归扫描解压文件夹，找出里面所有的 .md 文件，存到列表里。
        md_file_list: list[Path] = list(zip_file_dir_obj.rglob("*.md"))
        if not md_file_list:
            logger.error(f"向minerU返回的下载文件地址:{zip_url}请求,文件下载成功,内部没有md文件!业务无法继续,提前终止!!")
            raise FileNotFoundError(f"向minerU返回的下载文件地址:{zip_url}请求,文件下载成功,内部没有md文件!业务无法继续,提前终止!!")

        # 优先级1：同名
        found = False
        for md_file in md_file_list:
            if md_file.stem == file_name:
                md_path_list.append(md_file)
                found = True
                logger.info(f"向minerU返回的下载文件地址:{zip_url}请求,文件下载成功,文件地址为:{md_file},跳出循环即可!")
                break

        # 优先级2：找不到同名，找 full.md（MinerU 默认完整导出文件）
        if not found:
            for full_md_file in md_file_list:
                if full_md_file.stem == 'full':
                    # 重命名并返回即可
                    renamed = full_md_file.rename(full_md_file.with_name(f"{file_name}.md"))
                    md_path_list.append(renamed)
                    found = True
                    logger.info(f"向minerU返回的下载文件地址:{zip_url}请求,文件下载成功,文件地址为:{renamed},跳出循环即可!")
                    break

        # 最后：有md文件 命名既不是full 又不是 文件名.md
        if not found:
            logger.error(f"向minerU返回的下载文件地址:{zip_url}请求,文件下载成功,解压后文件名不叫full或者文件名,请根据官网明确后,再解析!")
            raise FileNotFoundError(f"向minerU返回的下载文件地址:{zip_url}请求,文件下载成功,解压后文件名不叫full或者文件名,请根据官网明确后,再解析!")

    # 单文件返回Path，批量返回list[Path]
    return md_path_list[0] if isinstance(zip_urls, str) else md_path_list


# 【文件转Markdown统一服务】支持单文件和多文件批量上传
@step_log("parse_file_to_markdown")
def parse_file_to_markdown(state: ImportGraphState) -> ImportGraphState:
    # 1. 收集所有启用的文件路径
    file_path_objs: list[Path] = []
    for flag_key, path_key in FILE_TYPE_PATH_MAP.items():
        if state.get(flag_key, False):
            if not state.get(path_key):
                logger.error(f"{flag_key}为True但{path_key}为空,业务无法继续,提前终止!")
                raise ValueError(f"{flag_key}为True但{path_key}为空,业务无法继续,提前终止!")
            file_path_obj, _ = validate_data_and_paths(state, path_key)
            file_path_objs.append(file_path_obj)

    if not file_path_objs:
        logger.error("未找到任何启用的文件类型标记,业务无法继续,提前终止!")
        raise ValueError("未找到任何启用的文件类型标记,业务无法继续,提前终止!")

    # 2. 校验输出目录
    local_dir: str | None = state.get("local_dir")
    if not local_dir:
        local_dir = str(PROJECT_ROOT / PARSE_PDF_OUTPUT_DIR)
        logger.warning(f"local_dir为空,为了业务继续进行,给与默认值:{local_dir}")
    local_dir_obj = Path(local_dir)
    if not local_dir_obj.is_dir():
        logger.warning(f"{str(local_dir_obj)}地址没有对应的文件夹,我们提前创建!!")
        local_dir_obj.mkdir(parents=True, exist_ok=True)

    # 3. minerU申请解析和文件上传以及轮询获取解析结果（单文件传Path，多文件传list[Path]）
    upload_input = file_path_objs[0] if len(file_path_objs) == 1 else file_path_objs
    full_zip_urls: str | list[str] = upload_file_and_poll(upload_input)

    # 4. 下载并解压md文件以及重命名工作（单文件传str，多文件传list[str]）
    file_names = [p.stem for p in file_path_objs]
    download_names = file_names[0] if len(file_names) == 1 else file_names
    md_path_obj = download_zip_and_extract_md(full_zip_urls, local_dir_obj, download_names)
    if isinstance(md_path_obj, Path):
        state['md_paths'] = [str(md_path_obj)]
    else:
        state['md_paths'] = [str(p) for p in md_path_obj]

    return state