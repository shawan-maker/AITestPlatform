"""
获取用例执行的前后置脚本中可用的函数列表
输出：
    [
        {
            "name":"函数名称",
            "params":"函数参数",
            "desc":"函数描述"
        },
                {
            "name":"函数名称",
            "params":"函数参数",
            "desc":"函数描述"
        }
    ]

"""
import types
# 添加目标项目的 tests 目录到搜索路径
# import sys
# sys.path.append(r"D:\PyProject\TestApiEngineXin\tests")
# import Tools




from typing import Dict, Any, List
import inspect
from config.settings import BASE_DIR


# from test_data import Tools


def get_module_functions(source_code: object) -> List[Dict[str,Any]]:
    """从源代码字符串中获取函数列表"""
    # 1. 创建一个空模块对象
    module = types.ModuleType("dynamic_tools")

    # 2. 将源代码字符串编译并执行到模块的命名空间中
    exec(compile(source_code, "<string>", "exec"), module.__dict__)
    functions = []
    # 获取模块中的函数列表
    function_list = inspect.getmembers(module,predicate=inspect.isfunction)
    # 遍历函数列表
    for name,func_obj in function_list:
        # 获取函数参数
        params = inspect.signature(func_obj).parameters
        # 获取函数描述
        desc = inspect.getdoc(func_obj)
        functions.append({"name":name,"params":list(params.keys()),"desc":desc})
    return functions

if __name__ == '__main__':
    file_path = BASE_DIR + r"\test_data\Tools.py"
    result = get_module_functions(open(file_path, "r", encoding="utf-8").read())
    print(result)