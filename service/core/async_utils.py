"""
async_utils.py —— 后台线程安全调度协程到主事件循环的工具模块
============================================================
解决的核心问题：
  Tortoise ORM 的 MySQL 连接池在服务器启动时绑定到主事件循环（FastAPI/uvicorn loop）。
  后台线程（threading.Thread / ThreadPoolExecutor）中如果调用 asyncio.run()，
  会创建并销毁一个新的事件循环，导致：
    1. Tortoise ORM 全局连接池状态被破坏（Tortoise.init/close_connections 被新循环干扰）
    2. httpx 异步客户端的连接绑定到错误的循环
    3. 所有后续 HTTP 请求永久 500（AttributeError / MultipleObjectsReturned 等）

  本模块提供 register_main_loop() 和 run_on_main_loop() 两个函数，
  让后台线程能安全地将协程调度回主事件循环执行，复用已有的连接池，不创建新循环。

使用方式：
  1. 服务启动时由 agent_stream 调用 register_main_loop(loop) 注册主循环
  2. 后台线程中需要执行协程时调用 run_on_main_loop(coro)
  3. 独立脚本（无主循环）降级为 asyncio.run()
"""
import asyncio
import threading


_main_loop_ref: asyncio.AbstractEventLoop | None = None
_main_loop_lock = threading.Lock()


def register_main_loop(loop: asyncio.AbstractEventLoop) -> None:
    """注册主事件循环引用（由 agent_stream 在服务启动时调用）"""
    global _main_loop_ref
    with _main_loop_lock:
        _main_loop_ref = loop


def get_main_loop() -> asyncio.AbstractEventLoop | None:
    """获取已注册的主事件循环，未注册时返回 None"""
    with _main_loop_lock:
        return _main_loop_ref


def run_on_main_loop(coro, timeout: int = 120):
    """
    安全地在主事件循环上执行协程并同步返回结果。

    - 如果主循环已注册（服务器运行时）：通过 run_coroutine_threadsafe 调度
    - 如果主循环未注册（独立脚本/测试）：降级为 asyncio.run()

    Args:
        coro: 要执行的协程
        timeout: 超时秒数（默认 120s），防止死锁

    Returns:
        协程的返回值
    """
    main_loop = get_main_loop()
    if main_loop is not None and main_loop.is_running():
        future = asyncio.run_coroutine_threadsafe(coro, main_loop)
        return future.result(timeout=timeout)
    else:
        # 降级：独立脚本或测试环境，无主循环
        return asyncio.run(coro)
