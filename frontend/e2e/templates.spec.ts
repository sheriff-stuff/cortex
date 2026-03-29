import { test, expect } from '@playwright/test';

test.describe('Templates page', () => {
  test('shows default template on load', async ({ page }) => {
    await page.goto('/templates');
    await expect(page.getByText('Prompt Templates')).toBeVisible();
    // Default template card should be visible with a "Default" badge
    await expect(page.getByText('Default Extraction')).toBeVisible();
    await expect(page.getByText('Default', { exact: true })).toBeVisible();
  });

  test('default template has no delete button', async ({ page }) => {
    await page.goto('/templates');
    await expect(page.getByText('Default Extraction')).toBeVisible();
    // The default template card should have a duplicate button but no delete button
    const defaultCard = page.locator('.cursor-pointer', { hasText: 'Default Extraction' }).first();
    await expect(defaultCard.getByTitle('Duplicate')).toBeVisible();
    await expect(defaultCard.getByTitle('Delete')).not.toBeVisible();
  });

  test('duplicate a template', async ({ page }) => {
    await page.goto('/templates');
    await expect(page.getByText('Default Extraction')).toBeVisible();

    const defaultCard = page.locator('.cursor-pointer', { hasText: 'Default Extraction' }).first();
    await defaultCard.getByTitle('Duplicate').click();

    // A copy should appear
    await expect(page.getByText('Default Extraction (copy)')).toBeVisible({ timeout: 5000 });
  });

  test('create a new template', async ({ page }) => {
    await page.goto('/templates');

    // Click the "Create Template" card
    await page.getByText('Create Template').click();

    // The editor modal should open with "New Template" heading
    await expect(page.getByText('New Template')).toBeVisible();

    // Fill in the name and description
    const nameInput = page.locator('input[placeholder="Template name"]');
    await nameInput.fill('My Test Template');

    const descInput = page.locator('input[placeholder*="Short description"]');
    await descInput.fill('A template for testing purposes');

    // Save — the prompt text is pre-filled with the default prompt
    await page.getByRole('button', { name: 'Save' }).click();

    // Modal should close and the new template card should appear
    await expect(page.getByText('My Test Template')).toBeVisible({ timeout: 5000 });
  });

  test('delete a non-default template', async ({ page }) => {
    await page.goto('/templates');
    // Wait for templates to load
    await expect(page.getByText('Default Extraction', { exact: true })).toBeVisible();

    // Count how many delete buttons exist before
    const cardsBefore = await page.locator('[title="Delete"]').count();

    // Duplicate the default to create a deletable template
    const defaultCard = page.locator('.cursor-pointer').filter({ has: page.getByText('Default', { exact: true }) }).first();
    await defaultCard.getByTitle('Duplicate').click();

    // Wait for the new delete button to appear
    await expect(page.locator('[title="Delete"]')).toHaveCount(cardsBefore + 1, { timeout: 5000 });

    // Delete the last duplicated card
    await page.locator('[title="Delete"]').last().click();

    // Should go back to original count
    await expect(page.locator('[title="Delete"]')).toHaveCount(cardsBefore, { timeout: 5000 });
  });
});
