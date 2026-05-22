"""
通过api接口去接入rag知识库系统
   - 优点：直接使用现有的RAG服务进行文档的学习和查询，不需要自己编写ragManager去学习和查询
   - 缺点：所有的学习文档都保存在同一个项目中，不适合多项目的情况


"""
import json

import requests

from config import settings

class RAGClient:
    """通过api接口去接入rag知识库"""
    def __init__(self):
        self.headers = {
            "Content-Type": "application/json",
            "X-API-Key": settings.RAG_API_KEY
        }
        self.url = settings.RAG_SERVER_URL

    def get_resquest_body(self,query:str,conversation_history=None,history_turns=10):
        """获取rag搜索接口的请求体"""
        return {
          "query": query,
          "mode": "hybrid",
          "only_need_context": False,
          "only_need_prompt": False,
          "response_type": "Multiple Paragraphs",
          "top_k": 15,
          "chunk_top_k": 8,
          "max_entity_tokens": 2000,
          "max_relation_tokens": 2000,
          "max_total_tokens": 8000,
          "conversation_history": [] if conversation_history is None else conversation_history,
          "history_turns": history_turns,
          "ids": [],
          "user_prompt": "",
          "enable_rerank": True
        }

    def query(self,query:str,conversation_history=None,history_turns=10):
        """rag搜索接口"""
        query_url = self.url + "/query"
        param = self.get_resquest_body(query,conversation_history,history_turns)
        res = requests.post(query_url,json=param,headers=self.headers)
        return res.json()

    def query_stream(self,query:str,conversation_history=None,history_turns=10):
        """rag搜索流式输出"""
        query_url = self.url + "/query/stream"
        param = self.get_resquest_body(query,conversation_history,history_turns)
        res = requests.post(query_url,json=param,headers=self.headers,stream=True)
        for item in res.iter_lines():
            content = json.loads(item.decode()).get("response")
            if content:
                yield content

if __name__ == '__main__':
    rag_client = RAGClient()
    # print(rag_client.query("登录模块的接口描述"))
    result4 = rag_client.query_stream("登录模块的接口描述")
    for i in result4:
        print(i,end="",flush=True)