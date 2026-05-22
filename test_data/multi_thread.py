from concurrent.futures import ThreadPoolExecutor
from time import sleep

def work(name):
    print(f"{name} begin to work")
    print(name)
    sleep(2)
    print(f"{name} end to work")

name_list = ["tom", "bob", "alice", "lucy", "jack"]

# 创建线程池(设置线程池的最大工作线程数为3)
with ThreadPoolExecutor(max_workers=3) as executor:
    future_list = []
    # 提交任务到线程池
    for name in name_list:
        # 提交任务到线程池(返回一个Future对象) - 第一个参数是要执行的函数，第二个参数是函数的参数
        future = executor.submit(work, name)
        # 将返回的Future对象添加到列表中
        future_list.append(future)
    # 等待线程池中的所有任务执行完毕，获取每个任务的返回结果
    result = [future.result() for future in future_list]
    print("result:",result)