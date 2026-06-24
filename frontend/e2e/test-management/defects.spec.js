import { test, expect } from '@playwright/test';
import { login, navigateTo, selectProject, waitForTableLoad, fillFormField, selectFormOption, clickButton, waitForSuccessMessage, closeDialog } from '../test-utils.js';

test.describe('缺陷管理', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await navigateTo(page, ['测试管理', '测试缺陷']);
    await selectProject(page);
  });

  test('应该能查看缺陷列表', async ({ page }) => {
    await waitForTableLoad(page);

    const table = page.locator('.el-table');
    await expect(table).toBeVisible();

    // 验证表头
    await expect(page.locator('th:has-text("缺陷标题")')).toBeVisible();
    await expect(page.locator('th:has-text("严重程度")')).toBeVisible();
    await expect(page.locator('th:has-text("优先级")')).toBeVisible();
    await expect(page.locator('th:has-text("状态")')).toBeVisible();
  });

  test('应该能创建新缺陷', async ({ page }) => {
    await clickButton(page, '新建缺陷');

    const dialog = page.locator('.el-dialog');
    await expect(dialog).toBeVisible();

    // 填写表单
    await fillFormField(page, '缺陷标题', `自动化缺陷_${Date.now()}`);

    // 选择缺陷类型
    await selectFormOption(page, '缺陷类型', '功能');

    // 选择严重程度
    await selectFormOption(page, '严重程度', '一般');

    // 选择优先级
    await selectFormOption(page, '优先级', '中');

    // 填写缺陷步骤
    const stepsInput = dialog.locator('textarea').first();
    if (await stepsInput.isVisible()) {
      await stepsInput.fill('1. 打开系统\n2. 执行操作\n3. 观察到错误');
    }

    // 填写缺陷原因
    const causeInput = dialog.locator('textarea').nth(1);
    if (await causeInput.isVisible()) {
      await causeInput.fill('自动化测试发现的缺陷原因');
    }

    // 保存
    await clickButton(page, '确定');
    await waitForSuccessMessage(page);
    await waitForTableLoad(page);
  });

  test('应该能查看缺陷详情', async ({ page }) => {
    await waitForTableLoad(page);

    const viewButton = page.locator('.el-table__body-wrapper button:has-text("查看")').first();
    if (await viewButton.isVisible()) {
      await viewButton.click();
      await page.waitForLoadState('networkidle');

      // 验证详情页
      await expect(page.locator('.defect-detail-view')).toBeVisible();

      // 验证基本信息区域
      await expect(page.locator('text=基本信息')).toBeVisible();

      // 验证状态流转按钮
      await expect(page.locator('button:has-text("处理缺陷")')).toBeVisible();
    }
  });

  test('应该能编辑缺陷', async ({ page }) => {
    await waitForTableLoad(page);

    const viewButton = page.locator('.el-table__body-wrapper button:has-text("查看")').first();
    if (await viewButton.isVisible()) {
      await viewButton.click();
      await page.waitForLoadState('networkidle');

      // 点击编辑按钮
      await clickButton(page, '编辑');

      const editSection = page.locator('text=编辑缺陷');
      await expect(editSection).toBeVisible();

      // 修改标题
      const titleInput = page.locator('.el-form-item:has(label:has-text("缺陷标题")) input');
      if (await titleInput.isVisible()) {
        await titleInput.fill('已修改的缺陷标题_' + Date.now());
      }

      // 点击保存
      const saveButton = page.locator('button:has-text("保存")');
      await saveButton.click();
      await waitForSuccessMessage(page);
    }
  });

  test('应该能处理缺陷状态流转', async ({ page }) => {
    await waitForTableLoad(page);

    const viewButton = page.locator('.el-table__body-wrapper button:has-text("查看")').first();
    if (await viewButton.isVisible()) {
      await viewButton.click();
      await page.waitForLoadState('networkidle');

      // 点击处理缺陷按钮
      await clickButton(page, '处理缺陷');

      const dialog = page.locator('.el-dialog');
      await expect(dialog).toBeVisible();

      // 选择新状态
      const statusSelect = dialog.locator('.el-select');
      await statusSelect.click();

      // 选择"打开"状态
      const openOption = page.locator('.el-select-dropdown__item:has-text("打开")');
      if (await openOption.isVisible()) {
        await openOption.click();
      }

      // 确认
      await clickButton(page, '确定');
      await waitForSuccessMessage(page);
    }
  });

  test('应该能添加评论', async ({ page }) => {
    await waitForTableLoad(page);

    const viewButton = page.locator('.el-table__body-wrapper button:has-text("查看")').first();
    if (await viewButton.isVisible()) {
      await viewButton.click();
      await page.waitForLoadState('networkidle');

      // 找到评论输入框
      const commentInput = page.locator('textarea[placeholder*="评论"]').first();
      if (await commentInput.isVisible()) {
        await commentInput.fill('自动化测试添加的评论_' + Date.now());

        // 点击添加评论按钮
        await clickButton(page, '添加评论');
        await waitForSuccessMessage(page);
      }
    }
  });

  test('应该能按严重程度筛选缺陷', async ({ page }) => {
    await waitForTableLoad(page);

    const severityFilter = page.locator('.el-select').filter({ hasText: '严重程度' }).first();
    if (await severityFilter.isVisible()) {
      await severityFilter.click();

      const seriousOption = page.locator('.el-select-dropdown__item:has-text("严重")');
      if (await seriousOption.isVisible()) {
        await seriousOption.click();
        await waitForTableLoad(page);
      }

      // 清除筛选
      await severityFilter.click();
      const clearButton = severityFilter.locator('.el-select__clear');
      if (await clearButton.isVisible()) {
        await clearButton.click();
        await waitForTableLoad(page);
      }
    }
  });

  test('应该能按优先级筛选缺陷', async ({ page }) => {
    await waitForTableLoad(page);

    const priorityFilter = page.locator('.el-select').filter({ hasText: '优先级' }).first();
    if (await priorityFilter.isVisible()) {
      await priorityFilter.click();

      const highOption = page.locator('.el-select-dropdown__item:has-text("高")');
      if (await highOption.isVisible()) {
        await highOption.click();
        await waitForTableLoad(page);
      }

      // 清除筛选
      await priorityFilter.click();
      const clearButton = priorityFilter.locator('.el-select__clear');
      if (await clearButton.isVisible()) {
        await clearButton.click();
        await waitForTableLoad(page);
      }
    }
  });

  test('应该能按状态筛选缺陷', async ({ page }) => {
    await waitForTableLoad(page);

    const statusFilter = page.locator('.el-select').filter({ hasText: '状态' }).first();
    if (await statusFilter.isVisible()) {
      await statusFilter.click();

      const openOption = page.locator('.el-select-dropdown__item:has-text("打开")');
      if (await openOption.isVisible()) {
        await openOption.click();
        await waitForTableLoad(page);
      }

      // 清除筛选
      await statusFilter.click();
      const clearButton = statusFilter.locator('.el-select__clear');
      if (await clearButton.isVisible()) {
        await clearButton.click();
        await waitForTableLoad(page);
      }
    }
  });

  test('应该能搜索缺陷', async ({ page }) => {
    await waitForTableLoad(page);

    const searchInput = page.locator('input[placeholder*="搜索"]').first();
    await searchInput.fill('缺陷');
    await searchInput.press('Enter');
    await waitForTableLoad(page);

    await searchInput.clear();
    await searchInput.press('Enter');
    await waitForTableLoad(page);
  });

  test('应该能批量删除缺陷', async ({ page }) => {
    await waitForTableLoad(page);

    // 选择第一行
    const firstCheckbox = page.locator('.el-table__body-wrapper .el-checkbox').first();
    if (await firstCheckbox.isVisible()) {
      await firstCheckbox.click();

      // 点击批量删除按钮
      const batchDeleteButton = page.locator('button:has-text("批量删除")');
      if (await batchDeleteButton.isVisible()) {
        await batchDeleteButton.click();

        // 确认删除
        await page.click('.el-message-box__btns button:has-text("确定")');
        await waitForSuccessMessage(page);
        await waitForTableLoad(page);
      }
    }
  });
});
