# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: test-management\defects.spec.js >> 缺陷管理 >> 应该能查看缺陷列表
- Location: e2e\test-management\defects.spec.js:11:3

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: locator('th:has-text("缺陷标题")')
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" with timeout 5000ms
  - waiting for locator('th:has-text("缺陷标题")')

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
  - text: 缺陷管理
  - button "新建"
  - textbox "搜索缺陷标题"
  - textbox "ID"
  - combobox
  - text: 状态
  - img
  - combobox
  - text: 严重程度
  - img
  - combobox
  - text: 优先级
  - img
  - combobox
  - text: 缺陷类型
  - img
  - img
  - combobox "提交时间"
  - text: "-"
  - combobox "提交时间"
  - button "搜索"
  - button "重置"
  - table:
    - rowgroup:
      - row "选择所有行 ID 缺陷管理 严重程度 优先级 状态 缺陷类型 处理人 提交人 提交时间 操作":
        - columnheader "选择所有行":
          - checkbox "选择所有行" [disabled]
        - columnheader "ID"
        - columnheader "缺陷管理"
        - columnheader "严重程度"
        - columnheader "优先级"
        - columnheader "状态"
        - columnheader "缺陷类型"
        - columnheader "处理人"
        - columnheader "提交人"
        - columnheader "提交时间"
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
  4   | test.describe('缺陷管理', () => {
  5   |   test.beforeEach(async ({ page }) => {
  6   |     await login(page);
  7   |     await navigateTo(page, ['测试管理', '测试缺陷']);
  8   |     await selectProject(page);
  9   |   });
  10  | 
  11  |   test('应该能查看缺陷列表', async ({ page }) => {
  12  |     await waitForTableLoad(page);
  13  | 
  14  |     const table = page.locator('.el-table');
  15  |     await expect(table).toBeVisible();
  16  | 
  17  |     // 验证表头
> 18  |     await expect(page.locator('th:has-text("缺陷标题")')).toBeVisible();
      |                                                       ^ Error: expect(locator).toBeVisible() failed
  19  |     await expect(page.locator('th:has-text("严重程度")')).toBeVisible();
  20  |     await expect(page.locator('th:has-text("优先级")')).toBeVisible();
  21  |     await expect(page.locator('th:has-text("状态")')).toBeVisible();
  22  |   });
  23  | 
  24  |   test('应该能创建新缺陷', async ({ page }) => {
  25  |     await clickButton(page, '新建缺陷');
  26  | 
  27  |     const dialog = page.locator('.el-dialog');
  28  |     await expect(dialog).toBeVisible();
  29  | 
  30  |     // 填写表单
  31  |     await fillFormField(page, '缺陷标题', `自动化缺陷_${Date.now()}`);
  32  | 
  33  |     // 选择缺陷类型
  34  |     await selectFormOption(page, '缺陷类型', '功能');
  35  | 
  36  |     // 选择严重程度
  37  |     await selectFormOption(page, '严重程度', '一般');
  38  | 
  39  |     // 选择优先级
  40  |     await selectFormOption(page, '优先级', '中');
  41  | 
  42  |     // 填写缺陷步骤
  43  |     const stepsInput = dialog.locator('textarea').first();
  44  |     if (await stepsInput.isVisible()) {
  45  |       await stepsInput.fill('1. 打开系统\n2. 执行操作\n3. 观察到错误');
  46  |     }
  47  | 
  48  |     // 填写缺陷原因
  49  |     const causeInput = dialog.locator('textarea').nth(1);
  50  |     if (await causeInput.isVisible()) {
  51  |       await causeInput.fill('自动化测试发现的缺陷原因');
  52  |     }
  53  | 
  54  |     // 保存
  55  |     await clickButton(page, '确定');
  56  |     await waitForSuccessMessage(page);
  57  |     await waitForTableLoad(page);
  58  |   });
  59  | 
  60  |   test('应该能查看缺陷详情', async ({ page }) => {
  61  |     await waitForTableLoad(page);
  62  | 
  63  |     const viewButton = page.locator('.el-table__body-wrapper button:has-text("查看")').first();
  64  |     if (await viewButton.isVisible()) {
  65  |       await viewButton.click();
  66  |       await page.waitForLoadState('networkidle');
  67  | 
  68  |       // 验证详情页
  69  |       await expect(page.locator('.defect-detail-view')).toBeVisible();
  70  | 
  71  |       // 验证基本信息区域
  72  |       await expect(page.locator('text=基本信息')).toBeVisible();
  73  | 
  74  |       // 验证状态流转按钮
  75  |       await expect(page.locator('button:has-text("处理缺陷")')).toBeVisible();
  76  |     }
  77  |   });
  78  | 
  79  |   test('应该能编辑缺陷', async ({ page }) => {
  80  |     await waitForTableLoad(page);
  81  | 
  82  |     const viewButton = page.locator('.el-table__body-wrapper button:has-text("查看")').first();
  83  |     if (await viewButton.isVisible()) {
  84  |       await viewButton.click();
  85  |       await page.waitForLoadState('networkidle');
  86  | 
  87  |       // 点击编辑按钮
  88  |       await clickButton(page, '编辑');
  89  | 
  90  |       const editSection = page.locator('text=编辑缺陷');
  91  |       await expect(editSection).toBeVisible();
  92  | 
  93  |       // 修改标题
  94  |       const titleInput = page.locator('.el-form-item:has(label:has-text("缺陷标题")) input');
  95  |       if (await titleInput.isVisible()) {
  96  |         await titleInput.fill('已修改的缺陷标题_' + Date.now());
  97  |       }
  98  | 
  99  |       // 点击保存
  100 |       const saveButton = page.locator('button:has-text("保存")');
  101 |       await saveButton.click();
  102 |       await waitForSuccessMessage(page);
  103 |     }
  104 |   });
  105 | 
  106 |   test('应该能处理缺陷状态流转', async ({ page }) => {
  107 |     await waitForTableLoad(page);
  108 | 
  109 |     const viewButton = page.locator('.el-table__body-wrapper button:has-text("查看")').first();
  110 |     if (await viewButton.isVisible()) {
  111 |       await viewButton.click();
  112 |       await page.waitForLoadState('networkidle');
  113 | 
  114 |       // 点击处理缺陷按钮
  115 |       await clickButton(page, '处理缺陷');
  116 | 
  117 |       const dialog = page.locator('.el-dialog');
  118 |       await expect(dialog).toBeVisible();
```