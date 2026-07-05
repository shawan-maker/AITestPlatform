# 1、上下文管理器
with open('../.env', 'r',encoding='utf-8') as f:
    data = f.read()
print(data)

# 2、手动实现上下文管理器
class MyContext:
    def __init__(self,file_name):
        self.file_name = file_name

    def __enter__(self):
        self.f = open(self.file_name, 'r', encoding='utf-8')
        return self.f

    def read(self):
        data = self.f.read()
        return data

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.f.close()

with MyContext("../.env") as f:
    data = f.read()
print(data)

# 3、异步上下文管理器
import asyncio
class MyContext:
    def __init__(self,file_name):
        self.file_name = file_name

    async def __aenter__(self):
        self.f = open(self.file_name, 'r', encoding='utf-8')
        return self

    async def read(self):
        data = self.f.read()
        return data

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.f.close()

async def main():
    async with MyContext("../.env") as f:
        data = await f.read()
    print(data)

if __name__ == '__main__':
    asyncio.run(main())