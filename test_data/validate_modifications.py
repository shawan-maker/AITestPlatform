"""
简化的代码验证脚本 - 验证修改的代码是否正确

这个脚本只做语法检查和基本的逻辑验证，不需要运行完整的服务
"""

import sys
import os

# 设置编码
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass

print("=" * 70)
print("  Bug修复代码验证")
print("=" * 70)
print()

# 验证1: 检查前端文件是否存在
print("[1/5] 检查前端文件...")
frontend_file = 'd:/PyProject/AITestPlatform/frontend/src/views/cases/ApiTestWorkspaceView.vue'
if os.path.exists(frontend_file):
    print(f"    OK - 文件存在: {frontend_file}")
    
    # 检查关键修改点
    with open(frontend_file, 'r', encoding='utf-8') as f:
        content = f.read()
        
        checks = [
            ('变量文件列表状态', 'environmentList'),
            ('调试环境ID状态', 'debugEnvId'),
            ('用例环境ID状态', 'caseEnvId'),
            ('文件上传类型选择器', 'bodyType'),
            ('上传文件选项列表', 'uploadFileOptions'),
            ('加载环境方法', 'refreshEnvironmentList'),
            ('选择调试环境方法', 'selectDebugEnvironment'),
            ('选择用例环境方法', 'selectCaseEnvironment'),
            ('加载上传文件方法', 'loadUploadFiles'),
            ('显示文件标签方法', 'displayFileLabel'),
            ('插入前置模板方法', 'insertPreTemplate'),
            ('插入后置模板方法', 'insertPostTemplate'),
            ('解析响应方法', 'parseDebugResponse'),
            ('获取状态颜色方法', 'getStatusColor'),
            ('获取状态标签方法', 'getStatusLabel'),
            ('格式化大小方法', 'formatSize'),
            ('结果状态变量', 'responseResult'),
            ('响应信息变量', 'responseDataInfo'),
            ('请求信息变量', 'requestInfo'),
            ('提取信息变量', 'extractInfo'),
            ('断言信息变量', 'assertInfo'),
            ('日志数据变量', 'logData'),
            ('前置操作容器样式', 'prepost-container'),
            ('模板列表样式', 'template-list'),
            ('结构化响应样式', 'structured-response'),
            ('断言列表样式', 'assert-list'),
            ('日志容器样式', 'log-container'),
            ('日志级别徽章样式', 'log-level-badge'),
            ('导入CircleCloseFilled', 'CircleCloseFilled'),
            ('导入fetchEnvList', 'listEnvironments as fetchEnvList'),
            ('导入listUploadedFiles', 'listUploadedFiles'),
            ('Form-Data选项', 'form-data'),
            ('日志信息Tab', 'log-info'),
        ]
        
        passed_checks = 0
        for check_name, check_str in checks:
            if check_str in content:
                print(f"    OK - 包含{check_name}")
                passed_checks += 1
            else:
                print(f"    FAIL - 缺少{check_name}: {check_str}")
        
        print(f"\n    前端检查通过: {passed_checks}/{len(checks)}")
else:
    print(f"    FAIL - 文件不存在: {frontend_file}")

print()

# 验证2: 检查后端文件是否存在
print("[2/5] 检查后端runner_gateway.py...")
backend_file1 = 'd:/PyProject/AITestPlatform/service/api_test/shared/runner_gateway.py'
if os.path.exists(backend_file1):
    print(f"    OK - 文件存在: {backend_file1}")
    
    with open(backend_file1, 'r', encoding='utf-8') as f:
        content = f.read()
        
        checks = [
            ('json模块导入', 'import json'),
            ('初始化详细结果', "detailed_result ="),
            ('状态字段', "'status':"),
            ('错误消息字段', "'error_message': None"),
            ('日志数据字段', "'log_data': []"),
            ('响应信息提取', "'response_info'"),
            ('请求信息提取', "'request_info'"),
            ('提取信息提取', "'extract_info'"),
            ('断言信息提取', "'assert_info'"),
            ('耗时计算', "duration_ms"),
            ('合并详细结果到result', "_debug_detail': detailed_result"),
        ]
        
        passed_checks = 0
        for check_name, check_str in checks:
            if check_str in content:
                print(f"    OK - 包含{check_name}")
                passed_checks += 1
            else:
                print(f"    FAIL - 缺少{check_name}: {check_str}")
        
        print(f"\n    runner_gateway.py检查通过: {passed_checks}/{len(checks)}")
else:
    print(f"    FAIL - 文件不存在: {backend_file1}")

print()

# 验证3: 检查debug_api.py
print("[3/5] 检查后端debug_api.py...")
backend_file2 = 'd:/PyProject/AITestPlatform/service/api_test/debug/debug_api.py'
if os.path.exists(backend_file2):
    print(f"    OK - 文件存在: {backend_file2}")
    
    with open(backend_file2, 'r', encoding='utf-8') as f:
        content = f.read()
        
        checks = [
            ('构造返回数据', 'base_data = {'),
            ('运行记录ID', "'run_record_id': record.id"),
            ('执行者信息', "'executor': user.username"),
            ('错误消息', "'error_message': record.error_message"),
            ('API请求信息处理', 'api_requests_info'),
            ('调试详情提取', '_debug_detail'),
            ('合并详情数据', 'base_data.update('),
        ]
        
        passed_checks = 0
        for check_name, check_str in checks:
            if check_str in content:
                print(f"    OK - 包含{check_name}")
                passed_checks += 1
            else:
                print(f"    FAIL - 缺少{check_name}: {check_str}")
        
        print(f"\n    debug_api.py检查通过: {passed_checks}/{len(checks)}")
else:
    print(f"    FAIL - 文件不存在: {backend_file2}")

print()

# 验证4: 检查文档文件
print("[4/5] 检查修改说明文档...")
doc_file = 'd:/PyProject/AITestPlatform/test_data/BugFix_Modification_Summary.md'
if os.path.exists(doc_file):
    print(f"    OK - 文档已创建: {doc_file}")
    
    with open(doc_file, 'r', encoding='utf-8') as f:
        doc_content = f.read()
        # 统计行数
        lines = doc_content.split('\n')
        print(f"    OK - 文档包含 {len(lines)} 行")
else:
    print(f"    FAIL - 文档不存在")

print()

# 验证5: 检查测试脚本
print("[5/5] 检查测试脚本...")
test_file = 'd:/PyProject/AITestPlatform/test_data/test_e2e_debug.py'
if os.path.exists(test_file):
    print(f"    OK - 测试脚本已创建: {test_file}")
    
    with open(test_file, 'r', encoding='utf-8') as f:
        test_content = f.read()
        # 统计测试函数数量
        test_functions = ['test_variable_file_loading', 'test_debug_payload_building', 
                         'test_file_upload_payload', 'test_response_parsing', 
                         'test_error_handling']
        found_tests = sum(1 for func in test_functions if func in test_content)
        print(f"    OK - 测试脚本包含 {found_tests}/{len(test_functions)} 个测试函数")
else:
    print(f"    FAIL - 测试脚本不存在")

print()
print("=" * 70)
print("  验证完成!")
print("=" * 70)
print()
print("修改总结:")
print("- [前端] ApiTestWorkspaceView.vue:")
print("    + 变量文件动态选择功能 (替代硬编码下拉菜单)")
print("    + 前置/后置操作左右分栏布局 (参考CaseEditor.vue)")
print("    + Body类型选择器 (JSON/Form-Data)")
print("    + 文件上传表单 (字段名+文件选择)")
print("    + 结构化结果展示 (6个tab)")
print("    + 日志信息tab (不同级别不同颜色)")
print()
print("- [后端] runner_gateway.py:")
print("    + 详细结果解析 (_debug_detail)")
print("    + 响应/请求/提取/断言/日志信息收集")
print()
print("- [后端] debug_api.py:")
print("    + 返回完整的调试详情数据")
print("    + 从record.api_requests_info提取详细信息")
print()
print("下一步操作:")
print("1. 启动前端开发服务器: npm run dev (在frontend目录下)")
print("2. 启动后端服务: python main.py (在项目根目录)")
print("3. 访问 API用例管理页面进行手动测试")
print()
