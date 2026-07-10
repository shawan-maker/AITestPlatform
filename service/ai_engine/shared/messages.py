"""SSE/日志双语消息目录。

提供 msg(key, lang, **kwargs) 函数，根据语言返回对应的中/英文消息文本。
"""

_MESSAGES = {
    # ── agent_stream.py: initial functional stage ──
    "stage.analyzing_and_gen": {
        "zh": "正在分析需求并生成测试用例...",
        "en": "Analyzing requirements and generating test cases...",
    },
    # ── pipeline.py: stage text ──
    "stage.parsing_doc": {
        "zh": "正在解析接口文档...",
        "en": "Parsing API document...",
    },
    "stage.gen_base_cases": {
        "zh": "正在为各接口生成基础用例...",
        "en": "Generating base cases for interfaces...",
    },
    "stage.base_cases_done": {
        "zh": "基础用例生成完毕",
        "en": "Base case generation complete",
    },
    "stage.edit_base_cases": {
        "zh": "请检查并编辑基础用例",
        "en": "Please review and edit base cases",
    },
    "stage.structure_cases": {
        "zh": "正在生成结构化测试用例...",
        "en": "Generating structured test cases...",
    },
    "stage.structure_done": {
        "zh": "结构化用例生成完毕",
        "en": "Structured case generation complete",
    },
    "stage.pre_run": {
        "zh": "正在预执行测试用例...",
        "en": "Pre-executing test cases...",
    },
    "stage.pre_run_done": {
        "zh": "预执行完毕",
        "en": "Pre-execution complete",
    },

    # ── pipeline.py: custom progress ──
    "pipeline.parse_done": {
        "zh": "解析完成，共发现 {count} 个接口",
        "en": "Parsing complete, found {count} interfaces",
    },
    "pipeline.gen_base_for": {
        "zh": "正在为「{name}」生成基础用例...",
        "en": "Generating base cases for \"{name}\"...",
    },
    "pipeline.base_done": {
        "zh": "✅ 「{name}」生成 {count} 条基础用例",
        "en": "✅ \"{name}\" generated {count} base cases",
    },
    "pipeline.base_fail": {
        "zh": "❌ 「{name}」生成失败: {error}",
        "en": "❌ \"{name}\" generation failed: {error}",
    },
    "pipeline.structure_for": {
        "zh": "正在为「{name}」生成结构化用例...",
        "en": "Generating structured cases for \"{name}\"...",
    },
    "pipeline.structure_done": {
        "zh": "✅ 「{name}」结构化完成: {count} 条",
        "en": "✅ \"{name}\" structured: {count} cases",
    },
    "pipeline.structure_fail": {
        "zh": "❌ 「{name}」结构化失败: {error}",
        "en": "❌ \"{name}\" structuring failed: {error}",
    },
    "pipeline.prerun_for": {
        "zh": "正在预执行「{name}」的用例...",
        "en": "Pre-executing cases for \"{name}\"...",
    },
    "pipeline.prerun_done": {
        "zh": "✅ 「{name}」预执行完成: {passed}/{total} 通过",
        "en": "✅ \"{name}\" pre-run: {passed}/{total} passed",
    },
    "pipeline.prerun_fail": {
        "zh": "❌ 「{name}」预执行失败",
        "en": "❌ \"{name}\" pre-execution failed",
    },
    "pipeline.user_selected": {
        "zh": "用户选择了 {count} 条用例进行结构化: {titles}",
        "en": "User selected {count} cases for structuring: {titles}",
    },

    # ── tools.py: MCP tool messages ──
    "tools.searching_req": {
        "zh": "🔍 [阶段1/3] 开始从知识库检索需求文档...",
        "en": "🔍 [Phase 1/3] Searching knowledge base for requirements...",
    },
    "tools.calling_rag": {
        "zh": "  → 正在调用 RAG 检索服务，请稍候...",
        "en": "  → Calling RAG search service, please wait...",
    },
    "tools.search_done_preview": {
        "zh": "  → 检索完成，已获取需求内容（预览: {preview}）",
        "en": "  → Search complete, got requirement content (preview: {preview})",
    },
    "tools.no_match_req": {
        "zh": "  ⚠️ 未检索到匹配的需求文档",
        "en": "  ⚠️ No matching requirement documents found",
    },
    "tools.req_search_done": {
        "zh": "✅ [阶段1完成] 需求文档检索完毕",
        "en": "✅ [Phase 1 Complete] Requirement search finished",
    },
    "tools.gen_starting": {
        "zh": "🧪 开始生成测试点与测试用例...",
        "en": "🧪 Generating test points and test cases...",
    },
    "tools.init_workflow": {
        "zh": "  → 正在初始化用例生成工作流...",
        "en": "  → Initializing case generation workflow...",
    },
    "tools.calling_llm": {
        "zh": "  → 调用大模型生成测试点和用例（耗时较长请耐心等待）...",
        "en": "  → Calling LLM to generate test points and cases (may take a while)...",
    },
    "tools.gen_done": {
        "zh": "  ✅ 测试用例生成完毕: {count} 条用例",
        "en": "  ✅ Test cases generated: {count} cases",
    },
    "tools.saving_result": {
        "zh": "  → 正在保存生成结果到会话...",
        "en": "  → Saving results to session...",
    },
    "tools.saved": {
        "zh": "  → 结果已保存",
        "en": "  → Results saved",
    },
    "tools.searching_api_doc": {
        "zh": "🔍 [阶段1/3] 开始从知识库检索接口文档...",
        "en": "🔍 [Phase 1/3] Searching knowledge base for API documents...",
    },
    "tools.rag_streaming": {
        "zh": "  → 正在调用 RAG 流式检索服务（流式模式）...",
        "en": "  → Calling RAG streaming search service...",
    },
    "tools.search_done_api": {
        "zh": "  → 检索完成（预览: {preview}）",
        "en": "  → Search complete (preview: {preview})",
    },
    "tools.no_match_api": {
        "zh": "  ⚠️ 未检索到匹配的接口文档",
        "en": "  ⚠️ No matching API documents found",
    },
    "tools.api_search_done": {
        "zh": "✅ [阶段1完成] 接口文档检索完毕",
        "en": "✅ [Phase 1 Complete] API document search complete",
    },
    "tools.gen_base_starting": {
        "zh": "🧪 [阶段2/3] 开始生成基础接口测试用例...",
        "en": "🧪 [Phase 2/3] Generating base API test cases...",
    },
    "tools.parsing_and_gen": {
        "zh": "  → 接口文档解析完成，正在调用工作流生成用例...",
        "en": "  → API document parsed, calling workflow to generate cases...",
    },
    "tools.base_gen_done": {
        "zh": "  ✅ 基础接口用例生成完毕: {count} 条用例",
        "en": "  ✅ Base API cases generated: {count} cases",
    },
    "tools.api_gen_done": {
        "zh": "✅ [阶段3完成] 接口测试用例生成完毕",
        "en": "✅ [Phase 3 Complete] API test case generation complete",
    },

    # ── case_generator_workflow.py ──
    "wf.node1_start": {
        "zh": "【开始执行节点】 1、基于需求生成测试点：",
        "en": "[Node Start] 1. Generating test points from requirements:",
    },
    "wf.node1_done": {
        "zh": "【执行节点完成】 1、基于需求生成测试点：{count}",
        "en": "[Node Complete] 1. Generated {count} test points from requirements",
    },
    "wf.node2_skip": {
        "zh": "【跳过】测试点数量已达上限（{current}/{max}），跳过覆盖率验证",
        "en": "[Skip] Test point count reached limit ({current}/{max}), skipping coverage check",
    },
    "wf.node2_start": {
        "zh": "【开始执行节点】 2、验证测试点覆盖率：",
        "en": "[Node Start] 2. Verifying test point coverage:",
    },
    "wf.node2_done": {
        "zh": "【执行节点完成】 2、验证测试点覆盖率：",
        "en": "[Node Complete] 2. Test point coverage verified",
    },
    "wf.node3_start": {
        "zh": "【开始执行节点】 3、对未覆盖的测试点补全：",
        "en": "[Node Start] 3. Completing uncovered test points:",
    },
    "wf.node3_done": {
        "zh": "【执行节点完成】 3、对未覆盖的测试点补全,补充了{added}个，总数量为：{total}",
        "en": "[Node Complete] 3. Added {added} test points, total: {total}",
    },
    "wf.node3_1_start": {
        "zh": "【开始执行节点】 3.1 创建测试点：",
        "en": "[Node Start] 3.1 Creating test points:",
    },
    "wf.node3_1_done": {
        "zh": "✅ 测试点生成完毕: {count} 个测试点",
        "en": "✅ Test point generation complete: {count} test points",
    },
    "wf.node3_1_end": {
        "zh": "【执行节点完成】 3.1 创建测试点",
        "en": "[Node Complete] 3.1 Test points created",
    },
    "wf.node3_2_start": {
        "zh": "【开始执行节点】 3.2 基于测试点生成测试用例：",
        "en": "[Node Start] 3.2 Generating test cases from test points:",
    },
    "wf.node3_2_done": {
        "zh": "【执行节点完成】 3.2 基于测试点生成测试用例，共{count}条",
        "en": "[Node Complete] 3.2 Generated {count} test cases from test points",
    },
    "wf.count_control": {
        "zh": "[数量控制] 用户指定{max}个, 已有{current}个测试点, 跳过补全",
        "en": "[Count Control] User specified {max}, already have {current} test points, skipping completion",
    },

    # ── api_basecase_workflow.py ──
    "api_wf.node1_start": {
        "zh": "【开始执行节点】 1、生成api基础测试用例：",
        "en": "[Node Start] 1. Generating API base test cases:",
    },
    "api_wf.node1_done": {
        "zh": "【执行节点完成】 1、生成api基础测试用例：",
        "en": "[Node Complete] 1. API base test cases generated",
    },
    "api_wf.node2_start": {
        "zh": "【开始执行节点】 2、验证api基础测试用例覆盖率：",
        "en": "[Node Start] 2. Verifying API base case coverage:",
    },
    "api_wf.node2_done": {
        "zh": "【执行节点完成】 2、验证api基础测试用例覆盖率：",
        "en": "[Node Complete] 2. API base case coverage verified",
    },
    "api_wf.node3_start": {
        "zh": "【开始执行节点】 3、补充生成api基础测试用例：",
        "en": "[Node Start] 3. Completing API base test cases:",
    },
    "api_wf.node3_done": {
        "zh": "【执行节点完成】 3、补充生成api基础测试用例：",
        "en": "[Node Complete] 3. API base test cases completed",
    },
    "api_wf.node3_count": {
        "zh": "基础用例补充生成次数：{count}/{max}",
        "en": "Base case regeneration count: {count}/{max}",
    },
    "api_wf.node4_start": {
        "zh": "【开始执行节点】 4、输出所有基础测试用例",
        "en": "[Node Start] 4. Outputting all base test cases",
    },
    "api_wf.skip_coverage": {
        "zh": "用户有附加要求，跳过覆盖率校验，直接输出生成结果",
        "en": "User has additional requirements, skipping coverage check, outputting results directly",
    },
    "api_wf.max_regen": {
        "zh": "已达基础用例最大补充生成次数({max})，停止补充",
        "en": "Reached max base case regeneration count ({max}), stopping",
    },

    # ── api_case_main_workflow.py ──
    "main_wf.node1_start": {
        "zh": "【开始执行主流程节点】 1、生成api基础测试用例：",
        "en": "[Main Node Start] 1. Generating API base test cases:",
    },
    "main_wf.node1_done": {
        "zh": "【执行主流程节点完成】 1、生成api基础测试用例：",
        "en": "[Main Node Complete] 1. API base test cases generated",
    },
    "main_wf.node2_start": {
        "zh": "【开始执行主流程节点】 2、生成可执行结构化接口用例：",
        "en": "[Main Node Start] 2. Generating executable structured API cases:",
    },
    "main_wf.node2_done": {
        "zh": "【执行主流程节点完成】 2、生成可执行结构化接口用例",
        "en": "[Main Node Complete] 2. Executable structured API cases generated",
    },
    "main_wf.node4_start": {
        "zh": "【开始执行主流程节点】 4、保存结构化接口用例到数据库：",
        "en": "[Main Node Start] 4. Saving structured API cases to database:",
    },
    "main_wf.node4_save": {
        "zh": "一共生成 {count} 个结构化接口用例，并保存到 {path} 中",
        "en": "Generated {count} structured API cases, saved to {path}",
    },
    "main_wf.node4_done": {
        "zh": "【执行主流程节点完成】 4、保存结构化接口用例到数据库：",
        "en": "[Main Node Complete] 4. Structured API cases saved to database",
    },

    # ── api_runcase_workflow.py ──
    "run_wf.node1_start": {
        "zh": "【开始执行节点】 1、获取测试环境数据(测试数据、工具函数、测试文件、前置依赖接口)",
        "en": "[Node Start] 1. Loading test environment data (test data, functions, files, dependencies)",
    },
    "run_wf.node1_end": {
        "zh": "【执行节点结束】 1、获取测试环境数据(测试数据、工具函数、测试文件、前置依赖接口)",
        "en": "[Node Complete] 1. Test environment data loaded",
    },
    "run_wf.node2_start": {
        "zh": "【开始执行节点】 2、生成可运行的api结构化测试用例",
        "en": "[Node Start] 2. Generating runnable structured API test cases",
    },
    "run_wf.node2_done": {
        "zh": "【执行节点完成】 2、生成可运行的api结构化测试用例",
        "en": "[Node Complete] 2. Runnable structured API test cases generated",
    },
    "run_wf.node3_start": {
        "zh": "【开始执行节点】 3、执行生成的结构化接口用例",
        "en": "[Node Start] 3. Executing generated structured API cases",
    },
    "run_wf.node3_done": {
        "zh": "【执行节点完成】 3、执行生成的结构化接口用例",
        "en": "[Node Complete] 3. Structured API cases executed",
    },
    "run_wf.node4_start": {
        "zh": "【开始执行节点】 4、重新生成可运行的api结构化测试用例",
        "en": "[Node Start] 4. Regenerating runnable structured API test cases",
    },
    "run_wf.node4_done": {
        "zh": "【执行节点完成】 4、重新生成可运行的api结构化测试用例",
        "en": "[Node Complete] 4. Runnable structured API test cases regenerated",
    },
    "run_wf.node5_start": {
        "zh": "【开始执行节点】 5、输出生成的接口用例",
        "en": "[Node Start] 5. Outputting generated API cases",
    },
    "run_wf.node5_done": {
        "zh": "【执行节点完成】 5、输出生成的接口用例",
        "en": "[Node Complete] 5. Generated API cases outputted",
    },

    # ── agent_stream.py ──
    "stream.session_interrupted": {
        "zh": "服务重启，任务中断",
        "en": "Service restarted, task interrupted",
    },
    "stream.timeout": {
        "zh": "Agent 执行超时（{seconds}秒），请稍后重试",
        "en": "Agent execution timed out ({seconds}s), please retry later",
    },
    "stream.mock_functional": {
        "zh": "已生成功能用例预览（mock）。",
        "en": "Functional case preview generated (mock).",
    },
    "stream.mock_api": {
        "zh": "已生成接口基础用例预览（mock）。",
        "en": "API base case preview generated (mock).",
    },
    "stream.transition": {
        "zh": "✅ {stage} 阶段完成，正在准备下一阶段，请稍候...",
        "en": "✅ {stage} phase complete, preparing next phase, please wait...",
    },
    "stream.stage_search_req": {
        "zh": "正在检索需求文档...",
        "en": "Searching requirement documents...",
    },
    "stream.stage_search_api": {
        "zh": "正在检索接口文档...",
        "en": "Searching API documents...",
    },
    "stream.stage_gen_testcases": {
        "zh": "正在生成测试用例...",
        "en": "Generating test cases...",
    },
    "stream.stage_gen_base": {
        "zh": "正在生成接口测试用例...",
        "en": "Generating API test cases...",
    },

    # ── pipeline.py: summary & error ──
    "pipeline.all_failed": {
        "zh": "所有接口的基础用例生成均失败，请检查 LLM 配置或重试",
        "en": "All interface base case generation failed, please check LLM config or retry",
    },
    "pipeline.gen_fail_prefix": {
        "zh": "❌ 生成失败: {error}",
        "en": "❌ Generation failed: {error}",
    },
    "pipeline.unnamed": {
        "zh": "未命名",
        "en": "Unnamed",
    },
    "pipeline.struct_log": {
        "zh": "✅ 「{name}」结构化 {count} 条",
        "en": "✅ \"{name}\" structured: {count} cases",
    },
    "pipeline.prerun_rate": {
        "zh": "{icon} 「{name}」预执行通过率 {rate}",
        "en": "{icon} \"{name}\" pre-run pass rate {rate}",
    },
    "pipeline.summary_header": {
        "zh": "生成完成：共 {interfaces} 个接口，{cases} 条用例，整体通过率 {rate}",
        "en": "Generation complete: {interfaces} interfaces, {cases} cases, overall pass rate {rate}",
    },

    # ── tools.py ──
    "tools.no_req_doc": {
        "zh": "（未检索到相关需求文档）",
        "en": "(No matching requirement documents found)",
    },
    "tools.search_req_error": {
        "zh": "❌ [阶段1失败] 检索异常({etype}): {detail}",
        "en": "❌ [Phase 1 failed] Search error ({etype}): {detail}",
    },
    "tools.search_req_fallback": {
        "zh": "知识库检索失败（{etype}），请基于用户输入的需求描述直接进行测试用例设计。",
        "en": "Knowledge base search failed ({etype}). Please design test cases directly based on the user's requirement description.",
    },
    "tools.gen_cases_error": {
        "zh": "❌ 用例生成异常({etype}): {detail}",
        "en": "❌ Test case generation error ({etype}): {detail}",
    },
    "tools.no_api_doc": {
        "zh": "（未检索到相关接口文档）",
        "en": "(No matching API documents found)",
    },
    "tools.search_api_error": {
        "zh": "❌ [阶段1失败] 检索异常({etype}): {detail}",
        "en": "❌ [Phase 1 failed] Search error ({etype}): {detail}",
    },
    "tools.search_api_fallback": {
        "zh": "知识库检索失败（{etype}），请基于用户提供的接口信息直接设计测试用例。",
        "en": "Knowledge base search failed ({etype}). Please design test cases directly based on the provided API information.",
    },
    "tools.gen_base_error": {
        "zh": "❌ [阶段2/3失败] 用例生成异常({etype}): {detail}",
        "en": "❌ [Phase 2/3 failed] Case generation error ({etype}): {detail}",
    },

    # ── session_lifecycle.py ──
    "lifecycle.iface_gen_label": {
        "zh": "接口用例生成({count}个接口)",
        "en": "API case generation ({count} interfaces)",
    },
}


def msg(key: str, lang: str = "zh", **kwargs) -> str:
    """获取双语消息文本。

    Args:
        key: 消息键名
        lang: 语言 ("zh" 或 "en")
        **kwargs: 格式化参数

    Returns:
        对应语言的消息文本，找不到 key 时返回 key 本身
    """
    entry = _MESSAGES.get(key)
    if not entry:
        return key
    text = entry.get(lang, entry.get("zh", key))
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError):
            return text
    return text


def lang_from_overlay(language_overlay: str) -> str:
    """从 language_overlay 推断语言：非空 = en，空 = zh。"""
    return "en" if language_overlay else "zh"
