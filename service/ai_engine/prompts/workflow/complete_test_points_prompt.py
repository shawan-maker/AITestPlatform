from langchain_core.prompts import PromptTemplate

# 统一的 prompt template，使用 max_test_points_section 动态控制数量限制
prompt = PromptTemplate.from_template(
    template="""
你是一位资深的软件测试工程师，请根据提供原始的需求文档、测试点和覆盖率分析报告，去补充未覆盖的功能测试点（仅仅根据需求文档来分析，不要凭空产生需求）,添加在输入的测试点后面
原始功能文档：
{document}
已有测试点（不要重复）：
{test_points}
覆盖率报告：
{coverage_report}
    - 要求：
      请根据原始功能需求和测试点，补充未覆盖的测试点：
      1、包括功能正常情况下的测试点、边界测试点、异常测试点
      2、只需要补充功能方面的测试点，不需要设计非功能方面（如性能、安全等）
      {max_test_points_section}
    - 输出的测试点以json格式输出，要求如下：
      [
         {{"type":"功能测试","dimension":"正向验证","test_point":"输入正确的用户名密码，登录成功"}},
         {{"type":"功能测试","dimension":"边界测试","test_point":"用户名为空，登录失败"}},
         {{"type":"功能测试","dimension":"异常测试","test_point":"用户名为空，登录失败"}},
      ]
{user_prompt_section}""")

def get_max_test_points_section(max_test_points: int | None) -> str:
    """根据是否有数量限制，返回对应的数量限制说明（用于替换 template 中的 {max_test_points_section}）"""
    if max_test_points is not None:
        return "**重要：补充后的测试点总数必须 ≤ {} 个**".format(max_test_points)
    return ""



"""
你是一位资深的软件测试工程师，请根据提供原始的需求文档、测试点和覆盖率分析报告，去补充未覆盖的测试点,添加在输入的测试点后面
原始功能文档：
{document}
测试点：
{test_points}
覆盖率报告：
{coverage_report}
    - 要求：
      请根据原始功能需求和测试点，补充未覆盖的测试点：
      1、包括功能正常情况下的测试点、边界测试点、异常测试点
      2、针对需求整理出对应的非功能测试点（不需要凭空想象需求，有就写，没有就不写），如：性能测试、安全测试、兼容性测试、易用性测试等（跳过这一步，不补充非功能测试点）
    - 输出的测试点以json格式输出，要求如下：
      [
         {{"type":"功能测试","dimension":"正向验证","test_point":"输入正确的用户名密码，登录成功"}},
         {{"type":"功能测试","dimension":"边界测试","test_point":"用户名为空，登录失败"}},
         {{"type":"功能测试","dimension":"异常测试","test_point":"用户名为空，登录失败"}},
         {{"type":"性能测试","dimension":"负载测试","test_point":"登录接口响应时间在100ms以内"}},
         {{"type":"安全测试","dimension":"应用层安全","test_point":"登录接口未暴露用户名和密码"}},
         {{"type":"兼容性测试","dimension":"浏览器兼容器","test_point":"登录接口兼容IE8浏览器"}},
         {{"type":"易用性测试","dimension":"可操作性","test_point":"登录接口易于使用"}}
      ]
"""