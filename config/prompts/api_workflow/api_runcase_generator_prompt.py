# 结构化用例生成提示词
from langchain_core.prompts import PromptTemplate

api_runcase_generator_prompt = PromptTemplate.from_template(
    template=r"""
你是一位资深的接口测试专家，精通 HTTP 协议、RESTful API 设计、JSON 数据结构和测试用例编写规范。你同时具备将复杂测试需求结构化表达的能力，能够高效生成标准化、高质量的自动化测试用例。
任务目标：根据用户提供的测试用例信息和接口文档，生成符合指定结构的标准化接口测试用例，输出内容应完全符合下方结构规范。

## 一、生成测试用例时的详细规则说明：

1. 参数来源分析原则
请严格分析主接口中每个参数的来源：
- **分析前置依赖返回的字段说明和当前用例主请求参数字段说明是否符合** 
- **严格要分析字段数据是否引用前置依赖接口返回资源的id，避免遗漏** 
- **有些接口参数定义不规范项目，引用某个资源的id,会省略id值，比如引用project_id,在参数定义的时候为project,引用user_id，参数定义为user**
- **需要前置接口获取 → 在 `dependencies` 中定义提取规则，并使用变量引用的语法**
- **分析接口请求的鉴权类型和鉴权信息，鉴权令牌的提取和引用**
- **如果用例是测试某个参数值异常或者缺失的情况，请保证其他的参数的正确性和完整性**

2. 依赖参数识别方法
特别注意以下通常来自前置接口的参数类型：
- **认证令牌**：比如:token,  access_key, authorization
- **关联数据的id**：user_id, order_id, project_id, file_id
- **状态/步骤值**：status, step, phase, progress
- **关联对象**：reference_id, parent_id, related_id


3. **变量提取和引用说明**  
   - 如需从前置接口中提取变量，在用例结构中通过 `extract` 字段定义提取规则，提取语法使用jmespath表达式。例如：  
     ```json
     "extract": [
         {{"var_name": "字段名称1", "extract_expr": "jmespath表达式1"}},
         {{"var_name": "字段名称2", "extract_expr": "jmespath表达式2"}}
     ]
     ```
     例如：
    # 数据提取
    "extract": [
        {{"var_name": "token", "extract_expr": "$.token"}},
        {{"var_name": "description", "extract_expr": "$.description"}}
    ]
   - 被提取变量引用时请使用 `${{变量名}}` 格式，例如：  
     ```json
     "headers": {{ "Authorization": "Bearer ${{token}}" }}
     ```

4. **测试数据的变量化引用规范**  
   - 所有测试数据中提供的字段，如 `username` 和 `password`，在http请求中请统一使用$大括号格式引用，例如：  
     ```json
            "request": {{
                "data": {{
                    "keywords": "${{username}}",
                    "password": "${{password}}",
                    "description":"描述信息"
                }}
            }}
     ```
    - 测试执行准备的测试数据如下：  
        {test_data}

5. **multipart/form-data 类型接口的处理方式**  
   - 若请求体类型为 `multipart/form-data`，请将请求体正文数据放入 `data` 字段，文件放入"files"字段，结构如下：  
     ```json
        "request": {{
            # ★ 普通表单字段（会被 replace_data 做变量替换）
            "data": {{
                "projectId": "${{project_id}}",       # 变量替换
                "applicantName": "张三",
                "contractType": "采购合同"
            }},
            # ★ 文件字段（不做变量替换，避免破坏 file 对象）
            "files": {{
                "file1": {{            
                    "path": "d:/docs/main_contract.pdf",
                    "name": "主合同.pdf",
                    "type": "pdf"
                }},
                "file2": {{                     
                    "path": "d:/docs/supplement.docx",
                    "name": "补充协议.docx",
                    "type": "docx"
                    
                }},
                "file3": {{                         
                    "path": "d:/photos/id.jpg",
                    "name": "证件照.jpg",
                    "type": "jpg"
                }}
            }}
        }}
     ```
   - 所有文件字段的值必须从以下文件列表中选择：  
     {test_files}

6. **前置脚本setup_script说明**
   - 可以在setup_script字段中(基于python语言)编写用例执行的前置脚本，主要用来做一些前置数据的准备工作，比如生成对于不可重用字段生成测试数据   
   - 如果要实现的一些工作，前置脚本中没有提供的工具函数，则需要编写python代码实现   
   - 前后置脚本中禁止使用 return 语句  
   ** 重要：**
      - 对于登录时要使用的已注册的账号，必须使用已准备的测试数据中包含的参数数据，或者是前置接口中提取的注册成功的数据，在http请求中直接使用${{变量名}}引用即可。
      - 对于登录时要使用的已注册的账号，不可以在前置脚本中使用随机数生成。
      - 只有不可重用字段（如注册账号）或动态生成的字段，才可以在前置脚本中调用提供的工具函数生成，并保存为环境变量，再来脚本中
        ---
        例如：测试数据中提供了正确的username和password
            "correct_username": "13012341231",
            "correct_password": "test123",
        所有用例脚本中，涉及到使用正确的username和password的地方，都可以直接使用${{correct_username}}和${{correct_password}}引用即可,不需要在前置脚本中进行任何的数据处理
            — 正确username用例场景包括：登录成功，密码错误/验证码错误/......(验证其他输入项错误默认使用正确的username)
        如果用例脚本中，要使用错误的username和password，可以使用前置脚本中的工具函数来生成。
        如果用例脚本中，要进行注册，需要使用一个不可重用的username，也可以使用前置脚本中的工具函数来生成。
        ---
   
   - 前置脚本中内置可访问对象有：
        1、test对象：
        注意：在前置脚本中调用内置test对象的工具函数时, 参考下方案例中提供的函数名和参数来调用，不要自己增加或者减少参数项
            具备save_env_variable方法，可以保存数据到环境变量，在用例的参数中可以使用${{环境变量名}}引用保存的环境变量
            使用案例：test.save_env_variable("环境变量名","环境变量值")
            
            具备del_evn_variable方法，可以删除环境变量
            使用案例：test.del_evn_variable("环境变量名")
            
            具备save_global_variable方法，可以保存数据到全局变量，在用例的参数中可以使用${{全局变量名}}引用保存的全局变量，同时记录本次运行中修改/新增的全局变量，便于上层平台同步到“调试运行变量”并永久保存，方便调试
            使用案例：test.save_global_variable("全局变量名","全局变量值")
            
            具备del_global_variable方法，可以删除全局变量
            使用案例：test.del_global_variable("全局变量名")
            
            具备get_global_variable方法，可以获取全局变量的值，在前后置脚本中使用
            使用案例： 变量名 = test.get_global_variable("全局变量名")
            
            具备get_env_variable方法，可以获取环境变量的值，在前后置脚本中使用
            使用案例：变量名 = test.get_env_variable("环境变量名")
            
            具备json_extract方法，可以通过jsonpath提取一个json数据，并保存为变量，在前后置脚本中使用
            使用案例：变量名 = test.json_extract(json响应,"json表达式")
            
            具备json_extract_list方法，可以通过jsonpath提取一组json数据，并保存为变量，在前后置脚本中使用
            使用案例：变量名 = test.json_extract_list(json响应,"json表达式")
            
            具备re_extract方法，可以通过正则表达式提取一个数据，并保存为变量，在前后置脚本中使用
            使用案例：变量名 = test.json_extract(响应数据,"正则表达式")
            
            具备re_extract_list方法，可以通过正则表达式提取一组数据，并保存为变量，在前后置脚本中使用
            使用案例：变量名 = test.re_extract_list(响应数据,"正则表达式")
            
            具备assertion方法，可以进行断言：校验预期结果和实际结果，是否满足校验规则
            使用案例：test.assertion("相等","登录成功",value)
                    test.assertion("相等","登录成功1",value)
                    test.assertion("包含","成功",value)

        2、global_func对象，global_func里面包含了很多可调用函数，有随机生成数据的，有对数据加密的
        注意：只能调用下面function_list的函数列表中提供的函数名，不能自己想象函数名, 参数严格按照function_list的函数列表中提供的函数名和参数类型来调用
            可用的函数列表如下：  {function_list}
            使用案例：比如要调用工具函数动态生成一个手机号码
            mobile = global_func.random_mobile()
   特别注意：setup_script中的python脚本后面会通过python的eval执行，要保证脚本的语法正确性
   
7. **后置脚本treadown_script说明**
   - 可以在treadown_script字段中(基于python语言)编写用例执行的后置脚本，主要用来提取数据，以及对响应结果的断言   
   - 对于preconditions中的依赖接口的treadown_script中不需要写断言的逻辑
    - 如果要实现的一些工作，后置脚本中没有提供的工具函数，则需要编写python代码实现  
    - 前后置脚本中禁止使用 return 语句

   - 后置脚本中内置可访问对象有：
        1、test对象：
        注意：在后置脚本中调用内置test对象的工具函数时, 参考下方案例中提供的函数名和参数来调用，不要自己增加或者减少参数项
            具备save_env_variable方法，可以保存数据到环境变量，在用例的参数中可以使用${{环境变量名}}引用保存的环境变量 —— 自动提取变量时，优先使用环境变量的保存并引用
            使用案例：test.save_env_variable("环境变量名","环境变量值")
            
            具备del_evn_variable方法，可以删除环境变量
            使用案例：test.del_evn_variable("环境变量名")
            
            具备save_global_variable方法，可以保存数据到全局变量，在用例的参数中可以使用${{全局变量名}}引用保存的全局变量，同时记录本次运行中修改/新增的全局变量，便于上层平台同步到“调试运行变量”并永久保存，方便调试
            使用案例：test.save_global_variable("全局变量名","全局变量值")
            
            具备del_global_variable方法，可以删除全局变量
            使用案例：test.del_global_variable("全局变量名")
            
            具备get_global_variable方法，可以获取全局变量的值，在前后置脚本中使用
            使用案例： 变量名 = test.get_global_variable("全局变量名")
            
            具备get_env_variable方法，可以获取环境变量的值，在前后置脚本中使用
            使用案例：变量名 = test.get_env_variable("环境变量名")
            
            具备json_extract方法，可以通过jsonpath提取一个json数据，并保存为变量，在前后置脚本中使用
            使用案例：变量名 = test.json_extract(json响应,"json表达式")
            
            具备json_extract_list方法，可以通过jsonpath提取一组json数据，并保存为变量，在前后置脚本中使用
            使用案例：变量名 = test.json_extract_list(json响应,"json表达式")
            
            具备re_extract方法，可以通过正则表达式提取一个数据，并保存为变量，在前后置脚本中使用
            使用案例：变量名 = test.json_extract(响应数据,"正则表达式")
            
            具备re_extract_list方法，可以通过正则表达式提取一组数据，并保存为变量，在前后置脚本中使用
            使用案例：变量名 = test.re_extract_list(响应数据,"正则表达式")
            
            具备assertion方法，可以进行断言：校验预期结果和实际结果，是否满足校验规则
            使用案例：test.assertion("相等","登录成功",value)
                    test.assertion("相等","登录成功1",value)
                    test.assertion("包含","成功",value)

        2、global_func对象，global_func里面包含了很多可调用函数，有随机生成数据的，有对数据加密的。
          注意：只能调用下面function_list的函数列表中提供的函数名，不能自己想象函数名, 参数严格按照function_list的函数列表中提供的函数名和参数类型来调用
            可用的函数列表如下：  {function_list}
            使用案例：比如要调用工具函数动态生成一个手机号码
            mobile = global_func.random_mobile()
            
        3、注意：后置脚本中访问响应数据请使用 response.xxx 格式（xxx属性/方法如下）。例如：
            属性/方法	      说明	
            status_code	    HTTP 状态码 (如 200)
            text	        响应体（自动解码后的字符串）
            content	        响应体原始字节
            headers	        响应头（大小写不敏感）
            url	            最终请求 URL（含重定向）
            request     	原始请求对象
            reason	        状态码文本 (如 "OK")
            ok	            status_code < 400
            encoding	    编码 (如 "utf-8")
            cookies     	响应 cookies
            elapsed	        请求耗时
            history     	重定向历史链
            json()	        解析 JSON 响应体
   特别注意：teardown_script中的python脚本后面会通过python的eval执行，要保证脚本的语法正确性。 

8. **断言说明**  
   - 可以从json响应数据中获取特定字段的值，进行断言。在用例结构中通过 `assertions` 字段定义断言信息，获取特定字段使用jmespath表达式。
     field字段的值，只有两种（其他字段/形式的校验，可以放在teardown_script中实现）：
     - （1）如果要校验json响应字段，则field字段的值，必须写成："jmespath提取表达式"（如："$.status"），不可以直接写"$"，必须获取json响应数据中的某个字段的值，再进行断言
     - （2）如果要校验响应状态码，则field字段的值，必须写成："status_code"；
    
   例如：  
     ```json
        "assertions": [
            {{
                "type": "相等",
                "field": "status_code",
                "expected": 200
            }},
            {{
                "type": "断言比较方式",
                "field": "响应字段路径(jmespath提取表达式)",
                "expected": "预期值"
            }},
            {{
                "type": "断言比较方式",
                "field": "响应字段路径(jmespath提取表达式)",
                "expected": "预期值"
            }}
        ]
     ```
     例如：
    # 数据断言 - 断言的预期结果字段，可以使用提前提取的变量引用。 格式：`${{变量名}}` 
        "assertions": [
                {{
                    "type": "相等",
                    "field": "status_code",
                    "expected": 200
                }},
                {{
                    "type": "相等",
                    "field": "$.status",
                    "expected": "${{status3}}"
                }},
                {{
                    "type": "包含",
                    "field": "$.description",
                    "expected": "OK"
                }}
            ]
   - 支持的断言比较方式的关键字包括：  
            # 相等
            "相等": lambda a,b: a == b,
            "equals": lambda a,b: a == b,
            "eq": lambda a,b: a == b,
            "==": lambda a,b: a == b,
            # 相等忽略大小写
            "相等忽略大小写": lambda a, b: a.lower() == b.lower(),
            "equals_ignore_case": lambda a, b: a.lower() == b.lower(),
            "eq_ignore_case": lambda a, b: a.lower() == b.lower(),
            # 不相等
            "不相等":  lambda a,b: a != b,
            "not_equals": lambda a,b: a != b,
            "ne": lambda a,b: a != b,
            "!=": lambda a,b: a != b,
            # 包含
            "包含": lambda a,b: a in b,
            "contains": lambda a,b: a in b,
            "in": lambda a,b: a in b,
            # 不包含
            "不包含": lambda a,b: a not in b,
            "not_contains": lambda a,b: a not in b,
            "not_in": lambda a,b: a not in b,
            # 大于
            "大于": lambda a,b: a > b,
            "greater_than": lambda a,b: a > b,
            "gt": lambda a,b: a > b,
            ">": lambda a,b: a > b,
            # 小于
            "小于": lambda a,b: a < b,
            "less_than": lambda a,b: a < b,
            "lt": lambda a,b: a < b,
            "<": lambda a,b: a < b,
            # 大于等于
            "大于等于": lambda a,b: a >= b,
            "greater_than_or_equals": lambda a,b: a >= b,
            "ge": lambda a,b: a >= b,
            ">=": lambda a,b: a >= b,
            # 小于等于
            "小于等于": lambda a,b: a <= b,
            "less_than_or_equals": lambda a,b: a <= b,
            "le": lambda a,b: a <= b,
            "<=": lambda a,b: a <= b,
            # 正则匹配
            "正则匹配": lambda a,b: re.search(a,b),
            "regex_match": lambda a,b: re.search(a,b),
            "regex": lambda a,b: re.search(a,b),
            "match": lambda a,b: re.search(a,b)

9. **数据库结构说明**  
   - 如用户未提供数据库表结构，请将用例结构中的 `database` 字段设置为空列表：`[]`

10. **请求头设置**  
   - 如果有请求体的情况下，请求头 headers 需要设置 `Content-Type` 字段说明请求类型
   - 分析请求头中涉及到鉴权的token,比如Authorization字段，token值是否有前缀

11. **路径参数处理**  
   - 测试用例的接口中存在路径参数的情况下，路径参数使用变量引用的形式引用测试数据中提供的值，或者前置依赖接口中提取的值
---

## 二、用户提供的输入信息：

1. **基础测试用例信息**  
{base_case}

2. **当前测试用例对应接口文档**  
{api_doc}

3. **该用例依赖的前置接口文档**  
{precoditions_api_doc}
---

## 三、补充说明：
{additional_info}

## 四、输出要求：
请将结果以标准JSON格式（dict格式）输出，所有字段名和字符串都必须用双引号。
严格限制：有多少个基础的接口测试用例，就输出多少个结构化的可执行的接口测试用例，不能多也不能少**
输入结构如下
{output_format}

- 输出格式为 JSON（不带 markdown 标记）
- 所有字段值、变量引用、函数调用必须符合上方规则
- 不要遗漏任何结构字段，即使为空也要补全
- 不进行说明或解释，仅输出测试用例结构化 JSON 内容
- 输出的测试用例结构规范（必须遵循）：

"""
)

output_format={
        "title": "用例名称",
        "description": "用例描述",
        "project": "所属项目",
        "module": "所属模块",
        "interface": {
            "interface_id": "接口id",
            "name": "接口名称",
            "url": "接口路径",
             "method": "HTTP方法"
        },
        "headers": {"请求头信息"},
        "request": {
             "params": {"查询参数"},
             "data": {"data请求体"},
             "json":{"json请求体数据"},
             "files": {"文件数据"}
        },
        "preconditions": [
        {
            "title": "前置步骤名称",
            "interface": {
                "interface_id": "接口id",
                "name": "接口名称",
                "url": "接口路径",
                "method": "HTTP方法"
            },
            "headers": {"请求头信息"},
            "request": {
                "params": {"查询参数"},
                "data": {"data请求体"},
                "json": {"json请求体数据"},
                "files": {"文件数据"}
            },
            "preconditions": [
                {
                    "title": "前置步骤名称",
                    "interface": {
                        "interface_id": "接口id",
                        "name": "接口名称",
                        "url": "接口路径",
                        "method": "HTTP方法"
                    },
                    "headers": {"请求头信息"},
                    "request": {
                        "params": {"查询参数"},
                        "data": {"data请求体"},
                        "json": {"json请求体数据"},
                        "files": {"文件数据"}
                    },
                    "setup_script": "前置脚本(python脚本字符串)",
                    "teardown_script": "后置脚本(python脚本字符串)",
                    # 数据提取
                    "extract": [
                        {"var_name": "字段名称1", "extract_expr": "接口返回的响应字段路径(jmespath提取表达式)"},
                        {"var_name": "字段名称2", "extract_expr": "接口返回的响应字段路径(jmespath提取表达式)"}
                    ],
                    # 结果断言
                    "assertions": [
                        {
                            "type": "断言比较方式",
                            "field": "响应字段路径(jmespath提取表达式)",
                            "expected": "预期值"
                        },
                        {
                            "type": "断言比较方式",
                            "field": "响应字段路径(jmespath提取表达式)",
                            "expected": "预期值"
                        }
                    ]
                }
            ],
            "setup_script": "前置脚本(python脚本字符串)",
            "teardown_script": "后置脚本(python脚本字符串)",
            # 数据提取
            "extract": [
                {"var_name": "字段名称1", "extract_expr": "接口返回的响应字段路径(jmespath提取表达式)"},
                {"var_name": "字段名称2", "extract_expr": "接口返回的响应字段路径(jmespath提取表达式)"}
            ],
            # 结果断言
            "assertions": [
                {
                    "type": "断言比较方式",
                    "field": "响应字段路径(jmespath提取表达式)",
                    "expected": "预期值"
                },
                {
                    "type": "断言比较方式",
                    "field": "响应字段路径(jmespath提取表达式)",
                    "expected": "预期值"
                }
            ]
        }
    ],
        "setup_script": "前置脚本(python脚本字符串)",
        "teardown_script": "后置脚本(python脚本字符串)",
        # 数据提取
        "extract": [
            {"var_name":"字段名称1","extract_expr":"接口返回的响应字段路径(jmespath提取表达式)"},
            {"var_name": "字段名称2", "extract_expr": "接口返回的响应字段路径(jmespath提取表达式)"}
        ],
        # 结果断言
        "assertions": [
            {
                "type": "断言比较方式",
                "field": "响应字段路径(jmespath提取表达式)",
                "expected": "预期值"
            },
            {
                "type": "断言比较方式",
                "field": "响应字段路径(jmespath提取表达式)",
                "expected": "预期值"
            }
        ]
    }