from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
import dotenv,os
dotenv.load_dotenv("../.env")

# 1、ChatOpenAI大模型对象 | 2、ChatPromptTemplate提示词模版 | 3、StrOutputParser输出解析器 都是LangChain中的Runnable对象(可执行组件)
model = ChatOpenAI(model_name=os.getenv("SI_MODEL_NAME"),
                 openai_api_key=os.getenv("SI_API_KEY"),
                 openai_api_base=os.getenv("SI_BASE_URL"))

prompt = ChatPromptTemplate.from_template("翻译这句话为英文：{input}")
parser = StrOutputParser()
# 2、 创建一个Chain对象，将prompt、model和parser组合起来，实现链式调用
chain = prompt | model | parser
# 3、 调用Chain对象的invoke方法（prompt、model和parser都可以调用invoke方法）
output = chain.invoke({"input": "今天天气很好"})
print(output)