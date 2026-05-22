"""
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

"""
from tortoise.models import Model
from tortoise import fields, Tortoise, run_async


# ============================================定义模型类============================================
class UserModel(Model):
    """定义用户模型"""
    id = fields.IntField(pk=True, description="用户id")
    username = fields.CharField(max_length=255,description="用户名")
    password = fields.CharField(max_length=255,description="密码")
    email = fields.CharField(max_length=255,description="邮箱")
    age = fields.IntField(description="年龄")
    # 定义外键关联
    # related_name="users"：定义反向查询的名字
    # 正向：用户 → 找项目      user.project
    # 反向：项目 → 找所有用户   project.users.all()
    project = fields.ForeignKeyField("models.ProjectModel", related_name="users", description="项目")
    # 定义反向关联 —— 与社群表反向关联（多对多）
    communities = fields.ReverseRelation["CommunityModel"]

    class Meta:
        # 数据库表名
        table = "user"


class ProjectModel(Model):
    """定义项目模型"""
    id = fields.IntField(pk=True,description="项目id")
    project_name = fields.CharField(max_length=255,description="项目名")
    project_desc = fields.CharField(max_length=255,description="项目描述")
    project_status = fields.CharField(max_length=255,description="项目状态")
    # create_time = fields.DatetimeField(auto_now_add=True,precision=0, description="创建时间")
    # 定义反向关联
    users = fields.ReverseRelation["UserModel"]

    class Meta:
        # 数据库表名
        table = "project"

class CommunityModel(Model):
    """社群表"""
    id = fields.IntField(primary_key=True, description="社群id")
    name = fields.CharField(max_length=255, description="社群名称")
    users = fields.ManyToManyField("models.UserModel", related_name="communities", description="用户id")

# =============================================配置数据库连接信息=====================================
async def init_db():
    await Tortoise.init(
        db_url="mysql://root:root@localhost:3306/test",
        modules={"models": ["__main__"]} # 模型所在的模块
    )
    await Tortoise.generate_schemas()

run_async(init_db())