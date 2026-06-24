# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: test-management\test-suites.spec.js >> 测试套件管理 >> 应该能搜索套件
- Location: e2e\test-management\test-suites.spec.js:116:3

# Error details

```
TimeoutError: locator.fill: Timeout 15000ms exceeded.
Call log:
  - waiting for locator('input[placeholder*="搜索"]').first()

```

# Page snapshot

```yaml
- generic [ref=e3]:
  - complementary [ref=e4]:
    - link "巧乐AI智能体测试平台" [ref=e6] [cursor=pointer]:
      - /url: /agent
      - generic [ref=e7]: 巧乐AI智能体测试平台
    - navigation [ref=e8]:
      - menubar [ref=e9]:
        - menuitem "智能体中心" [ref=e10] [cursor=pointer]:
          - img [ref=e12]
          - generic [ref=e15]: 智能体中心
        - menuitem "用例管理" [ref=e16]:
          - generic [ref=e17] [cursor=pointer]:
            - img [ref=e19]
            - generic [ref=e21]: 用例管理
            - img [ref=e23]
        - menuitem "测试管理" [expanded] [ref=e25]:
          - generic [ref=e26] [cursor=pointer]:
            - img [ref=e28]
            - generic [ref=e30]: 测试管理
            - img [ref=e32]
          - menu [ref=e34]:
            - menuitem "测试套件" [ref=e35] [cursor=pointer]
            - menuitem "测试任务" [ref=e36] [cursor=pointer]
            - menuitem "测试缺陷" [ref=e37] [cursor=pointer]
        - menuitem "文档库管理" [ref=e38]:
          - generic [ref=e39] [cursor=pointer]:
            - img [ref=e41]
            - generic [ref=e43]: 文档库管理
            - img [ref=e45]
        - menuitem "环境数据管理" [ref=e47]:
          - generic [ref=e48] [cursor=pointer]:
            - img [ref=e50]
            - generic [ref=e52]: 环境数据管理
            - img [ref=e54]
        - menuitem "项目管理" [ref=e56] [cursor=pointer]:
          - img [ref=e58]
          - generic [ref=e62]: 项目管理
        - menuitem "用户管理 SA" [ref=e63] [cursor=pointer]:
          - img [ref=e65]
          - generic [ref=e67]: 用户管理
          - generic [ref=e69]: SA
    - generic [ref=e70]:
      - button "admin" [ref=e72] [cursor=pointer]:
        - img [ref=e74]
        - generic [ref=e75]: admin
      - button "中文" [ref=e77] [cursor=pointer]:
        - generic [ref=e78]: 中文
  - main [ref=e80]:
    - generic [ref=e81]:
      - generic [ref=e83]:
        - generic [ref=e86]:
          - generic [ref=e87]:
            - combobox [active] [ref=e89]
            - generic [ref=e90]: KnowSmoke_1780558346
          - img [ref=e93] [cursor=pointer]
        - generic [ref=e95]: 测试套件
      - generic [ref=e97]:
        - button "新建" [ref=e99] [cursor=pointer]:
          - generic [ref=e100]: 新建
        - generic [ref=e101]:
          - textbox "关键词" [ref=e104]
          - generic [ref=e107] [cursor=pointer]:
            - generic:
              - combobox [ref=e109]
              - generic [ref=e110]: 执行状态
            - img [ref=e113]
        - generic [ref=e115]:
          - button "搜索" [ref=e116] [cursor=pointer]:
            - generic [ref=e117]: 搜索
          - button "重置" [ref=e118] [cursor=pointer]:
            - generic [ref=e119]: 重置
      - generic [ref=e122]:
        - table [ref=e124]:
          - rowgroup [ref=e135]:
            - row "选择所有行 套件名称 套件类型 用例数 执行状态 成功率 执行人 最近执行 操作" [ref=e136]:
              - columnheader "选择所有行" [ref=e137]:
                - generic "选择所有行" [ref=e139]:
                  - generic [ref=e140] [cursor=pointer]:
                    - checkbox "选择所有行" [disabled]
              - columnheader "套件名称" [ref=e142]:
                - generic [ref=e143]: 套件名称
              - columnheader "套件类型" [ref=e144]:
                - generic [ref=e145]: 套件类型
              - columnheader "用例数" [ref=e146]:
                - generic [ref=e147]: 用例数
              - columnheader "执行状态" [ref=e148]:
                - generic [ref=e149]: 执行状态
              - columnheader "成功率" [ref=e150]:
                - generic [ref=e151]: 成功率
              - columnheader "执行人" [ref=e152]:
                - generic [ref=e153]: 执行人
              - columnheader "最近执行" [ref=e154]:
                - generic [ref=e155]: 最近执行
              - columnheader "操作" [ref=e156]:
                - generic [ref=e157]: 操作
        - generic [ref=e161]:
          - table:
            - rowgroup
          - generic [ref=e163]: 暂无数据
```

# Test source

```ts
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
> 121 |     await searchInput.fill('测试');
      |                       ^ TimeoutError: locator.fill: Timeout 15000ms exceeded.
  122 | 
  123 |     // 点击搜索或按回车
  124 |     await searchInput.press('Enter');
  125 |     await waitForTableLoad(page);
  126 | 
  127 |     // 清空搜索
  128 |     await searchInput.clear();
  129 |     await searchInput.press('Enter');
  130 |     await waitForTableLoad(page);
  131 |   });
  132 | });
  133 | 
```