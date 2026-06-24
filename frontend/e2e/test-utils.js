import { expect } from '@playwright/test';

export const TEST_USER = {
  username: 'admin',
  password: '123456',
};

export async function login(page, username = TEST_USER.username, password = TEST_USER.password) {
  await page.goto('/login');
  await page.waitForLoadState('networkidle');

  // Element Plus 表单使用 autocomplete 属性
  await page.locator('input[autocomplete="username"]').fill(username);
  await page.locator('input[autocomplete="current-password"]').fill(password);
  await page.getByRole('button', { name: /登录|Sign In/ }).click();

  // 登录后跳转到 /agent
  await page.waitForURL('**/agent**', { timeout: 15000 });
}

export async function navigateTo(page, menuPath) {
  // 展开子菜单并点击
  for (let i = 0; i < menuPath.length; i++) {
    const menuItem = menuPath[i];
    if (i < menuPath.length - 1) {
      // 父菜单 - 展开
      await page.locator('.el-sub-menu__title').filter({ hasText: menuItem }).click();
      await page.waitForTimeout(300);
    } else {
      // 叶子菜单 - 点击导航
      await page.locator('.el-menu-item').filter({ hasText: menuItem }).click();
      await page.waitForTimeout(500);
    }
  }
  await page.waitForLoadState('networkidle');
}

export async function selectProject(page) {
  // 选择第一个可用项目
  const switcher = page.locator('.project-switcher');
  if (await switcher.isVisible()) {
    await switcher.click();
    await page.waitForTimeout(300);
    const firstOption = page.locator('.el-select-dropdown__item').first();
    if (await firstOption.isVisible()) {
      await firstOption.click();
      await page.waitForTimeout(1000);
    }
  }
}

export async function waitForTableLoad(page) {
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(500);
}

export async function fillFormField(page, label, value) {
  const formItem = page.locator(`.el-form-item:has(label:has-text("${label}"))`);
  const input = formItem.locator('input, textarea').first();
  await input.fill(value);
}

export async function selectFormOption(page, label, optionText) {
  const formItem = page.locator(`.el-form-item:has(label:has-text("${label}"))`);
  await formItem.locator('.el-select').click();
  await page.click(`.el-select-dropdown__item:has-text("${optionText}")`);
}

export async function clickButton(page, buttonText) {
  await page.click(`button:has-text("${buttonText}")`);
  await page.waitForTimeout(500);
}

export async function waitForSuccessMessage(page) {
  await expect(page.locator('.el-message--success')).toBeVisible({ timeout: 10000 });
}

export async function closeDialog(page) {
  await page.click('.el-dialog__close');
  await page.waitForTimeout(500);
}
