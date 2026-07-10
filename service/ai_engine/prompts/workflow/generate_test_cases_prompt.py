from langchain_core.prompts import PromptTemplate

# 统一的 prompt template，使用 max_test_points_section 动态控制数量限制
prompt = PromptTemplate.from_template(
    template='''
    你是一位资深测试工程师，请基于下面功能整理的出来的测试点，结合覆盖功能 + 探测缺陷的思维生成标准的测试用例，
    如果提供已经编写的测试用例，则在提供的测试用例基础上补充未覆盖测试点的用例
    如果未提供已经编写的测试用例，则根据测试点生成测试用例

    {max_test_points_section}

    输出的用例，包含测试用例的八要素，：
        用例编号(case_id)
        用例名称(case_name)
        优先级(priority) 
        用例类型(type)
        维度(dimension)
        前置步骤(preconditions)
        测试步骤(test_steps) 
        输入数据(test_data) 
        预期结果(expected_result)
        实际结果(actual_result)
    要以json格式输出，输出格式要求为：
        [
            {{
                "case_id": "用例编号",
                "case_name": "用例名称",
                "priority": "优先级",
                "type": "用例类型",
                "dimension": "维度",
                "preconditions": "前置步骤",
                "test_steps": "测试步骤",
                "test_data": "输入数据",
                "expected_result": "预期结果",
                "actual_result": "实际结果"
            }},
            ...
        ]
    {max_test_points_requirement}
    输入测试点：
    {points}
    {user_prompt_section}
    {language_overlay}
    '''
)

def get_max_test_points_section(max_test_points: int | None) -> str:
    """根据是否有数量限制，返回对应的数量限制说明（用于替换 template 中的 {max_test_points_section}）"""
    if max_test_points is not None:
        return "### 数量控制（必须严格遵守）\n**每个测试点仅生成1条测试用例**，总用例数必须等于测试点数，且**必须 ≤ {} 条**。".format(max_test_points)
    return ""

def get_max_test_points_requirement(max_test_points: int | None) -> str:
    """根据是否有数量限制，返回对应的数量要求说明（用于替换 template 中的 {max_test_points_requirement}）"""
    if max_test_points is not None:
        return "最多生成 {} 条用例。".format(max_test_points)
    return ""