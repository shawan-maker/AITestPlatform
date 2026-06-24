import { test, expect } from '@playwright/test';
import { login, navigateTo, selectProject, waitForTableLoad, fillFormField, selectFormOption, clickButton, waitForSuccessMessage, closeDialog } from '../test-utils.js';

test.describe('测试套件管理', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await navigateTo(page, ['测试管理', '测试套件']);
    await selectProject(page);
  });

  test('应该能查看套件列表', async ({ page }) => {
    await waitForTableLoad(page);

    // 验证表格存在
    const table = page.locator('.el-table');
    await expect(table).toBeVisible();

    // 验证表头
    await expect(page.locator('th:has-text("套件名称")')).toBeVisible();
    await expect(page.locator('th:has-text("用例数量")')).toBeVisible();
    await expect(page.locator('th:has-text("执行状态")')).toBeVisible();
  });

  test('应该能创建新套件', async ({ page }) => {
    await clickButton(page, '新建套件');

    // 等待对话框出现
    const dialog = page.locator('.el-dialog');
    await expect(dialog).toBeVisible();

    // 填写表单
    await fillFormField(page, '套件名称', `自动化测试套件_${Date.now()}`);
    await fillFormField(page, '描述', '这是自动化测试创建的套件');

    // 选择环境（如果有）
    const envSelect = page.locator('.el-form-item:has(label:has-text("环境")) .el-select');
    if (await envSelect.isVisible()) {
      await envSelect.click();
      await page.click('.el-select-dropdown__item').first();
    }

    // 保存
    await clickButton(page, '确定');
    await waitForSuccessMessage(page);

    // 验证套件出现在列表中
    await waitForTableLoad(page);
  });

  test('应该能查看套件详情', async ({ page }) => {
    await waitForTableLoad(page);

    // 点击第一行的查看按钮
    const viewButton = page.locator('.el-table__body-wrapper button:has-text("查看")').first();
    if (await viewButton.isVisible()) {
      await viewButton.click();
      await page.waitForLoadState('networkidle');

      // 验证详情页
      await expect(page.locator('.suite-detail-view')).toBeVisible();

      // 验证基本信息标签页
      await expect(page.locator('.el-tabs__item:has-text("基本信息")')).toBeVisible();

      // 验证用例列表标签页
      await expect(page.locator('.el-tabs__item:has-text("用例列表")')).toBeVisible();

      // 切换到用例列表
      await page.click('.el-tabs__item:has-text("用例列表")');
      await waitForTableLoad(page);
    }
  });

  test('应该能编辑套件', async ({ page }) => {
    await waitForTableLoad(page);

    // 进入详情页
    const viewButton = page.locator('.el-table__body-wrapper button:has-text("查看")').first();
    if (await viewButton.isVisible()) {
      await viewButton.click();
      await page.waitForLoadState('networkidle');

      // 点击编辑按钮
      await clickButton(page, '编辑');

      const dialog = page.locator('.el-dialog');
      await expect(dialog).toBeVisible();

      // 修改描述
      const descInput = dialog.locator('textarea').first();
      if (await descInput.isVisible()) {
        await descInput.fill('已修改的描述_' + Date.now());
      }

      // 保存
      await clickButton(page, '确定');
      await waitForSuccessMessage(page);
    }
  });

  test('应该能删除套件', async ({ page }) => {
    await waitForTableLoad(page);

    // 点击删除按钮
    const deleteButton = page.locator('.el-table__body-wrapper button:has-text("删除")').first();
    if (await deleteButton.isVisible()) {
      await deleteButton.click();

      // 确认删除
      await page.click('.el-message-box__btns button:has-text("确定")');
      await waitForSuccessMessage(page);
      await waitForTableLoad(page);
    }
  });

  test('应该能搜索套件', async ({ page }) => {
    await waitForTableLoad(page);

    // 在搜索框输入
    const searchInput = page.locator('input[placeholder*="搜索"]').first();
    await searchInput.fill('测试');

    // 点击搜索或按回车
    await searchInput.press('Enter');
    await waitForTableLoad(page);

    // 清空搜索
    await searchInput.clear();
    await searchInput.press('Enter');
    await waitForTableLoad(page);
  });
});
