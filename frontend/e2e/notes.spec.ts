import { test, expect } from '@playwright/test';
import { seedMeeting } from './helpers';

test.describe('Notes with seeded data', () => {
  test.beforeAll(async () => {
    await seedMeeting();
  });

  test('shows seeded meeting in notes list', async ({ page }) => {
    await page.goto('/');
    // Wait for the list to load — should see the seeded meeting card
    await expect(page.getByText('3 speakers')).toBeVisible({ timeout: 10000 });
    await expect(page.getByText('2 topics')).toBeVisible();
    await expect(page.getByText('1 action item')).toBeVisible();
    await expect(page.getByText('45:00')).toBeVisible();
  });

  test('navigates to note detail view', async ({ page }) => {
    await page.goto('/');
    // Click the meeting card
    await page.getByText('3 speakers').click();

    // Should navigate to the detail view
    await expect(page).toHaveURL(/\/notes\//);

    // Metadata should be visible
    await expect(page.getByText('45:00')).toBeVisible();

    // Overview text should be visible
    await expect(page.getByText('Test meeting about project planning and roadmap.')).toBeVisible();
  });

  test('detail view shows topics and action items', async ({ page }) => {
    await page.goto('/');
    await page.getByText('3 speakers').click();
    await expect(page).toHaveURL(/\/notes\//);

    // Topics
    await expect(page.getByText('Project Roadmap')).toBeVisible();
    await expect(page.getByText('Testing Strategy')).toBeVisible();

    // Action items
    await expect(page.getByText('Write the technical spec')).toBeVisible();

    // Decisions
    await expect(page.getByText('Ship v2 by end of March')).toBeVisible();
  });
});
