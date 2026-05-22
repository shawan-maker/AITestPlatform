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
from raganything import RAGAnything
from config.settings import RAG_MANAGE_STORAGE, OUTPUT_DIR, DOCUMENT_DIR


# 1、加载env文件到环境变量
# 获取当前脚本所在的目录，然后加载同目录下的.env
# _base_dir = os.path.dirname(os.path.abspath(__file__))
# dotenv.load_dotenv(os.path.join(_base_dir, ".env"))
# dotenv.load_dotenv("./.env")

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

# 4、定义视觉模型处理函数（一定是异步函数）
# 作用：(1) 往知识库上传文档时，理解文档中的图片和表格等复杂数据。（2）在进行rag检索的时候，分析图片中的内容
async def visual_model_func(prompt: str, system_prompt: str = "", history_messages: list[dict[str, Any]] | None = None, image_data=None,  **kwargs: Any):
    """处理视觉模型函数"""
    # 定义系统提示
    system_prompt = system_prompt or "你是一个资深的知识库检索助手，请根据用户的问题进行分析，并去知识库检索结果，并以中文回复"
    # 构造图片上传处理的消息
    messages = [
        {"role": "system", "content": system_prompt},
    ]
    if image_data:
        # 构造图片上传处理的消息
        messages.append({"role": "user", "content": [
            {"type": "text","text":prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
        ]})
        return await openai_complete_if_cache(
            model=os.getenv("VISUAL_MODEL"),
            base_url=os.getenv("VISUAL_BINDING_HOST"),
            api_key=os.getenv("VISUAL_BINDING_API_KEY"),
            prompt="",
            system_prompt="",
            history_messages=[],
            messages=messages,
            **kwargs
        )
    else:
        return await openai_complete_if_cache(
            model=os.getenv("VISUAL_MODEL"),
            base_url=os.getenv("VISUAL_BINDING_HOST"),
            api_key=os.getenv("VISUAL_BINDING_API_KEY"),
            prompt=prompt,
            system_prompt=system_prompt,
            history_messages=history_messages,
            **kwargs
        )


class RAGManager:
    """用于检索分享的RAG类型"""
    def __init__(self):
        # 初始化rag对象
        self.rag = None
        self.lightrag=None
        # 定义一个消息对话的列表，保存对话的历史记录
        self.message_list = []

    # 定义初始化rag的函数
    async def init_rag(self,project_name: str):
        """初始化rag的函数"""
        # 1、初始化Lightrag对象
        self.lightrag = LightRAG(
            # 配置llm模型处理函数
            llm_model_func=llm_model_func,
            # 配置嵌入模型处理函数
            embedding_func=EmbeddingFunc(
                embedding_dim=int(os.getenv("EMBEDDING_DIM", 4096)),
                func=embedding_model_func
            ),
            # 配置重排序模型处理函数
            rerank_model_func=reorder_model_func,
            # 配置工作空间
            workspace=os.path.join(RAG_MANAGE_STORAGE, project_name),
            # 👇 新增优化参数
            chunk_token_size=4096,  # 增大chunk，减少总数
            chunk_overlap_token_size=128,  # chunk重叠区
            # # 配置图存储的方式（部署线上时，如果知识库中的文档数据太多，可以使用数据库来进行图存储）
            # graph_storage="Neo4JStorage",  # 覆盖默认的 NetworkX
            # # 配置向量存储的方式（部署线上时，如果知识库中的文档数据太多，可以使用数据库来进行向量存储）
            # vector_storage="FaissVectorDBStorage",
            # vector_db_storage_cls_kwargs={
            #     "cosine_better_than_threshold":0.3
            # }
        )
        # 初始化rag对象的存储
        await self.lightrag.initialize_storages()
        # 初始化pipeline状态
        await initialize_pipeline_status()
        # 2、初始化RAGAnything对象 - 配置多模态的处理能力
        self.rag = RAGAnything(
            lightrag=self.lightrag,
            # 配置视觉模型处理函数
            vision_model_func=visual_model_func,
        )
        # 返回rag对象
        return self.rag

    # 纯文本插入(仅LightRAG支持)
    async def add_document(self,file_path: str):
        """往rag中添加文档（字符串格式）"""
        if os.path.isfile(file_path):
            # 读取文件内容
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            # 往rag对象中插入文档
            print(f"插入文档：{file_path}")
            await self.lightrag.ainsert([content],ids=[file_path])
            print(f"插入文档完成：{file_path}")
        else:
            raise ValueError(f"{file_path} is not a file")

    # 纯文本删除(仅LightRAG支持)
    async def delete_document(self,file_path: str):
        """删除rag对象中的文档"""
        if os.path.isfile(file_path):
            # 删除rag对象中的文档
            print(f"删除文档：{file_path}")
            # 通过hash计算文档的id
            # text_id = hashlib.md5(file_path.encode("utf-8")).hexdigest()
            # 调用lightrag的删除文档函数
            await self.lightrag.adelete_by_doc_id(file_path)
            print(f"删除文档完成：{file_path}")
        else:
            raise ValueError(f"{file_path} is not a file")

    # 纯文本查询(LightRAG和RAGAnything都支持)
    async def query(self,question: str,prompt: str = "", mode: str = "hybrid"):
        """检索rag对象中的内容"""
        if not self.rag:
            raise ValueError("rag is not initialized")
        # # 定义查询参数（使用RAGanything增强后的rag，不支持param=QueryParam参数，去掉后query函数可以通用）
        # query_param = QueryParam(
        #     mode=mode,
        #     stream=True,  # 是否流式返回结果
        #     conversation_history=self.message_list,  # 会话的历史记录
        #     user_prompt=prompt
        # )
        # 调用rag对象中的查询函数
        result = await self.rag.aquery(
            question,
            mode=mode,
            # user_prompt=prompt,
            stream=True,  # 是否流式返回结果
            conversation_history=self.message_list,  # 会话的历史记录
            )
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

    # 多模态插入(PDF/图片) （仅RAGanything支持）
    async def load_document(self,file_path: str):
        """加载文档(任意格式)"""
        print(f"插入多模态文档：{file_path}")
        await self.rag.process_document_complete(
            file_path=file_path,
            output_dir=OUTPUT_DIR,
        )
        print(f"插入多模态文档完成：{file_path}")

    # 多模态查询(带图片) （仅RAGanything支持）
    async def query_multimodal(self,question: str,img_path: str="",prompt: str = "", mode: str = "hybrid"):
        """多模态检索"""
        result= await self.rag.aquery_with_multimodal(
            question,
            mode=mode,
            stream=True,  # 是否流式返回结果
            multimodal_content=[
                {
                    "type": "image",
                    "img_path": img_path
                }
            ],
            user_prompt=prompt)
        print(f"问题：{question},回答：")
        answer = ""
        if isinstance(result, str):
            print(result)
            answer = result
        else:
            async for chunk in result:
                print(chunk, end="", flush=True)
                answer += chunk
        return answer


async def main():
    # 初始化自定义RAGManager类的对象
    rag_manager = RAGManager()
    # 初始化rag对象
    await rag_manager.init_rag("tpshop")
    # 2、往rag对象中插入文档
    # （2.1）往rag对象中插入文档（字符串格式）   ———— 增强RAG后ainsert()方法不能再使用了
    await rag_manager.add_document(os.path.join(DOCUMENT_DIR,"tester.md"))
    # await rag_manager.add_document("./document/金融P2P项目需求说明.md")
    # await rag_manager.add_document("./document/01_TPshop需求说明书V5.2.md")
    # （2.2）往rag对象中插入多模态文档（图片、表格、excel等）
    await rag_manager.load_document(os.path.join(DOCUMENT_DIR,"picture-desc.pdf"))
    # # 3、查询rag对象中的内容
    # （3.1）普通文本内容检索
    # await rag_manager.query("怎么做性能压测？")
    # （3.2）多模态（学习文档）内容检索
    # await rag_manager.query("环境搭建过程介绍")
    # （3.3）多模态（检索内容：如使用图片检索）内容检索
    # await rag_manager.query_multimodal("请根据图片中的内容描述，给出一个完整的环搭建过程。","./document/setup_env.jpg")

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())


"""
项目文档的知识库作用：
   1、 生成功能用例时：      某个需求去生成用例（完整的需求文档，业务流程图，数据库字典）
   2、 生成接口自动化用例时： 给某个业务流，生成对应的接口自动化用例（业务流的接口链路）
   3、 做一个项目的知识问答助手： 给出一个问题，回答这个问题（项目的知识库）
"""