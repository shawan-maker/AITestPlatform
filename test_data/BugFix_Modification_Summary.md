# API用例管理页Bug修复 - 修改说明

## 修复内容概览

本次修改主要解决了API用例管理页面的4个关键问题：

### Bug #1: 变量文件选择功能 ✅
**问题**: 接口调试tab和测试用例tab中的变量文件选择是硬编码的静态数据  
**解决方案**:
- 前端：动态加载"变量管理"页面中的变量文件列表（调用 `/env/environments` API）
- 后端：已支持接收 `environment_id` 参数，用于加载对应变量文件的环境配置
- 用户选择变量文件后，该ID会传递给后端调试API

**修改文件**:
- `frontend/src/views/cases/ApiTestWorkspaceView.vue`
  - 添加 `environmentList`, `debugEnvId`, `caseEnvId` 状态变量
  - 添加 `refreshEnvironmentList()`, `selectDebugEnvironment()`, `selectCaseEnvironment()` 方法
  - 替换接口调试tab和测试用例tab中的硬编码下拉菜单为动态列表

---

### Bug #2: 前置/后置操作Tab优化 ✅
**问题**: 前置操作和后置操作tab只有简单的代码编辑器和方法帮助器折叠面板  
**解决方案**: 参考 `CaseEditor.vue` 的设计模式，改为左右分栏布局：
- **左侧**: Python代码编辑器（MonacoJsonEditor）
- **右侧**: 操作模板展示区（可点击插入函数提示）

**模板包含的内容**:
- **前置操作模板**: 设置临时/环境变量、执行SQL、获取变量、发送请求、等待等
- **后置操作模板**: 获取响应体、JSONPath提取、正则提取、断言、设置变量、保存文件、记录日志等

**修改文件**:
- `frontend/src/views/cases/ApiTestWorkspaceView.vue`
  - 重构PreOps和PostOps tab的template结构
  - 添加 `insertPreTemplate()`, `insertPostTemplate()` 方法
  - 添加 `.prepost-container` CSS样式（左右分栏布局）

---

### Bug #3: 文件上传支持 ✅
**问题**: 请求只支持JSON body格式，不支持文件上传  
**解决方案**: 在Body tab中添加form-data文件上传选项：
- 添加Body类型选择器（JSON / Form-Data）
- Form-Data模式下显示字段名和文件选择下拉框
- 调用 `listUploadedFiles` API获取已上传的文件列表
- 在 `buildDebugPayload()` 中添加文件信息到payload

**修改文件**:
- `frontend/src/views/cases/ApiTestWorkspaceView.vue`
  - Body tab中添加类型选择器和表单组件
  - 添加 `bodyType`, `uploadFileOptions`, `uploadFieldName`, `selectedUploadId` 状态变量
  - 添加 `loadUploadFiles()`, `displayFileLabel()` 方法
  - 修改 `buildDebugPayload()` 支持文件上传信息

---

### Bug #4: 端到端测试与结果展示优化 ✅
**问题**: 
1. 点击调试后无法完整组装请求信息
2. 结果直接以JSON字符串形式展示，不够直观
3. 缺少日志信息tab

**解决方案**:

#### 4.1 完善请求组装
- 修改 `buildDebugPayload()` 方法，确保包含所有字段：
  - method, path, headers, query, path_params, body
  - extracts, assertions
  - preconditions, postconditions（Python代码）
  - files（文件上传信息）

#### 4.2 结构化结果展示
替换原来的简单JSON展示，改为按Tab分类的结构化显示：

- **返回结果Tab**: 显示执行状态、耗时、错误信息（带颜色标识）
- **返回信息Tab**: 显示状态码、Content-Type、响应时间、响应体大小、响应内容
- **请求信息Tab**: 显示请求方法、URL、请求头、参数、请求体
- **抽取信息Tab**: 以表格形式展示提取的变量名、表达式、值
- **断言信息Tab**: 列表展示每个断言的结果（通过/失败带图标和背景色）

#### 4.3 新增日志信息Tab
- 逐条打印接口测试引擎返回的日志
- 不同级别使用不同颜色：
  - DEBUG: 绿色背景 (#6a9955)
  - INFO: 蓝色背景 (#3794ff)
  - WARNING/WARN: 黄色背景 (#cca700)
  - ERROR: 红色背景 (#f44747)

#### 4.4 后端增强
- 修改 `runner_gateway.py` 的 `execute_case_payload()` 方法
- 解析引擎返回的详细信息（response_info, request_info, extract_info, assert_info, log_data）
- 将详细信息存储在 `_debug_detail` 字段中
- 修改 `debug_api.py` 的 `debug_run_interface()` 接口
- 返回完整的调试结果数据（包含所有详情）

**修改文件**:
- `frontend/src/views/cases/ApiTestWorkspaceView.vue`
  - 重构响应区域UI（6个tab）
  - 添加结果解析相关状态变量（responseResult, responseDataInfo, requestInfo, extractInfo, assertInfo, logData）
  - 添加辅助方法（getStatusColor, getStatusLabel, formatSize, parseDebugResponse）
  - 修改 runDebug() 使用新的解析逻辑
  - 添加大量CSS样式（结构化展示、断言列表、日志容器等）

- `service/api_test/shared/runner_gateway.py`
  - 导入 json 模块
  - 在 execute_case_payload() 中初始化 detailed_result
  - 解析引擎返回的详细信息并合并到 result 中
  - 计算耗时并存入详细结果

- `service/api_test/debug/debug_api.py`
  - 修改 debug_run_interface() 接口返回值
  - 从 record.api_requests_info 提取 _debug_detail 信息
  - 合并所有信息到最终返回数据

---

## 技术细节

### 数据流图
```
用户填写请求信息 → buildDebugPayload() → debugRunInterface API (POST)
    ↓
后端接收 payload + environment_id + file_id
    ↓
TestEnvDataAssembler.get_test_env_data(environment_id) → 加载变量文件配置
    ↓
RunnerGateway.execute_case_payload() → TestRunner.execute_cases(case_payload)
    ↓
引擎执行完成 → 返回详细结果（包含 response/request/extract/assert/log）
    ↓
存储到 ApiCaseRunRecord.api_requests_info
    ↓
前端接收响应 → parseDebugResponse() → 结构化展示在各个Tab
```

### 关键API调用
1. **获取变量文件列表**: `GET /api/env/environments?project_id={id}`
2. **获取上传文件列表**: `GET /api/env/uploaded-files?project={id}`
3. **运行接口调试**: `POST /api/api-test/interfaces/{id}/debug-run`

### 兼容性说明
- 所有新增功能都是向后兼容的
- 如果后端没有返回详细信息，前端会优雅降级显示空状态
- 变量文件选择是可选的（未选择时会提示用户）

---

## 测试要点

### 功能测试
1. [ ] 进入API用例管理页，点击左侧接口
2. [ ] 在接口调试tab中，点击"选择变量文件"下拉菜单，确认能看到变量管理中的变量文件列表
3. [ ] 选择一个变量文件，点击调试按钮，确认能正常执行
4. [ ] 测试前置操作tab，点击右侧模板按钮，确认能插入对应的函数代码
5. [ ] 测试后置操作tab，同上
6. [ ] 在Body tab中选择"Form-Data"，确认能看到文件上传表单
7. [ ] 选择已上传的文件，执行调试
8. [ ] 查看返回结果的各个tab，确认信息正确且结构化显示
9. [ ] 查看"日志信息"tab，确认有日志输出且不同级别颜色不同
10. [ ] 在测试用例tab中同样测试变量文件选择功能

### 边界情况测试
- [ ] 不选择变量文件就点击调试（应提示用户选择）
- [ ] 变量文件列表为空时（显示"暂无变量文件"禁用项）
- [ ] 调试过程中取消操作（AbortController）
- [ ] 后端返回错误时的前端处理
- [ ] 大型响应体的性能表现

---

## 后续优化建议

1. **自动刷新变量文件列表**: 当用户在另一个标签页创建了新变量文件，当前页面应该能感知变化
2. **文件上传功能**: 目前只能选择已上传的文件，可以考虑支持直接上传新文件
3. **调试历史记录**: 可以将每次调试的结果保存下来，方便回溯对比
4. **批量调试**: 支持同时调试多个接口或用例
5. **Mock数据**: 在没有真实后端的情况下提供Mock数据用于前端开发测试

---

## 修改文件清单

### 前端文件
1. `frontend/src/views/cases/ApiTestWorkspaceView.vue` - 主要修改文件

### 后端文件
1. `service/api_test/shared/runner_gateway.py` - 执行逻辑增强
2. `service/api_test/debug/debug_api.py` - 返回值增强

---

**修改日期**: 2026-06-11  
**修改人**: AI Assistant  
**版本**: v1.0
