from langchain_core.prompts import PromptTemplate

# 接口文档解析提示词
api_parser_prompt = PromptTemplate.from_template(
    template="""
    你是一个接口分析专家，请你从下方提供的接口文本描述中提取所有接口的关键信息，
    并转换为统一结构化 JSON 格式。

    ### 重要约束
        - 严禁编造或推测文档中未明确提及的信息
        - 只提取文档中明确存在的字段和参数
        - 如果某个字段在文档中不存在，请设置为 null 或空数组
        - 如果文档中包含示例值（如 example、示例值、如"xxx"、例如13800138000 等），请提取到 example 字段；如果文档中没有示例，example 填 null，不要编造
        - **必须提取文档中的每一个接口，不要遗漏任何接口**

    ### 规则说明
        - 请求体中每个字段都需标注 required，若文档无明确说明，默认true（保守原则）
        - 参数需要按类型分类到 header、path、query 三个数组中,
        - 对于常见的非必填请求头无需保存到header中，比如：Accept-Encoding,Accept-Language、Origin等
        - 路径参数识别：URL中用{{}}包围的变量（如{{userId}}、{{id}},{{user_id}}）
        - 无请求体时，requestBody 各字段均填 null
        - 响应需要包含 http_code、description、media_type 和 response_body
        - responses数组中，要把接口文档中描述的所有可能的响应场景都列出来，并给出对应的响应体示例，方便后续的用例生成(要进行预期结果校验)
        - 如果文档中没有明确的响应示例，response_body 设置为空对象 {{}}
        - nested_fields 字段：仅当字段 type 为 "object" 时才包含此字段，用于描述对象内部的字段结构
        - array_item_fields 字段：仅当字段 type 为 "array" 时才包含此字段，用于描述数组元素的字段结构
        - 对于 string、integer、boolean、number 等基础类型，不要包含 nested_fields 和 array_item_fields 字段

    ### 输出格式要求：
    你必须输出一个 JSON 数组，数组中每个元素代表一个接口。格式如下：
        [
          {{
            "path": "API路径",
            "method": "HTTP方法(GET/POST/PUT/DELETE等)",
            "summary": "接口的简要名称",
            "parameters": {{
              "header": [{{
                  "name": "参数名",
                  "type": "参数类型",
                  "description": "参数说明",
                  "required": true/false,
                  "example": "示例值（文档中有则提取，无则null）"
              }}],
              "path": [{{
                  "name": "参数名",
                  "type": "参数类型",
                  "description": "参数说明",
                  "required": true/false,
                  "example": "示例值（文档中有则提取，无则null）"
              }}],
              "query": [{{
                  "name": "参数名",
                  "type": "参数类型",
                  "description": "参数说明",
                  "required": true/false,
                  "example": "示例值（文档中有则提取，无则null）"
              }}]
            }},
            "requestBody": {{
              "content_type": "请求体类型，如 application/json，无请求体时为null",
              "body": [
                {{
                  "name": "字段名",
                  "type": "string|integer|boolean|number等基础类型",
                  "description": "字段说明",
                  "required": true/false,
                  "example": "示例值（文档中有则提取，无则null）"
                }}
              ]
            }},
            "responses": [{{
              "http_code": "状态码",
              "description": "响应描述",
              "media_type": "响应内容类型，如 application/json",
              "response_body": {{"示例响应数据": "值"}}
            }}]
          }},
          // ... 文档中每个接口一个对象，全部放入这个数组中，不得遗漏
        ]
    请处理以下接口数据，提取其中所有接口，输出完整的结构化JSON数组结果：
    {input_text}
""")
