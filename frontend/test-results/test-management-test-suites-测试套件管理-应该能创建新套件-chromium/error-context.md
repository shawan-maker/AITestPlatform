# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: test-management\test-suites.spec.js >> 测试套件管理 >> 应该能创建新套件
- Location: e2e\test-management\test-suites.spec.js:24:3

# Error details

```
TimeoutError: page.click: Timeout 15000ms exceeded.
Call log:
  - waiting for locator('button:has-text("新建套件")')

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
  1  | import { expect } from '@playwright/test';
  2  | 
  3  | export const TEST_USER = {
  4  |   username: 'admin',
  5  |   password: '123456',
  6  | };
  7  | 
  8  | export async function login(page, username = TEST_USER.username, password = TEST_USER.password) {
  9  |   await page.goto('/login');
  10 |   await page.waitForLoadState('networkidle');
  11 | 
  12 |   // Element Plus 表单使用 autocomplete 属性
  13 |   await page.locator('input[autocomplete="username"]').fill(username);
  14 |   await page.locator('input[autocomplete="current-password"]').fill(password);
  15 |   await page.getByRole('button', { name: /登录|Sign In/ }).click();
  16 | 
  17 |   // 登录后跳转到 /agent
  18 |   await page.waitForURL('**/agent**', { timeout: 15000 });
  19 | }
  20 | 
  21 | export async function navigateTo(page, menuPath) {
  22 |   // 展开子菜单并点击
  23 |   for (let i = 0; i < menuPath.length; i++) {
  24 |     const menuItem = menuPath[i];
  25 |     if (i < menuPath.length - 1) {
  26 |       // 父菜单 - 展开
  27 |       await page.locator('.el-sub-menu__title').filter({ hasText: menuItem }).click();
  28 |       await page.waitForTimeout(300);
  29 |     } else {
  30 |       // 叶子菜单 - 点击导航
  31 |       await page.locator('.el-menu-item').filter({ hasText: menuItem }).click();
  32 |       await page.waitForTimeout(500);
  33 |     }
  34 |   }
  35 |   await page.waitForLoadState('networkidle');
  36 | }
  37 | 
  38 | export async function selectProject(page) {
  39 |   // 选择第一个可用项目
  40 |   const switcher = page.locator('.project-switcher');
  41 |   if (await switcher.isVisible()) {
  42 |     await switcher.click();
  43 |     await page.waitForTimeout(300);
  44 |     const firstOption = page.locator('.el-select-dropdown__item').first();
  45 |     if (await firstOption.isVisible()) {
  46 |       await firstOption.click();
  47 |       await page.waitForTimeout(1000);
  48 |     }
  49 |   }
  50 | }
  51 | 
  52 | export async function waitForTableLoad(page) {
  53 |   await page.waitForLoadState('networkidle');
  54 |   await page.waitForTimeout(500);
  55 | }
  56 | 
  57 | export async function fillFormField(page, label, value) {
  58 |   const formItem = page.locator(`.el-form-item:has(label:has-text("${label}"))`);
  59 |   const input = formItem.locator('input, textarea').first();
  60 |   await input.fill(value);
  61 | }
  62 | 
  63 | export async function selectFormOption(page, label, optionText) {
  64 |   const formItem = page.locator(`.el-form-item:has(label:has-text("${label}"))`);
  65 |   await formItem.locator('.el-select').click();
  66 |   await page.click(`.el-select-dropdown__item:has-text("${optionText}")`);
  67 | }
  68 | 
  69 | export async function clickButton(page, buttonText) {
> 70 |   await page.click(`button:has-text("${buttonText}")`);
     |              ^ TimeoutError: page.click: Timeout 15000ms exceeded.
  71 |   await page.waitForTimeout(500);
  72 | }
  73 | 
  74 | export async function waitForSuccessMessage(page) {
  75 |   await expect(page.locator('.el-message--success')).toBeVisible({ timeout: 10000 });
  76 | }
  77 | 
  78 | export async function closeDialog(page) {
  79 |   await page.click('.el-dialog__close');
  80 |   await page.waitForTimeout(500);
  81 | }
  82 | 
```