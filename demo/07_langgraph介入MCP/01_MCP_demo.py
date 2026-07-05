from mcp.server.fastmcp import FastMCP

# 1、实例话一个FastMCP对象
mcp = FastMCP("mcp_demo")

# 2、定义MCP服务的工具函数
@mcp.tool(description="打印hello world")
def hello_world():
    return "hello world"

@mcp.tool(description="加法运算")
def add(a: int, b: int):
    print(f"正在执行加法运算：{a} + {b}，结果是：{a + b}")
    return a + b

@mcp.tool(description="乘法运算")
def multiply(a: int, b: int):
    print(f"正在执行乘法运算：{a} * {b}，结果是：{a * b}")
    return a * b

@mcp.tool(description="获取城市天气")
def get_weather(city: str):
    print(f"正在获取{city}天气信息,结果是：晴天")
    return f"{city}的天气是晴天"

if __name__ == '__main__':
    # # 使用studio启动MCP服务
    # mcp.run(transport="studio")
    # 使用http启动MCP服务
    mcp.run(transport="streamable-http")