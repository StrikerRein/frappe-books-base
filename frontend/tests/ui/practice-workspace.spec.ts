import { expect, test } from '@playwright/test';
import { useBooksSession } from './helpers/session';

useBooksSession();

test('practice workspace remains useful when no client-review portal is configured', async ({ page }) => {
  await page.goto('/books/practice');
  await expect(page.getByRole('heading', { name: /work that matters/i })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Work queue' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Bank statements' })).toBeVisible();
  await expect(page.getByRole('link', { name: /Import or review a statement/i })).toBeVisible();

  // The bank module remains available even if the separate portal backend fails.
  await page.getByRole('link', { name: /Import or review a statement/i }).click();
  await expect(page).toHaveURL(/\/books\/bank-statements$/);
  await expect(page.getByRole('heading', { name: 'Upload a statement' })).toBeVisible();
  await expect(page.getByText('1. Upload CSV')).toBeVisible();
});

test('practice navigation is accessible from the desktop sidebar', async ({ page }) => {
  const navigation = page.getByRole('navigation', { name: 'Books', exact: true });
  await navigation.getByRole('link', { name: 'Practice' }).click();
  await expect(page).toHaveURL(/\/books\/practice$/);
  await expect(page.getByRole('heading', { name: 'Work queue' })).toBeVisible();
});
