# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: test-management\test-tasks.spec.js >> 测试任务管理 >> 应该能搜索任务
- Location: e2e\test-management\test-tasks.spec.js:157:3

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
        - generic [ref=e95]: 测试任务
      - generic [ref=e97]:
        - button "新建" [ref=e99] [cursor=pointer]:
          - generic [ref=e100]: 新建
        - generic [ref=e101]:
          - textbox "关键词" [ref=e104]
          - generic [ref=e107] [cursor=pointer]:
            - generic:
              - combobox [ref=e109]
              - generic [ref=e110]: 任务类型
            - img [ref=e113]
          - generic [ref=e116] [cursor=pointer]:
            - generic:
              - combobox [ref=e118]
              - generic [ref=e119]: 执行状态
            - img [ref=e122]
        - generic [ref=e124]:
          - button "搜索" [ref=e125] [cursor=pointer]:
            - generic [ref=e126]: 搜索
          - button "重置" [ref=e127] [cursor=pointer]:
            - generic [ref=e128]: 重置
      - generic [ref=e131]:
        - table [ref=e133]:
          - rowgroup [ref=e144]:
            - row "选择所有行 任务名称 任务类型 用例数 执行状态 成功率 执行人 最近执行 操作" [ref=e145]:
              - columnheader "选择所有行" [ref=e146]:
                - generic "选择所有行" [ref=e148]:
                  - generic [ref=e149] [cursor=pointer]:
                    - checkbox "选择所有行" [disabled]
              - columnheader "任务名称" [ref=e151]:
                - generic [ref=e152]: 任务名称
              - columnheader "任务类型" [ref=e153]:
                - generic [ref=e154]: 任务类型
              - columnheader "用例数" [ref=e155]:
                - generic [ref=e156]: 用例数
              - columnheader "执行状态" [ref=e157]:
                - generic [ref=e158]: 执行状态
              - columnheader "成功率" [ref=e159]:
                - generic [ref=e160]: 成功率
              - columnheader "执行人" [ref=e161]:
                - generic [ref=e162]: 执行人
              - columnheader "最近执行" [ref=e163]:
                - generic [ref=e164]: 最近执行
              - columnheader "操作" [ref=e165]:
                - generic [ref=e166]: 操作
        - generic [ref=e170]:
          - table:
            - rowgroup
          - generic [ref=e172]: 暂无数据
```

# Test source

```ts
  61  |     await fillFormField(page, '描述', '自动化创建的API任务');
  62  | 
  63  |     // 选择环境（如果有）
  64  |     const envSelect = dialog.locator('.el-form-item:has(label:has-text("环境")) .el-select');
  65  |     if (await envSelect.isVisible()) {
  66  |       await envSelect.click();
  67  |       await page.click('.el-select-dropdown__item').first();
  68  |     }
  69  | 
  70  |     // 保存
  71  |     await clickButton(page, '确定');
  72  |     await waitForSuccessMessage(page);
  73  |     await waitForTableLoad(page);
  74  |   });
  75  | 
  76  |   test('应该能查看任务详情', async ({ page }) => {
  77  |     await waitForTableLoad(page);
  78  | 
  79  |     const viewButton = page.locator('.el-table__body-wrapper button:has-text("查看")').first();
  80  |     if (await viewButton.isVisible()) {
  81  |       await viewButton.click();
  82  |       await page.waitForLoadState('networkidle');
  83  | 
  84  |       // 验证详情页
  85  |       await expect(page.locator('.task-detail-view')).toBeVisible();
  86  | 
  87  |       // 验证基本信息标签页
  88  |       await expect(page.locator('.el-tabs__item:has-text("基本信息")')).toBeVisible();
  89  |     }
  90  |   });
  91  | 
  92  |   test('应该能编辑任务', async ({ page }) => {
  93  |     await waitForTableLoad(page);
  94  | 
  95  |     const viewButton = page.locator('.el-table__body-wrapper button:has-text("查看")').first();
  96  |     if (await viewButton.isVisible()) {
  97  |       await viewButton.click();
  98  |       await page.waitForLoadState('networkidle');
  99  | 
  100 |       // 点击编辑按钮
  101 |       await clickButton(page, '编辑');
  102 | 
  103 |       const dialog = page.locator('.el-dialog');
  104 |       await expect(dialog).toBeVisible();
  105 | 
  106 |       // 修改描述
  107 |       const descInput = dialog.locator('textarea').first();
  108 |       if (await descInput.isVisible()) {
  109 |         await descInput.fill('已修改的任务描述_' + Date.now());
  110 |       }
  111 | 
  112 |       // 保存
  113 |       await clickButton(page, '确定');
  114 |       await waitForSuccessMessage(page);
  115 |     }
  116 |   });
  117 | 
  118 |   test('应该能删除任务', async ({ page }) => {
  119 |     await waitForTableLoad(page);
  120 | 
  121 |     const deleteButton = page.locator('.el-table__body-wrapper button:has-text("删除")').first();
  122 |     if (await deleteButton.isVisible()) {
  123 |       await deleteButton.click();
  124 | 
  125 |       // 确认删除
  126 |       await page.click('.el-message-box__btns button:has-text("确定")');
  127 |       await waitForSuccessMessage(page);
  128 |       await waitForTableLoad(page);
  129 |     }
  130 |   });
  131 | 
  132 |   test('应该能按类型筛选任务', async ({ page }) => {
  133 |     await waitForTableLoad(page);
  134 | 
  135 |     // 找到类型筛选下拉框
  136 |     const typeFilter = page.locator('.el-select').filter({ hasText: '任务类型' }).first();
  137 |     if (await typeFilter.isVisible()) {
  138 |       await typeFilter.click();
  139 | 
  140 |       // 选择手工类型
  141 |       const manualOption = page.locator('.el-select-dropdown__item:has-text("手工")');
  142 |       if (await manualOption.isVisible()) {
  143 |         await manualOption.click();
  144 |         await waitForTableLoad(page);
  145 |       }
  146 | 
  147 |       // 清除筛选
  148 |       await typeFilter.click();
  149 |       const clearButton = typeFilter.locator('.el-select__clear');
  150 |       if (await clearButton.isVisible()) {
  151 |         await clearButton.click();
  152 |         await waitForTableLoad(page);
  153 |       }
  154 |     }
  155 |   });
  156 | 
  157 |   test('应该能搜索任务', async ({ page }) => {
  158 |     await waitForTableLoad(page);
  159 | 
  160 |     const searchInput = page.locator('input[placeholder*="搜索"]').first();
> 161 |     await searchInput.fill('任务');
      |                       ^ TimeoutError: locator.fill: Timeout 15000ms exceeded.
  162 |     await searchInput.press('Enter');
  163 |     await waitForTableLoad(page);
  164 | 
  165 |     await searchInput.clear();
  166 |     await searchInput.press('Enter');
  167 |     await waitForTableLoad(page);
  168 |   });
  169 | });
  170 | 
```