"""
工具模块，负责提供 embedding 相关的辅助能力。
"""
from pymilvus.model.hybrid import BGEM3EmbeddingFunction

from app.shared.config.embedding_config import embedding_config
from app.shared.runtime.logger import logger

_DEFAULT_EMBEDDING_DEVICE = "mps"
_bge_m3_ef: BGEM3EmbeddingFunction | None = None


# 模型单例对象，避免重复初始化
def get_bge_m3_ef() -> BGEM3EmbeddingFunction:
    """
    获取BGE-M3模型单例对象，自动加载环境变量配置
    :return: 初始化完成的BGEM3EmbeddingFunction实例
    """
    global _bge_m3_ef
    # 单例模式：已初始化则直接返回，避免重复加载模型
    if _bge_m3_ef is not None:
        logger.debug("BGE-M3模型单例已存在，直接返回实例")
        return _bge_m3_ef

    # 仅使用本地部署的模型路径，不允许自动下载
    model_name = embedding_config.bge_m3_path or embedding_config.bge_m3
    if not model_name:
        raise ValueError(
            "BGE-M3模型未配置本地路径！请在.env中设置 BGE_M3_PATH（本地模型路径）或 BGE_M3（模型名称）"
        )
    device = embedding_config.bge_device or _DEFAULT_EMBEDDING_DEVICE
    use_fp16 = embedding_config.bge_fp16

    # 打印模型初始化配置，便于问题排查
    logger.info(
        "开始初始化BGE-M3模型",
        extra={
            "model_name": model_name,
            "device": device,
            "use_fp16": use_fp16,
            "normalize_embeddings": True
        }
    )

    try:
        # 初始化 BGE-M3 模型，开启原生 L2 归一化（适配 Milvus IP 内积检索）
        _bge_m3_ef = BGEM3EmbeddingFunction(
            model_name=model_name,
            device=device,
            use_fp16=use_fp16,
            normalize_embeddings=True  # 模型原生对稠密+稀疏向量做L2归一化
        )
        logger.success("BGE-M3模型初始化成功，已开启原生L2归一化")
        return _bge_m3_ef
    except Exception as e:
        logger.error(f"BGE-M3模型初始化失败：{str(e)}", exc_info=True)
        raise  # 向上抛出异常，由调用方处理


def generate_embeddings(texts: list[str]) -> dict[str, list]:
    """
    为文本列表生成稠密+稀疏混合向量嵌入（模型原生L2归一化）
    :param texts: 要生成嵌入的文本列表，单文本也需封装为列表
    :return: 字典格式的向量结果，key为dense/sparse，对应嵌套列表/字典列表
    :raise: 向量生成过程中的异常，由调用方捕获处理
    """
    # 入参合法性校验
    if not isinstance(texts, list) or len(texts) == 0:
        logger.warning("生成向量入参不合法，texts必须为非空列表")
        raise ValueError("参数texts必须是包含文本的非空列表")
    if any(not isinstance(text, str) for text in texts):
        logger.warning("生成向量入参不合法，texts中存在非字符串内容")
        raise ValueError("参数texts必须是字符串列表")

    logger.info(f"开始为{len(texts)}条文本生成混合向量嵌入")
    try:
        # 加载BGE-M3模型单例
        model = get_bge_m3_ef()
        # 模型编码生成向量，返回dense（稠密向量）+sparse（CSR格式稀疏向量）
        # embeddings = 稠密 -> [[1024],[1024],[1024]]
        #              稀疏 250009 大部分都是0  [[25万],[25万],[25万]] -> BGEM3FlagModel -> [{index:x,index:x} -> 一个,{},{}]
        #              milvus -> 250009 -> c [compress]s [sparse]r [row] 压缩稀疏矩阵 -> 本次解析的所有的稀疏量  更高效的存储多组稀疏数据
        embeddings = model.encode_documents(texts)
        logger.debug(f"模型编码完成，开始解析稀疏向量格式，共{len(texts)}条")

        # 初始化稀疏向量处理结果，解析为字典格式（适配序列化/存储）
        processed_sparse = []
        # # 把模型输出的 CSR 稀疏矩阵 ，按“每条文本一行”拆成 {特征索引: 权重} 字典
        # # - indices ：非零元素的“列号（特征ID）”
        # # - data ：对应列号的权重值
        # # - indptr ：每一行在 indices/data 里的起止位置指针
        # # 数据示例:
        # # indices = [3, 8, 20, 1, 9]
        # # data    = [0.7, 0.2, 0.1, 0.6, 0.4]  -> milvus -> 稠密向量 [1024] 稀疏向量 : {index:值,index:值}
        # # indptr  = [0, 3, 5]
        # # 获取对应的数据
        # # - 第0条文本用 0:3 => indices=[3,8,20] , data=[0.7,0.2,0.1]
        # # - 第1条文本用 3:5 => indices=[1,9] , data=[0.6,0.4]
        for i in range(len(texts)):
            # 提取第i个文本的稀疏向量索引：np.int64 → Python int（满足字典key可哈希要求）
            sparse_indices = embeddings["sparse"].indices[
                #  1 0 : 2 3
                embeddings["sparse"].indptr[i]:embeddings["sparse"].indptr[i + 1]
            ].tolist()
            # 提取第i个文本的稀疏向量权重：np.float32 → Python float（适配JSON序列化/接口返回）
            sparse_data = embeddings["sparse"].data[
                embeddings["sparse"].indptr[i]:embeddings["sparse"].indptr[i + 1]
            ].tolist()
            # 构造{特征索引: 归一化权重}的稀疏向量字典
            sparse_dict = {k: v for k, v in zip(sparse_indices, sparse_data)}
            processed_sparse.append(sparse_dict)

        # 构造最终返回结果，稠密向量转列表（解决numpy数组不可序列化问题）
        result = {
            # [[1024],[1024] -> texts]
            "dense": [emb.tolist() for emb in embeddings["dense"]],  # 嵌套列表，与输入文本一一对应
            # [csr -> {},{} -> texts]
            "sparse": processed_sparse  # 字典列表，模型已做L2归一化  # [{},{},{}]
        }

        # {"dense":[[1024],[]]  ,  "sparse":[{},{}]}

        logger.success(f"{len(texts)}条文本向量生成完成，格式已适配工业级使用")
        return result

    except Exception as e:
        logger.error(f"文本向量生成失败：{str(e)}", exc_info=True)
        raise  # 不吞异常，向上传递让调用方做重试/降级处理


"""
核心设计亮点&适配说明：
1. normalize_embeddings=True 的价值：
- 检索更稳定 ：不同文本长短、词频差异不会把分数拉偏。
- IP 可近似 cosine ：向量都归一化后， Inner Product 和余弦相似度等价，Milvus 用 IP 检索就很合适。
- dense/sparse 都统一标尺 ：混合检索时两路分数更容易做融合，不容易一边压死另一边。
- 减少异常高分 ：防止“模长大”的向量仅靠长度拿高分。
2. 彻底解决NumPy类型做key问题：sparse_indices加.tolist()，将np.int64转为Python原生int，满足字典key的可哈希要求，无报错风险；
3. 稀疏值适配序列化：sparse_data加.tolist()，将np.float32转为Python原生float，支持JSON写入/接口返回/Milvus入库等所有场景；
4. 单例模式优化：模型仅初始化一次，避免重复加载耗时耗资源，提升批量处理效率；
5. 格式匹配业务调用：返回dense嵌套列表、sparse字典列表，与vector_result["dense"][0]/sparse_vector["sparse"][0]取值逻辑完美契合；
6. 分级日志覆盖：从模型初始化、向量生成到异常报错，全流程日志记录，便于生产环境问题排查；
7. 入参合法性校验：防止空列表/非列表入参导致的内部报错，提升工具类健壮性。
"""