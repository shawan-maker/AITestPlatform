import { test, expect } from '@playwright/test';
import { login, navigateTo, selectProject, waitForTableLoad, fillFormField, selectFormOption, clickButton, waitForSuccessMessage, closeDialog } from '../test-utils.js';

test.describe('测试任务管理', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await navigateTo(page, ['测试管理', '测试任务']);
    await selectProject(page);
  });

  test('应该能查看任务列表', async ({ page }) => {
    await waitForTableLoad(page);

    // 验证表格存在
    const table = page.locator('.el-table');
    await expect(table).toBeVisible();

    // 验证表头
    await expect(page.locator('th:has-text("任务名称")')).toBeVisible();
    await expect(page.locator('th:has-text("任务类型")')).toBeVisible();
  });

  test('应该能创建手工测试任务', async ({ page }) => {
    await clickButton(page, '新建任务');

    const dialog = page.locator('.el-dialog');
    await expect(dialog).toBeVisible();

    // 填写表单
    await fillFormField(page, '任务名称', `手工任务_${Date.now()}`);

    // 选择类型为手工
    const typeRadio = dialog.locator('.el-radio:has-text("手工")');
    if (await typeRadio.isVisible()) {
      await typeRadio.click();
    }

    await fillFormField(page, '描述', '自动化创建的手工任务');

    // 保存
    await clickButton(page, '确定');
    await waitForSuccessMessage(page);
    await waitForTableLoad(page);
  });

  test('应该能创建API测试任务', async ({ page }) => {
    await clickButton(page, '新建任务');

    const dialog = page.locator('.el-dialog');
    await expect(dialog).toBeVisible();

    // 填写表单
    await fillFormField(page, '任务名称', `API任务_${Date.now()}`);

    // 选择类型为API
    const typeRadio = dialog.locator('.el-radio:has-text("API")');
    if (await typeRadio.isVisible()) {
      await typeRadio.click();
    }

    await fillFormField(page, '描述', '自动化创建的API任务');

    // 选择环境（如果有）
    const envSelect = dialog.locator('.el-form-item:has(label:has-text("环境")) .el-select');
    if (await envSelect.isVisible()) {
      await envSelect.click();
      await page.click('.el-select-dropdown__item').first();
    }

    // 保存
    await clickButton(page, '确定');
    await waitForSuccessMessage(page);
    await waitForTableLoad(page);
  });

  test('应该能查看任务详情', async ({ page }) => {
    await waitForTableLoad(page);

    const viewButton = page.locator('.el-table__body-wrapper button:has-text("查看")').first();
    if (await viewButton.isVisible()) {
      await viewButton.click();
      await page.waitForLoadState('networkidle');

      // 验证详情页
      await expect(page.locator('.task-detail-view')).toBeVisible();

      // 验证基本信息标签页
      await expect(page.locator('.el-tabs__item:has-text("基本信息")')).toBeVisible();
    }
  });

  test('应该能编辑任务', async ({ page }) => {
    await waitForTableLoad(page);

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
        await descInput.fill('已修改的任务描述_' + Date.now());
      }

      // 保存
      await clickButton(page, '确定');
      await waitForSuccessMessage(page);
    }
  });

  test('应该能删除任务', async ({ page }) => {
    await waitForTableLoad(page);

    const deleteButton = page.locator('.el-table__body-wrapper button:has-text("删除")').first();
    if (await deleteButton.isVisible()) {
      await deleteButton.click();

      // 确认删除
      await page.click('.el-message-box__btns button:has-text("确定")');
      await waitForSuccessMessage(page);
      await waitForTableLoad(page);
    }
  });

  test('应该能按类型筛选任务', async ({ page }) => {
    await waitForTableLoad(page);

    // 找到类型筛选下拉框
    const typeFilter = page.locator('.el-select').filter({ hasText: '任务类型' }).first();
    if (await typeFilter.isVisible()) {
      await typeFilter.click();

      // 选择手工类型
      const manualOption = page.locator('.el-select-dropdown__item:has-text("手工")');
      if (await manualOption.isVisible()) {
        await manualOption.click();
        await waitForTableLoad(page);
      }

      // 清除筛选
      await typeFilter.click();
      const clearButton = typeFilter.locator('.el-select__clear');
      if (await clearButton.isVisible()) {
        await clearButton.click();
        await waitForTableLoad(page);
      }
    }
  });

  test('应该能搜索任务', async ({ page }) => {
    await waitForTableLoad(page);

    const searchInput = page.locator('input[placeholder*="搜索"]').first();
    await searchInput.fill('任务');
    await searchInput.press('Enter');
    await waitForTableLoad(page);

    await searchInput.clear();
    await searchInput.press('Enter');
    await waitForTableLoad(page);
  });
});
