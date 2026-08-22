"""
应用主包 / 工具模块中的 normalize_sparse_vector 模块，负责承载对应场景的具体实现逻辑。
"""
import numpy as np
def normalize_sparse_vector(sparse_vec):
    """
    对稀疏向量做 L2 归一化（仅处理非零维度，不影响零维度）
    :param sparse_vec: 原始稀疏向量（dict 格式：{维度: 数值}）
    :return: 归一化后的稀疏向量
    """
    if not sparse_vec:  # 空向量直接返回
        return sparse_vec

    # 提取非零维度的数值
    values = np.array(list(sparse_vec.values()), dtype=np.float64)
    # 计算 L2 范数（避免除以 0）
    l2_norm = np.linalg.norm(values)
    if l2_norm < 1e-9:  # 范数接近 0 时，直接返回原向量（避免除零错误）
        return sparse_vec

    # 归一化：每个数值除以 L2 范数
    normalized_values = values / l2_norm
    # normalized_values = (values / l2_norm).astype(np.float32)  # 统一转为 float32
    # 重建稀疏向量 dict
    return dict(zip(sparse_vec.keys(), normalized_values))
