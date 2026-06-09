# 编码规范与调试流程

## 规则概述
本规则定义了代码修改、调试和测试的标准流程，确保代码质量并减少反复修改。

## 规则 1：代码修改与调试规范

### 适用场景
- 修改任何前端或后端代码
- 修复 bug 或添加新功能
- 重构现有代码

### 执行步骤

#### 1.1 代码修改原则
- **确定性问题**：直接修复 + 添加调试日志
- **不确定性问题**：先添加详细调试日志，等待复现，**禁止盲目修改代码**

#### 1.2 调试日志规范
修改代码时，必须在关键位置添加调试日志：
- **前端（JavaScript/Vue）**：使用 `console.log('[DEBUG] 函数名: ', 变量)`
- **后端（Python）**：使用 `print('[DEBUG] 函数名: ', 变量)` 或 `logger.debug()`

示例：
```javascript
// 前端示例
function flattenCatalogs(tree, parentPath = '') {
  console.log('[DEBUG] flattenCatalogs 开始, parentPath:', parentPath, 'tree长度:', tree?.length)
  // ... 函数逻辑
  console.log('[DEBUG] flattenCatalogs 完成, 结果数量:', result.length)
  return result
}
```

```python
# 后端示例
def save_test_case(case_data):
    print('[DEBUG] save_test_case 开始, case_data:', case_data)
    # ... 函数逻辑
    print('[DEBUG] save_test_case 完成, result:', result)
    return result
```

#### 1.3 修改后基础校验（**强制必须执行**）
修改代码后，**必须立即执行**以下校验，确保没有基础错误：

##### 前端校验
```powershell
# 在 frontend 目录下执行
cd d:/PyProject/AITestPlatform/frontend
npx vite build --mode development
```
- ✅ **通过标准**：exitCode = 0，无编译错误
- ❌ **失败处理**：如果有编译错误，立即修复，**不允许继续后续步骤**

##### 后端校验
```powershell
# 在项目根目录下执行
cd d:/PyProject/AITestPlatform
python -c "import py_compile; import os; [py_compile.compile(os.path.join(r, f)) for r,d,fs in os.walk('service') for f in fs if f.endswith('.py')]"
```
- ✅ **通过标准**：exitCode = 0，无语法错误
- ❌ **失败处理**：如果有语法错误，立即修复，**不允许继续后续步骤**

#### 1.4 校验失败处理流程
```
修改代码 → 执行前端校验 → 执行后端校验
    ↓
如果有错误 → 修复错误 → 重新执行校验 → 直到校验通过
    ↓
校验通过 → 继续后续步骤（重启服务、测试等）
```

### 验证标准
- [ ] 代码修改处已添加调试日志
- [ ] 前端编译检查通过（exitCode = 0）
- [ ] 后端语法检查通过（exitCode = 0）
- [ ] 无盲目修改代码的行为

---

## 规则 2：自动重启服务与测试调试

### 适用场景
- 修改代码后需要测试
- 需要调试前后端交互
- 需要验证修复效果

### 执行步骤

#### 2.1 自动重启前端服务
```powershell
# 停止现有前端服务
cd d:/PyProject/AITestPlatform/frontend
Stop-Process -Name "node" -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

# 清理 Vite 缓存（可选，如果遇到缓存问题）
Remove-Item -Recurse -Force node_modules/.vite -ErrorAction SilentlyContinue

# 启动前端服务
npm run dev
```

#### 2.2 自动重启后端服务
```powershell
# 停止现有后端服务
cd d:/PyProject/AITestPlatform
Stop-Process -Name "python" -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

# 启动后端服务（后台运行）
Start-Process -NoNewWindow python -ArgumentList "main.py"
```

#### 2.3 编写测试脚本进行调试
根据需要编写测试脚本：
- **前端测试**：使用 `agent-browser` 或手动测试
- **后端测试**：编写 Python 测试脚本，调用 API 接口
- **端到端测试**：编写完整的测试流程脚本

#### 2.4 根据调试日志定位问题
- 查看前端浏览器控制台（F12）的 `[DEBUG]` 日志
- 查看后端服务输出的 `[DEBUG]` 日志
- 根据日志信息定位问题根源，**不要盲目猜测**

#### 2.5 项目登录账号
- **账号**：test1213
- **密码**：123456

### 验证标准
- [ ] 前端服务已重启并正常运行（http://localhost:5173）
- [ ] 后端服务已重启并正常运行（http://localhost:8000）
- [ ] 已编写测试脚本或使用工具进行调试
- [ ] 已根据调试日志定位问题

---

## 规则 3：端到端测试验证

### 适用场景
- 代码修改完成后
- 修复 bug 后
- 添加新功能后

### 执行步骤

#### 3.1 测试范围确定
- 明确本次修改涉及的代码逻辑
- 确定需要测试的功能点
- 识别可能的边界情况

#### 3.2 测试用例设计
设计测试用例，覆盖以下情况：
- **正常情况**：标准输入，预期输出
- **边界情况**：空输入、最大值、最小值等
- **异常情况**：错误输入、网络错误、服务异常等
- **交互情况**：用户操作流程、前后端交互流程

#### 3.3 执行端到端测试
按照以下步骤执行测试：
1. 登录系统（账号：test1213 / 密码：123456）
2. 按照测试用例执行操作
3. 观察前端界面变化
4. 查看前端控制台日志
5. 查看后端服务日志
6. 记录测试结果

#### 3.4 测试不通过处理
如果测试不通过：
1. 根据调试日志定位问题
2. 修复问题
3. 重新执行规则 1 的基础校验
4. 重新执行规则 2 的重启服务
5. 重新执行测试
6. 重复以上步骤，**直到测试通过**

### 验证标准
- [ ] 已设计完整的测试用例（覆盖正常、边界、异常情况）
- [ ] 已执行所有测试用例
- [ ] 所有测试用例通过
- [ ] 代码逻辑正确，无遗漏情况

---

## 规则执行流程图

```
开始代码修改
    ↓
添加调试日志（确定性：直接修复+日志；不确定性：仅添加日志）
    ↓
执行前端校验（npx vite build --mode development）
    ↓
执行后端校验（python -c "..." 语法检查）
    ↓
校验通过？
    ↓ 是
自动重启前后端服务
    ↓
编写测试脚本 / 使用工具调试
    ↓
根据调试日志定位问题
    ↓
执行端到端测试（覆盖各种情况）
    ↓
测试通过？
    ↓ 否 → 修复问题 → 重新执行校验 → 重新测试
    ↓ 是
清理调试脚本
    ↓
任务完成
```

---

## 规则 4：调试脚本清理规范

### 适用场景
- 编写了临时调试脚本用于自验证
- 测试完成后，调试脚本不再需要
- 避免调试脚本污染项目目录

### 执行步骤

#### 4.1 调试脚本识别
以下文件属于调试脚本，调试结束后必须删除：
- 临时测试脚本（如 `test_*.py`, `test_*.js`）
- 临时调试页面（如 `debug_*.html`, `debug_*.vue`）
- 临时配置文件（如 `debug_*.json`, `debug_*.yaml`）
- 临时日志文件（如 `debug_*.log`）

#### 4.2 清理时机
**必须在以下时机清理调试脚本**：
1. **调试结束后立即清理**：确认问题已修复，测试通过后
2. **提交代码前清理**：确保没有调试脚本被提交到版本库
3. **切换任务前清理**：开始新的任务前，清理上一个任务的调试脚本

#### 4.3 清理方法
```powershell
# 清理前端调试脚本
cd d:/PyProject/AITestPlatform/frontend
Remove-Item -Force debug_*, test_debug* -ErrorAction SilentlyContinue

# 清理后端调试脚本
cd d:/PyProject/AITestPlatform
Remove-Item -Force debug_*, test_debug*, temp_*.py -ErrorAction SilentlyContinue

# 清理临时日志
Remove-Item -Force debug_*.log, temp_*.log -ErrorAction SilentlyContinue
```

#### 4.4 验证清理结果
```powershell
# 验证项目目录中没有遗留调试脚本
Get-ChildItem -Path "d:/PyProject/AITestPlatform" -Recurse -Include "debug_*", "test_debug*", "temp_*" -ErrorAction SilentlyContinue
```

### 验证标准
- [ ] 项目目录中没有 `debug_*` 文件
- [ ] 项目目录中没有 `test_debug*` 文件
- [ ] 项目目录中没有 `temp_*` 文件
- [ ] 没有将调试脚本提交到 Git 版本库

---

## 禁止行为

1. **禁止盲目修改代码**：不确定性问题时，必须先添加调试日志，等待复现
2. **禁止跳过基础校验**：修改代码后必须执行前端编译检查和后端语法检查
3. **禁止反复盲目修改**：一个问题修改多次仍不成功时，必须停下来分析调试日志
4. **禁止没有测试用例就宣布完成任务**：必须执行端到端测试，覆盖各种情况
5. **禁止遗留调试脚本**：自验证过程中产生的临时调试脚本，调试结束后必须删除，不得留在项目目录中

---

## 示例：完整执行流程

### 场景：修复前端目录显示错误

1. **代码修改**：
   - 分析：不确定具体原因
   - 行动：添加详细调试日志到 `flattenCatalogs` 函数
   - 代码：
     ```javascript
     function flattenCatalogs(tree, parentPath = '') {
       console.log('[DEBUG] flattenCatalogs 开始, parentPath:', parentPath, 'tree长度:', tree?.length)
       // ... 原有逻辑
       console.log('[DEBUG] flattenCatalogs 完成, 结果数量:', result.length)
       return result
     }
     ```

2. **基础校验**：
   ```powershell
   cd d:/PyProject/AITestPlatform/frontend
   npx vite build --mode development
   ```
   - 结果：exitCode = 0，通过

   ```powershell
   cd d:/PyProject/AITestPlatform
   python -c "..."  # 后端语法检查
   ```
   - 结果：exitCode = 0，通过

3. **重启服务**：
   ```powershell
   # 重启前端
   cd d:/PyProject/AITestPlatform/frontend
   Stop-Process -Name "node" -Force
   npm run dev
   
   # 重启后端
   cd d:/PyProject/AITestPlatform
   Stop-Process -Name "python" -Force
   Start-Process -NoNewWindow python -ArgumentList "main.py"
   ```

4. **测试调试**：
   - 打开浏览器访问 http://localhost:5173
   - 登录（test1213 / 123456）
   - 操作触发目录显示功能
   - 查看浏览器控制台 `[DEBUG]` 日志
   - 查看后端服务日志
   - 定位问题根源

5. **端到端测试**：
   - 设计测试用例（正常目录、多级目录、空目录等）
   - 执行所有测试用例
   - 验证目录显示正确
   - 测试通过，任务完成

---

## 总结

本规则确保：
1. **代码修改有依据**：不确定性问题先加日志，不盲目修改
2. **基础错误提前发现**：修改后立即执行编译和语法检查
3. **调试有方法**：根据调试日志定位问题，不盲目猜测
4. **测试全覆盖**：端到端测试覆盖各种情况，确保质量
5. **调试脚本及时清理**：自验证过程中产生的调试脚本，调试结束后必须删除，不得留在项目目录中

**记住：质量优于速度，调试优于猜测。**