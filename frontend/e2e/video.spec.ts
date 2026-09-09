import { test, expect } from "@playwright/test";
test("record camera video, real server pose, timeline, review and PDF", async ({
  page,
}) => {
  test.skip(
    !process.env.E2E_CAMERA_FILE || !process.env.E2E_PASSWORD,
    "Requires camera fixture, demo credentials and running worker.",
  );
  test.setTimeout(150000);
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await page
    .getByLabel("E-mail", { exact: true })
    .fill(process.env.E2E_EMAIL || "admin@biometria.local");
  await page
    .getByLabel("Senha", { exact: true })
    .fill(process.env.E2E_PASSWORD!);
  await page.getByRole("button", { name: "Entrar na plataforma" }).click();
  await expect(page.getByRole("heading", { name: /^Olá,/ })).toBeVisible();
  await page
    .getByRole("button", { name: "Nova avaliação", exact: true })
    .click();
  await page
    .getByRole("combobox", { name: "Modo", exact: true })
    .selectOption("video");
  await page
    .getByRole("combobox", { name: "Protocolo", exact: true })
    .selectOption("bilateral_squat");
  await page
    .getByRole("button", { name: "Iniciar captura", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Gravar movimento", exact: true })
    .click();
  await expect(page.getByText("Gravando · 3s", { exact: true })).toBeVisible({
    timeout: 10000,
  });
  await page
    .getByRole("button", { name: "Parar gravação", exact: true })
    .click();
  await page.getByLabel("Conferi a câmera fixa e nivelada.").check();
  await page.getByLabel("Confirmei o plano do movimento.").check();
  await page
    .getByRole("button", { name: "Processar vídeo", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Vídeo e medidas sincronizados" }),
  ).toBeVisible({ timeout: 90000 });
  await expect(page.locator(".measure-value").first()).toBeVisible();
  await expect(
    page.getByText("0 ciclos completos · experimental", { exact: true }),
  ).toBeVisible();
  const slider = page.getByLabel("Frame da análise", { exact: true });
  await slider.fill("3");
  await expect(page.locator(".phase-card")).not.toContainText("Frame 0 ·");
  await page.getByRole("button", { name: /Ombros/ }).click();
  await expect(page.locator(".finding").first()).toBeVisible();
  await page.getByRole("button", { name: "Todas", exact: true }).click();
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Baixar relatório PDF" }).click();
  expect((await download).suggestedFilename()).toMatch(/\.pdf$/);
  await page.getByRole("button", { name: "Histórico", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Histórico de avaliações" }),
  ).toBeVisible();
  expect(errors).toEqual([]);
});
