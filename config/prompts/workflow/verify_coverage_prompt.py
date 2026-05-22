from langchain_core.prompts import PromptTemplate

prompt = PromptTemplate.from_template(
    template="""
你是一位资深的软件测试工程师，请根据提供原始的需求文档和测试点，去分析
原始功能文档：
{document}
测试点：
{test_points}
如果测试点覆盖了所有的功能，则回复：测试点已经全部覆盖
    分析覆盖率的原则：
      1、测试点涵盖了功能正常情况下的测试点、边界测试点、异常测试点
      2、不需要考虑非功能方面测试点（如性能、安全等）
如果没有全部覆盖，请给出覆盖率分析报告，并整理出未覆盖的点
""")