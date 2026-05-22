from typing import Annotated

from fastapi import FastAPI, Header, Form, UploadFile,status
import uvicorn
from pydantic import BaseModel, Field

"""
一、接口请求参数定义
1、定义查询参数：
http://127.0.0.1:9999/get/detail?user_id=1234
方法：直接在接口的业务处理函数里定义参数即可
@app.get("/get/user/info",description="获取用户信息")
def get_user_info(username: str):
    return {"code":200,"message":"获取用户信息成功","data":{"username":username}}
    
2、定义路径参数
http://127.0.0.1:9999/user/update/12312
方法：在接口路径中通过{参数名}定义路径参数，在接口的业务处理函数里定义同名参数
@app.get("/user/update/{user_id}",description="更新用户信息")
async def update_user(user_id: str):
    return {"code":200,"message":"用户信息更新成功","data":{"user_id":user_id}}
    
3、定义请求头参数
http://127.0.0.1:9999/user/update/12131?username=test123
方法：在接口的业务处理函数里定义参数，并使用Annotated装饰器指定参数类型为Header - 如：token: Annotated[str, Header()]
@app.get("/user/update/{user_id}",description="更新用户信息")
async def update_user(user_id: str,username: str, token: Annotated[str, Header()]):
    return {"code":200,"message":"用户信息更新成功","data":{"name":username,"token":token,"user_id":user_id}}
    
4、定义请求体参数
    json格式：
      - 通过 pydantic 的 BaseModel 来定义json请求体参数的字段和类型
      - 在接口的业务处理函数里定义参数，并使用Annotated装饰器指定参数类型为Body - 如：login_data: Annotated[LoginModel, Body()]
            {
                "username": "test",
                "password": "<PASSWORD>",
            }
    form格式：
      - 在接口的业务处理函数里定义参数，并使用Annotated装饰器指定参数 - 如：username: Annotated[str, Form(...,description="用户名")]
            username=test&password=12312&email=123%40qq.com
    文件上传：
     参数直接使用fastapi.UploadFile类型进行申明即可。
     
二、业务处理（与数据库交互）
    1、写原生的sql语句，去操作数据库
    2、通过ORM模型去操作数据库（通过python代码实现，不需要写sql）
        一张数据库表 ——  一个模型类
        表中的每个字段 —— 模型类的每个属性
        表中的每条记录 —— 模型类的每个实例对象
    ORM模型框架：
        1、sqlmodel(SQLAlchemy + pydantic)   ——  fastapi团队开发
        2、Tortoise ORM(语法使用方法 和Django中的ORM类型，但底层使用的是sqlalchemy)  —— 异步框架
        3、sqlalchemy(ORM框架)
    数据库操作： fastapi + Tortoise ORM + mysql

三、返回响应
    1、响应状态码
         - 在接口声明的装饰器中通过status字段去申明
         @app.post("/api/v1/register",description="用户注册接口",status_code=status.HTTP_200_OK)
    2、响应体
         - 默认返回json数据：直接返回响应体数据即可
                return {"code":200,"message":"注册成功","data":{"username":username,"password":password,"email":email}}
         - 自定义响应内容：
            - 返回json数据（同默认）：
                    return JSONResponse(status_code=404, content={"message": "Item not found"})
             - 返回html数据：
                    return HTMLResponse(content="<h1>Hello World</h1>", status_code=200)
            - 返回文件数据：
                    return FileResponse(path="test.txt", media_type="text/plain", filename="test.txt")
            - 返回流式数据：
                    retrun StreamingResponse(生成器对象) —— 常用于与大模型交互
    3、响应头
            headers = {"X-Cat-Dog": "alone in the world", "Content-Language": "zh-CN"}
            return JSONResponse(content=content, headers=headers)
    4、响应cookie
            response = JSONResponse(content=content)
            response.set_cookie(key="fakesession", value="fake-cookie-session-value")
            return response
    5、响应体返回的字段声明
"""



# 创建一个FastAPI应用
app = FastAPI()

# 定义登录接口的请求体参数模型
class LoginModel(BaseModel):
    username: str = Field(description="用户名")
    password: str = Field(description="密码")

# 1、定义接口
@app.post("/api/v1/register",description="用户注册接口",status_code=status.HTTP_200_OK)
def register(username: Annotated[str, Form(...,description="用户名")],
             password: Annotated[str, Form(...,description="密码")],
             email: Annotated[str, Form(...,description="邮箱")]):
    return {"code":200,"message":"注册成功","data":{"username":username,"password":password,"email":email}}


@app.post("/api/v1/login",description="用户登录接口")
def login(login_data: LoginModel):
    return {"code":200,"message":"登录成功","data":{"user":login_data.username,"token":login_data.password}}

@app.get("/get/user/info",description="获取用户信息")
def get_user_info(username: str):
    # 2、请求参数接收

    # 3、 处理业务逻辑

    # 4、 响应返回
    return {"code":200,"message":"获取用户信息成功","data":{"username":username}}

@app.get("/get/detail",description="获取详情信息")
async def get_detail(user_id: str):
    # 2、请求参数接收

    # 3、 处理业务逻辑

    # 4、 响应返回
    return {"code":200,"message":"获取用户详情成功","data":{"user_id":user_id}}


@app.get("/user/update/{user_id}",description="更新用户信息")
async def update_user(user_id: str,username: str, token: Annotated[str, Header()]):
    # 2、请求参数接收

    # 3、 处理业务逻辑

    # 4、 响应返回
    return {"code":200,"message":"用户信息更新成功","data":{"name":username,"token":token,"user_id":user_id}}


@app.post("/upload/file",description="上传文件接口")
def upload_file(file: UploadFile):
    return {"code":200,"message":"上传成功","data":{"file":file}}

if __name__ == '__main__':
    uvicorn.run(app, host="127.0.0.1", port=9999)