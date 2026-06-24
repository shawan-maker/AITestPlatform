# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: test-management\test-suites.spec.js >> 测试套件管理 >> 应该能查看套件列表
- Location: e2e\test-management\test-suites.spec.js:11:3

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: locator('th:has-text("用例数量")')
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" with timeout 5000ms
  - waiting for locator('th:has-text("用例数量")')

```

```yaml
- complementary:
  - link "巧乐AI智能体测试平台":
    - /url: /agent
  - navigation:
    - menubar:
      - menuitem "智能体中心":
        - img
        - text: 智能体中心
      - menuitem "用例管理":
        - img
        - text: 用例管理
        - img
      - menuitem "测试管理" [expanded]:
        - img
        - text: 测试管理
        - img
        - menu:
          - menuitem "测试套件"
          - menuitem "测试任务"
          - menuitem "测试缺陷"
      - menuitem "文档库管理":
        - img
        - text: 文档库管理
        - img
      - menuitem "环境数据管理":
        - img
        - text: 环境数据管理
        - img
      - menuitem "项目管理":
        - img
        - text: 项目管理
      - menuitem "用户管理 SA":
        - img
        - text: 用户管理 SA
  - button "admin":
    - img
    - text: admin
  - button "中文"
- main:
  - combobox
  - text: KnowSmoke_1780558346
  - img
  - text: 测试套件
  - button "新建"
  - textbox "关键词"
  - combobox
  - text: 执行状态
  - img
  - button "搜索"
  - button "重置"
  - table:
    - rowgroup:
      - row "选择所有行 套件名称 套件类型 用例数 执行状态 成功率 执行人 最近执行 操作":
        - columnheader "选择所有行":
          - checkbox "选择所有行" [disabled]
        - columnheader "套件名称"
        - columnheader "套件类型"
        - columnheader "用例数"
        - columnheader "执行状态"
        - columnheader "成功率"
        - columnheader "执行人"
        - columnheader "最近执行"
        - columnheader "操作"
  - table:
    - rowgroup
  - text: 暂无数据
```

# Test source

```ts
  1   | import { test, expect } from '@playwright/test';
  2   | import { login, navigateTo, selectProject, waitForTableLoad, fillFormField, selectFormOption, clickButton, waitForSuccessMessage, closeDialog } from '../test-utils.js';
  3   | 
  4   | test.describe('测试套件管理', () => {
  5   |   test.beforeEach(async ({ page }) => {
  6   |     await login(page);
  7   |     await navigateTo(page, ['测试管理', '测试套件']);
  8   |     await selectProject(page);
  9   |   });
  10  | 
  11  |   test('应该能查看套件列表', async ({ page }) => {
  12  |     await waitForTableLoad(page);
  13  | 
  14  |     // 验证表格存在
  15  |     const table = page.locator('.el-table');
  16  |     await expect(table).toBeVisible();
  17  | 
  18  |     // 验证表头
  19  |     await expect(page.locator('th:has-text("套件名称")')).toBeVisible();
> 20  |     await expect(page.locator('th:has-text("用例数量")')).toBeVisible();
      |                                                       ^ Error: expect(locator).toBeVisible() failed
  21  |     await expect(page.locator('th:has-text("执行状态")')).toBeVisible();
  22  |   });
  23  | 
  24  |   test('应该能创建新套件', async ({ page }) => {
  25  |     await clickButton(page, '新建套件');
  26  | 
  27  |     // 等待对话框出现
  28  |     const dialog = page.locator('.el-dialog');
  29  |     await expect(dialog).toBeVisible();
  30  | 
  31  |     // 填写表单
  32  |     await fillFormField(page, '套件名称', `自动化测试套件_${Date.now()}`);
  33  |     await fillFormField(page, '描述', '这是自动化测试创建的套件');
  34  | 
  35  |     // 选择环境（如果有）
  36  |     const envSelect = page.locator('.el-form-item:has(label:has-text("环境")) .el-select');
  37  |     if (await envSelect.isVisible()) {
  38  |       await envSelect.click();
  39  |       await page.click('.el-select-dropdown__item').first();
  40  |     }
  41  | 
  42  |     // 保存
  43  |     await clickButton(page, '确定');
  44  |     await waitForSuccessMessage(page);
  45  | 
  46  |     // 验证套件出现在列表中
  47  |     await waitForTableLoad(page);
  48  |   });
  49  | 
  50  |   test('应该能查看套件详情', async ({ page }) => {
  51  |     await waitForTableLoad(page);
  52  | 
  53  |     // 点击第一行的查看按钮
  54  |     const viewButton = page.locator('.el-table__body-wrapper button:has-text("查看")').first();
  55  |     if (await viewButton.isVisible()) {
  56  |       await viewButton.click();
  57  |       await page.waitForLoadState('networkidle');
  58  | 
  59  |       // 验证详情页
  60  |       await expect(page.locator('.suite-detail-view')).toBeVisible();
  61  | 
  62  |       // 验证基本信息标签页
  63  |       await expect(page.locator('.el-tabs__item:has-text("基本信息")')).toBeVisible();
  64  | 
  65  |       // 验证用例列表标签页
  66  |       await expect(page.locator('.el-tabs__item:has-text("用例列表")')).toBeVisible();
  67  | 
  68  |       // 切换到用例列表
  69  |       await page.click('.el-tabs__item:has-text("用例列表")');
  70  |       await waitForTableLoad(page);
  71  |     }
  72  |   });
  73  | 
  74  |   test('应该能编辑套件', async ({ page }) => {
  75  |     await waitForTableLoad(page);
  76  | 
  77  |     // 进入详情页
  78  |     const viewButton = page.locator('.el-table__body-wrapper button:has-text("查看")').first();
  79  |     if (await viewButton.isVisible()) {
  80  |       await viewButton.click();
  81  |       await page.waitForLoadState('networkidle');
  82  | 
  83  |       // 点击编辑按钮
  84  |       await clickButton(page, '编辑');
  85  | 
  86  |       const dialog = page.locator('.el-dialog');
  87  |       await expect(dialog).toBeVisible();
  88  | 
  89  |       // 修改描述
  90  |       const descInput = dialog.locator('textarea').first();
  91  |       if (await descInput.isVisible()) {
  92  |         await descInput.fill('已修改的描述_' + Date.now());
  93  |       }
  94  | 
  95  |       // 保存
  96  |       await clickButton(page, '确定');
  97  |       await waitForSuccessMessage(page);
  98  |     }
  99  |   });
  100 | 
  101 |   test('应该能删除套件', async ({ page }) => {
  102 |     await waitForTableLoad(page);
  103 | 
  104 |     // 点击删除按钮
  105 |     const deleteButton = page.locator('.el-table__body-wrapper button:has-text("删除")').first();
  106 |     if (await deleteButton.isVisible()) {
  107 |       await deleteButton.click();
  108 | 
  109 |       // 确认删除
  110 |       await page.click('.el-message-box__btns button:has-text("确定")');
  111 |       await waitForSuccessMessage(page);
  112 |       await waitForTableLoad(page);
  113 |     }
  114 |   });
  115 | 
  116 |   test('应该能搜索套件', async ({ page }) => {
  117 |     await waitForTableLoad(page);
  118 | 
  119 |     // 在搜索框输入
  120 |     const searchInput = page.locator('input[placeholder*="搜索"]').first();
```