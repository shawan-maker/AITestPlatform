# 1、定义异步函数
import asyncio


async def add(a: int, b: int) -> int:
    """加法运算"""
    print(f"正在执行加法运算：{a} + {b}")
    await asyncio.sleep(1)
    print(f"{a} + {b}加法运算结果是：{a + b}")
    return a + b

async def main():
    # res1 = asyncio.create_task(add(1, 2))
    # res2 = asyncio.create_task(add(3, 4))
    # await res1
    # await res2
    res = await asyncio.gather(add(1, 2), add(3, 4))
    print(f"最终结果是：{res}")


if __name__ == '__main__':
    asyncio.run(main())