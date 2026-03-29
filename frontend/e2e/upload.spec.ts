import { test, expect } from '@playwright/test';

test.describe('Upload page', () => {
  test('shows upload UI with drop zone and template selector', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('button', { name: 'Upload' }).click();

    await expect(page.getByText('Process a Recording')).toBeVisible();
    await expect(page.getByText('Drag & drop your file here')).toBeVisible();
    await expect(page.getByText('MP3, WAV, M4A, AAC, MP4, MKV, AVI, MOV')).toBeVisible();
    await expect(page.getByText('Extraction Template')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Process' })).toBeDisabled();
  });

  test('shows "Process New Recording" button on home page', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByRole('button', { name: '+ Process New Recording' })).toBeVisible();
  });
});
