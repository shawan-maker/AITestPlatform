"""测试环境模块 — 聚合各子包 schemas，兼容旧 import 路径。"""

from service.test_environment.database.schemas import *  # noqa: F403
from service.test_environment.file.schemas import *  # noqa: F403
from service.test_environment.function.schemas import *  # noqa: F403
from service.test_environment.variable.schemas import *  # noqa: F403

# 兼容旧常量
from service.test_environment.function.schemas import FUNCTION_FILE_PATTERN  # noqa: F401
