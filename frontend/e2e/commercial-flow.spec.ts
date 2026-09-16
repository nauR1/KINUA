import { test, expect, Page } from "@playwright/test";
import { readFileSync } from "node:fs";

test.use({ timezoneId: "America/Bahia" });

test("commercial onboarding through first completed assessment and report", async ({
  page,
  browser,
}) => {
  test.skip(
    process.env.E2E_ISOLATED !== "1" ||
      !process.env.E2E_PASSWORD ||
      !process.env.E2E_IMAGE,
    "Requires isolated QA database and authorized pose fixture.",
  );
  test.setTimeout(180000);
  page.setDefaultTimeout(15000);
  const password = process.env.E2E_PASSWORD!;
  const suffix = Date.now();
  const clinicName = `Clínica Comercial Fictícia ${suffix}`;
  const adminName = `Admin Comercial ${suffix}`;
  const adminEmail = `comercial${suffix}@qa.local`;
  const patientName = `Paciente Comercial Ficticio ${suffix}`;
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));

  async function login(target: Page, email: string) {
    target.setDefaultTimeout(15000);
    await target.context().clearCookies();
    await target.goto("/");
    await target.getByLabel("E-mail", { exact: true }).fill(email);
    await target.getByLabel("Senha", { exact: true }).fill(password);
    await target.getByRole("button", { name: "Entrar na plataforma" }).click();
  }

  await login(page, "platform@kinua.local");
  await expect(
    page.getByRole("heading", { name: "Gestão de acessos" }),
  ).toBeVisible();

  await page.getByRole("button", { name: "Clínicas", exact: true }).click();
  await page.getByLabel("Nome da clínica").fill(clinicName);
  await page.locator('select[name="plan_code"]').selectOption("lifetime");
  await page
    .getByRole("button", { name: "Salvar clínica", exact: true })
    .click();
  const clinicRow = page.getByRole("row").filter({ hasText: clinicName });
  await expect(clinicRow.getByText("ILIMITADO", { exact: true })).toBeVisible();

  const clinics = await (
    await page.request.get("/api/platform/clinics")
  ).json();
  const clinic = clinics.find((item: { name: string }) => item.name === clinicName);
  expect(clinic).toBeTruthy();

  await page
    .getByRole("button", { name: "Usuários e acessos", exact: true })
    .click();
  await page.getByLabel("Nome", { exact: true }).fill(adminName);
  await page.getByLabel("E-mail", { exact: true }).fill(adminEmail);
  await page.getByLabel("Senha inicial").fill(password);
  await page
    .getByRole("combobox", { name: "Clínica", exact: true })
    .selectOption(clinic.id);
  await page
    .getByRole("combobox", { name: "Permissão", exact: true })
    .selectOption("admin");
  const userCreated = page.waitForResponse(
    (response) =>
      response.url().endsWith("/api/platform/users") &&
      response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Cadastrar usuário" }).click();
  const userResponse = await userCreated;
  expect(userResponse.status()).toBe(201);
  expect(userResponse.request().postDataJSON()).toMatchObject({
    access_starts_at: null,
    access_expires_at: null,
  });

  const clinicContext = await browser.newContext({
    baseURL: process.env.E2E_BASE_URL,
    timezoneId: "America/Bahia",
  });
  const clinicPage = await clinicContext.newPage();
  const clinicErrors: string[] = [];
  clinicPage.on("pageerror", (error) => clinicErrors.push(error.message));
  await login(clinicPage, adminEmail);
  await expect(clinicPage.getByRole("heading", { name: /^Olá,/ })).toBeVisible();
  await expect(clinicPage.locator(".demo-banner")).toHaveCount(0);

  await clinicPage
    .getByRole("button", { name: "Pacientes", exact: true })
    .click();
  await clinicPage
    .getByRole("button", { name: "Cadastrar paciente", exact: true })
    .click();
  await clinicPage.getByLabel("Nome completo").fill(patientName);
  await clinicPage.getByLabel("Data de nascimento").fill("1991-03-11");
  await clinicPage
    .getByLabel("Queixa principal")
    .fill("Fluxo comercial automatizado com dados totalmente fictícios.");
  await clinicPage
    .getByRole("button", { name: "Cadastrar paciente", exact: true })
    .click();
  await expect(
    clinicPage.getByRole("heading", { name: patientName, exact: true }),
  ).toBeVisible();

  await clinicPage
    .getByRole("button", { name: "Avaliar paciente", exact: true })
    .click();
  await clinicPage
    .getByRole("button", { name: "Iniciar captura", exact: true })
    .click();
  await expect(
    clinicPage.getByRole("heading", { name: "Enquadre o corpo inteiro" }),
  ).toBeVisible();
  await clinicPage.locator('input[type="file"]').setInputFiles(process.env.E2E_IMAGE!);
  await clinicPage.getByLabel("Conferi o nivelamento da câmera.").check();
  await clinicPage.getByLabel("Confirmei a vista anterior.").check();
  await clinicPage
    .getByRole("button", { name: "Analisar e salvar captura" })
    .click();

  await expect(
    clinicPage.getByRole("heading", { name: "Resultados da avaliação" }),
  ).toBeVisible({ timeout: 60000 });
  await expect(clinicPage.locator(".measure-value").first()).toBeVisible();
  await expect(clinicPage.locator(".result-image canvas")).toBeVisible();

  const findings = clinicPage.locator(".finding");
  const findingCount = await findings.count();
  expect(findingCount).toBeGreaterThan(0);
  for (let index = 0; index < findingCount; index++) {
    const finding = findings.nth(index);
    await finding.locator("summary").click();
    await finding
      .getByLabel("Observação do fisioterapeuta")
      .fill("Revisão de QA comercial com dados fictícios; sem conclusão clínica.");
    await finding.getByRole("button", { name: "Confirmar medida" }).click();
    await expect(finding.locator("summary")).toContainText("Confirmado");
  }

  await clinicPage
    .getByLabel("Conclusão profissional", { exact: true })
    .fill("Avaliação fictícia concluída para validar o fluxo comercial do KINUA.");
  await clinicPage
    .getByRole("button", { name: "Concluir avaliação", exact: true })
    .click();
  await expect(clinicPage.locator(".assessment-heading")).toContainText(
    "Concluída",
  );

  const downloadPromise = clinicPage.waitForEvent("download");
  await clinicPage
    .getByRole("button", { name: "Baixar relatório PDF" })
    .click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toMatch(
    /^KINUA_Paciente_Comercial_Ficticio_\d+_\d{4}-\d{2}-\d{2}\.pdf$/,
  );
  const downloadedPath = await download.path();
  expect(downloadedPath).toBeTruthy();
  if (downloadedPath) {
    const bytes = readFileSync(downloadedPath);
    expect(bytes.subarray(0, 4).toString()).toBe("%PDF");
  }

  await clinicPage
    .getByRole("button", { name: "Histórico", exact: true })
    .click();
  await expect(
    clinicPage.getByRole("heading", { name: "Histórico de avaliações" }),
  ).toBeVisible();
  await expect(clinicPage.locator("table")).toContainText("Concluída");

  const dashboard = await (
    await page.request.get("/api/platform/dashboard")
  ).json();
  expect(dashboard.production_clinics).toBeGreaterThanOrEqual(1);
  expect(dashboard.active_clinics).toBeGreaterThanOrEqual(1);
  expect(dashboard.active_users).toBeGreaterThanOrEqual(1);
  expect(errors).toEqual([]);
  expect(clinicErrors).toEqual([]);
  await clinicContext.close();
});
