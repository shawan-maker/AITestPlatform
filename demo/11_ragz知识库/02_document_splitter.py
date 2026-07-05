# 对数据进行切分
from langchain_text_splitters import RecursiveCharacterTextSplitter

with open("./01_basic_embedded_model.py", "r", encoding="utf-8") as f:
    data = f.read()

splitter = RecursiveCharacterTextSplitter(
    chunk_size=200,      # 每一块最大 200 个字符
    chunk_overlap=20,    # 块与块之间重叠 20 个字符（保证语义连贯）
    length_function=len, # 用长度 len 来计算大小
    is_separator_regex=False
)

texts = splitter.create_documents([data])
for item in texts:
    print("==============================================")
    print(item.page_content)