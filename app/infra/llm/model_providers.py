from langchain_openai import ChatOpenAI

from app.infra.config.providers import infra_config
from app.shared.model.embedding_utils import generate_embeddings
from app.shared.model.llm_utils import get_llm_client
from app.shared.model.reranker_utils import get_reranker_model

# 【LLM 模型统一网关（提供器）】
class ModelProvider:
    """
    封装所有大模型调用入口，统一管理普通对话、视觉模型、向量模型等
    外部业务只需要调用 llm_provider 就能获取各种模型，不用关心底层配置
    """
    # 1. 获取大语言模型
    def llm_model(self, model_name:str|None=None, json_mode:bool=False):
        return get_llm_client(model=model_name, json_mode=json_mode)

    # 2. 获取视觉模型
    def vision_model(self, model_name:str):
        return get_llm_client(model=model_name) # 默认使用配置中的 lv_model（视觉大模型）

    # 3. 嵌入式模型生成向量的函数
    def create_embeddings(self,texts: list[str])-> dict[str, list]:
        # 将[改写问题]编码成稠密向量,同时生成稀疏向量；
        # 为 Milvus 混合检索准备统一输入。
        return generate_embeddings(texts)

    # 4. 调用reranker模型对问答对进行打分
    def compute_scores(self, question_answer_pair: list[tuple[str, str]]) -> list[float]:
        reranker_model = get_reranker_model()
        scores = reranker_model.compute_score(question_answer_pair, normalize=True)
        if scores is None:
            return []
        return scores.tolist()

    # 5. 计算文本token数量
    def compute_token_number(self, data: str) -> int:
        reranker_model = get_reranker_model()
        tokenizer = reranker_model.tokenizer
        # encode() 获取字符串转成token的id的列表!
        # add_special_tokens -> 计算token的时候,不要考虑特殊字符(分割字符)  514 - 2 -4 = 508
        token_id_list = tokenizer.encode(data, add_special_tokens=False)
        token_number: int = len(token_id_list)
        return token_number


# 创建全局唯一的 LLM 提供器实例，全项目通用，避免重复创建
model_provider = ModelProvider()