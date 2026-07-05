from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.prompts import base

mcp = FastMCP("mcp_dev")

@mcp.tool(description="加法运算")
def add(a: int, b: int) -> int:
    """加法运算"""
    print(f"正在执行加法运算：{a} + {b}，结果是：{a + b}")
    return a + b

@mcp.resource("file:///{name}")
def get_file(name: str) -> str:
    """获取文件内容"""
    with open(name, "r",encoding='utf-8') as f:
        return f.read()

@mcp.prompt(title="debug_errorr")
def debug_errorr(error:str) -> list[base.Message]:
    """调试错误"""
    return [
        base.UserMessage(content=f"我看到了这个错误"),
        base.UserMessage(content=f"错误信息：{error}"),
        base.AssistantMessage(content=f"我正在处理这个错误"),
        base.AssistantMessage(content=f"请你帮我分析这个错误，并给出解决方案")
    ]

if __name__ == '__main__':
    mcp.run(transport="streamable-http")