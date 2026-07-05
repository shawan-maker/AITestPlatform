# 1、同步生成器
import asyncio


def countdown(n):
    while n > 0:
        yield n
        n -= 1

for i in countdown(5):
    print(i)


# 2、异步生成器
async def countdown2(n):
    while n > 0:
        await asyncio.sleep(1)
        yield n
        n -= 1

async def main():
    async for i in countdown2(5):
        print(i)

asyncio.run(main())