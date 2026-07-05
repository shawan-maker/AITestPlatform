# 1、同步迭代器
import asyncio


class SyncCounter:
    def __init__(self, max):
        self.count = 0
        self.max = max

    def __iter__(self):
        return self

    def __next__(self):
        if self.count >= self.max:
            raise StopIteration
        self.count += 1
        return self.count

for num in SyncCounter(3):
    print(num)

# 2、异步迭代器
class AsyncCounter:
    def __init__(self, max):
        self.count = 0
        self.max = max

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.count >= self.max:
            raise StopAsyncIteration
        await asyncio.sleep(1)
        self.count += 1
        return self.count

async def main():
    async for i in AsyncCounter(3):
        print(i)

asyncio.run(main())