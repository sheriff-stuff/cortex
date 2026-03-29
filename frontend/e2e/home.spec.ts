import { test, expect } from '@playwright/test';

test.describe('Home page', () => {
  test('shows empty state when no notes exist', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('No notes yet.')).toBeVisible();
    await expect(page.getByText('Upload a recording to get started.')).toBeVisible();
  });

  test('shows header with navigation', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByRole('button', { name: 'Meetings' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Templates' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Upload' })).toBeVisible();
  });

  test('navigates to Templates page', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('button', { name: 'Templates' }).click();
    await expect(page).toHaveURL('/templates');
    await expect(page.getByText('Prompt Templates')).toBeVisible();
  });

  test('navigates to upload page via header button', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('button', { name: 'Upload' }).click();
    await expect(page.getByText('Process a Recording')).toBeVisible();
  });
});
