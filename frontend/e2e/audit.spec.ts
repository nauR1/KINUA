import { test, expect, type Page } from "@playwright/test";
async function login(page: Page) {
  await page.goto("/");
  await page.getByLabel("E-mail", { exact: true }).fill(process.env.E2E_EMAIL!);
  await page
    .getByLabel("Senha", { exact: true })
    .fill(process.env.E2E_PASSWORD!);
  await page.getByRole("button", { name: "Entrar na plataforma" }).click();
  await expect(page.getByRole("heading", { name: /Olá,/ })).toBeVisible();
}
test.beforeEach(({ page }) => {
  page.setDefaultTimeout(10000);
  test.skip(
    process.env.E2E_ISOLATED !== "1" || !process.env.E2E_PASSWORD,
    "Requires isolated QA",
  );
});
test("patient create edit reopen and preserved optional fields", async ({
  page,
}) => {
  await login(page);
  await page.getByRole("button", { name: "Pacientes", exact: true }).click();
  await page
    .getByRole("button", { name: "Cadastrar paciente", exact: true })
    .click();
  const name = "QA Audit " + Date.now();
  await page.getByLabel("Nome completo").fill(name);
  await page.getByLabel("Data de nascimento").fill("1990-01-01");
  await page.getByLabel("Telefone", { exact: true }).fill("111111");
  await page.getByLabel("Histórico relevante").fill("Synthetic history");
  await page
    .getByRole("button", { name: "Cadastrar paciente", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Editar paciente", exact: true })
    .click();
  await expect(page.getByLabel("Telefone", { exact: true })).toHaveValue(
    "111111",
  );
  await page.getByLabel("Telefone", { exact: true }).fill("222222");
  await page
    .getByRole("button", { name: "Salvar paciente", exact: true })
    .click();
  await page.reload();
  await page.getByRole("button", { name: "Pacientes", exact: true }).click();
  await page
    .getByRole("row")
    .filter({ hasText: name })
    .getByRole("button", { name: "Abrir", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Editar paciente", exact: true })
    .click();
  await expect(page.getByLabel("Telefone", { exact: true })).toHaveValue(
    "222222",
  );
  await expect(page.getByLabel("Histórico relevante")).toHaveValue(
    "Synthetic history",
  );
});
for (const kind of ["NotAllowedError", "NotFoundError", "NotReadableError"])
  test("camera " + kind, async ({ page }) => {
    await page.addInitScript((kind) => {
      Object.defineProperty(navigator.mediaDevices, "getUserMedia", {
        value: async () => {
          throw new DOMException("native", kind);
        },
      });
    }, kind);
    await login(page);
    await page
      .getByRole("button", { name: "Nova avaliação", exact: true })
      .click();
    await page
      .getByRole("button", { name: "Iniciar captura", exact: true })
      .click();
    await page
      .getByRole("button", { name: "Abrir câmera", exact: true })
      .click();
    await expect(page.locator(".error")).toContainText("câmera");
    await expect(page.locator(".error")).not.toContainText("native");
    await expect(
      page.getByRole("button", { name: "Abrir câmera", exact: true }),
    ).toBeEnabled();
  });
test("all navigation widths and console", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await login(page);
  for (const [width, height] of [
    [1920, 1080],
    [1440, 900],
    [1366, 768],
    [1024, 768],
    [768, 1024],
    [390, 844],
  ]) {
    await page.setViewportSize({ width, height });
    for (const name of [
      "Início",
      "Pacientes",
      "Avaliações",
      "Protocolos",
      "ROM",
      "Relatórios",
      "Configurações",
    ]) {
      await page.getByRole("button", { name, exact: true }).click();
      await expect(page.locator("main")).toBeVisible();
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
      ).toBe(true);
    }
  }
  expect(errors).toEqual([]);
});
