from langchain_core.prompts import PromptTemplate

# 统一的 prompt template，使用 max_test_points_section 动态控制数量限制
prompt = PromptTemplate.from_template(
    template="""
    你是一位资深测试工程师,擅长根据需求文档分析测试点，接下来需要您根据需求整理生成功能测试点（仅仅根据需求文档来分析，不要凭空产生需求）。
    
    {max_test_points_section}
    
    输入的需求文档：{document}
    - 要求：
      1、仔细阅读需求文档，理解功能描述和业务逻辑
      2、根据功能描述，列出功能正常情况下的测试点
      3、分析功能的边界条件，设计边界测试点
      4、分析功能的异常情况，设计异常测试点
      5、只需要设计功能方面的测试点，不需要设计非功能方面（如性能、安全等）
      {max_test_points_requirement}
    - 输出的测试点以json格式输出，格式要求如下：
      [
         {{"type":"功能测试","dimension":"正向验证","test_point":"输入正确的用户名密码，登录成功"}},
         {{"type":"功能测试","dimension":"边界测试","test_point":"用户名为空，登录失败"}},
         {{"type":"功能测试","dimension":"异常测试","test_point":"用户名为空，登录失败"}}
      ]
    {user_prompt_section}
    {language_overlay}""")

def get_max_test_points_section(max_test_points: int | None) -> str:
    """根据是否有数量限制，返回对应的数量限制说明（用于替换 template 中的 {max_test_points_section}）"""
    if max_test_points is not None:
        return "### 数量控制（必须严格遵守）\n    你**必须**严格控制生成的测试点总数不超过 {} 个。\n    优先选择最关键、覆盖面最广的测试场景。".format(max_test_points)
    return ""

def get_max_test_points_requirement(max_test_points: int | None) -> str:
    """根据是否有数量限制，返回对应的数量要求说明（用于替换 template 中的 {max_test_points_requirement}）"""
    if max_test_points is not None:
        return "6、**严格限制**：生成的测试点数量必须 ≤ {} 个".format(max_test_points)
    return "6、根据需求复杂度，生成合理数量的测试点"




