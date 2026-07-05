import hashlib
from typing import Any, Optional

from lightrag import LightRAG, QueryParam
from lightrag.kg.shared_storage import initialize_pipeline_status
from lightrag.llm.openai import openai_complete_if_cache, openai_embed
from lightrag.rerank import cohere_rerank
import dotenv
import os
from langchain_openai import ChatOpenAI
from lightrag.utils import EmbeddingFunc

# 1、加载env文件到环境变量
dotenv.load_dotenv("./.env")
# 1、定义llm对话的处理函数（一定是异步函数）
async def llm_model_func(prompt: str, system_prompt: str = "", history_messages: list[dict[str, Any]] | None = None, token_tracker: Any = None, **kwargs: Any):
    """处理rag生出内容的大模型函数"""
    if history_messages is None:
        history_messages = []
    return await openai_complete_if_cache(
        model=os.getenv("LLM_MODEL"),
        base_url=os.getenv("LLM_BINDING_HOST"),
        api_key=os.getenv("LLM_BINDING_API_KEY"),
        prompt=prompt,
        system_prompt=system_prompt,
        history_messages=history_messages,
        token_tracker=token_tracker,
        **kwargs
    )

# 2、定义嵌入模型的处理函数（一定是异步函数）
async def embedding_model_func(texts: list[str]):
    """处理向量数据库的嵌入模型函数"""
    return await openai_embed.func(
        texts,
        model=os.getenv("EMBEDDING_MODEL"),
        base_url=os.getenv("EMBEDDING_BINDING_HOST"),
        api_key=os.getenv("EMBEDDING_BINDING_API_KEY")
    )

# 3、定义重排序模型处理函数（一定是异步函数）
async def reorder_model_func(query: str, documents: list[str],top_n: Optional[int] = None, **kwargs: Any):
    """处理重排序模型函数"""
    return await cohere_rerank(
        query=query,
        documents=documents,
        top_n=top_n,  # 返回所有文档的评分
        model=os.getenv("RERANK_MODEL", "BAAI/bge-reranker-v2-m3"),  # 模型名称
        base_url=os.getenv("RERANK_BINDING_HOST"), # 模型服务地址
        api_key=os.getenv("RERANK_BINDING_API_KEY"), # 模型服务密钥
        **kwargs
    )

class RAGManager:
    """用于检索分享的RAG类型"""
    def __init__(self):
        # 初始化rag对象
        self.rag = None
        # 定义一个消息对话的列表，保存对话的历史记录
        self.message_list = []

    # 4、定义初始化rag的函数
    async def init_rag(self,project_name: str):
        """初始化rag的函数"""
        # 初始化rag对象
        self.rag = LightRAG(
            # 配置llm模型处理函数
            llm_model_func=llm_model_func,
            # 配置嵌入模型处理函数
            embedding_func=EmbeddingFunc(
                embedding_dim=4096,
                func=embedding_model_func
            ),
            # 配置重排序模型处理函数
            rerank_model_func=reorder_model_func,
            # 配置工作空间
            workspace=project_name,
            # # 配置图存储的方式（部署线上时，如果知识库中的文档数据太多，可以使用数据库来进行图存储）
            # graph_storage="Neo4JStorage",  # 覆盖默认的 NetworkX
            # # 配置向量存储的方式（部署线上时，如果知识库中的文档数据太多，可以使用数据库来进行向量存储）
            # vector_storage="FaissVectorDBStorage",
            # vector_db_storage_cls_kwargs={
            #     "cosine_better_than_threshold":0.3
            # }
        )
        # 初始化rag对象的存储
        await self.rag.initialize_storages()
        # 初始化pipeline状态
        await initialize_pipeline_status()
        # 返回rag对象
        return self.rag

    async def add_document(self,file_path: str):
        """往rag中添加文档"""
        if os.path.isfile(file_path):
            # 读取文件内容
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            # 往rag对象中插入文档
            print(f"插入文档：{file_path}")
            await self.rag.ainsert([content],ids=[file_path])
            print(f"插入文档完成：{file_path}")
        else:
            raise ValueError(f"{file_path} is not a file")

    async def delete_document(self,file_path: str):
        """删除rag对象中的文档"""
        if os.path.isfile(file_path):
            # 删除rag对象中的文档
            print(f"删除文档：{file_path}")
            # 通过hash计算文档的id
            # text_id = hashlib.md5(file_path.encode("utf-8")).hexdigest()
            # 调用lightrag的删除文档函数
            await self.rag.adelete_by_doc_id(file_path)
            print(f"删除文档完成：{file_path}")
        else:
            raise ValueError(f"{file_path} is not a file")

    async def query(self,question: str,prompt: str = "", mode: str = "hybrid"):
        """检索rag对象中的内容"""
        if not self.rag:
            raise ValueError("rag is not initialized")
        # 定义查询参数
        query_param = QueryParam(
            mode=mode,
            stream=True,  # 是否流式返回结果
            conversation_history=self.message_list,  # 会话的历史记录
            user_prompt=prompt
        )
        # 调用rag对象中的查询函数
        result = await self.rag.aquery(question,param=query_param)

        print(f"问题：{question},回答：")
        # 保存用户问题
        self.message_list.append({"role": "user", "content": question})
        """
        场景	返回值类型	说明
        缓存命中 ✅	str（字符串）	直接从 KV 存储读缓存结果，忽略 stream 参数
        缓存未命中 + stream=True	异步迭代器	调用 LLM 流式接口
        缓存未命中 + stream=False	str（字符串）	等待完整响应后返回
        """
        answer = ""
        if isinstance(result, str):
            print(result)
            answer = result
        else:
            async for chunk in result:
                print(chunk, end="", flush=True)
                answer += chunk
        # 保存ai回复的答案
        self.message_list.append({"role": "assistant", "content": answer})
        return answer


async def main():
    # 初始化自定义RAGManager类的对象
    rag_manager = RAGManager()
    # 初始化rag对象
    await rag_manager.init_rag("project01")
    # # 往rag对象中插入文档
    await rag_manager.add_document("01_demo_LightRAG.py")
    await rag_manager.add_document("./document/cursor生成项目代码方法.md")
    await rag_manager.add_document("./document/测试学科面试题整理_whv1.3.md")
    # # 检索rag对象中的内容
    # question = "请显示出嵌入式大模型的初始化模型函数"
    # result = await rag_manager.query(question)
    # 删除rag对象中的文档
    # await rag_manager.delete_document("01_demo_LightRAG.py")

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())

