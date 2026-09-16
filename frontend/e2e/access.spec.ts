import { test, expect, Page } from "@playwright/test";

test.use({ timezoneId: "America/Bahia" });

test("platform administration, trial, tenant workflow, suspension, expiry and extension", async ({
  page,
  browser,
}) => {
  test.skip(
    process.env.E2E_ISOLATED !== "1" || !process.env.E2E_PASSWORD,
    "Requires isolated QA",
  );
  test.setTimeout(150000);
  page.setDefaultTimeout(12000);
  const password = process.env.E2E_PASSWORD!;
  const suffix = Date.now();
  const clinicName = "Clínica Teste " + suffix;
  const email = "admin" + suffix + "@qa.local";
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  async function login(p: Page, mail: string) {
    p.setDefaultTimeout(12000);
    await p.context().clearCookies();
    await p.goto("/");
    await p.getByLabel("E-mail", { exact: true }).fill(mail);
    await p.getByLabel("Senha", { exact: true }).fill(password);
    await p.getByRole("button", { name: "Entrar na plataforma" }).click();
  }
  await login(page, "platform@kinua.local");
  await expect(
    page.getByRole("heading", { name: "Gestão de acessos" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Pacientes", exact: true }),
  ).toHaveCount(0);
  await page.getByRole("button", { name: "Clínicas", exact: true }).click();
  await page.getByLabel("Nome da clínica").fill(clinicName);
  await page.locator('select[name="plan_code"]').selectOption("lifetime");
  await page
    .getByRole("button", { name: "Salvar clínica", exact: true })
    .click();
  const row = page.getByRole("row").filter({ hasText: clinicName });
  await expect(row.getByText("ILIMITADO", { exact: true })).toBeVisible();
  const headers = {
    "X-Requested-With": "Biometria",
    Origin: process.env.E2E_BASE_URL!,
  };
  const clinics = await (
    await page.request.get("/api/platform/clinics")
  ).json();
  const clinic = clinics.find((c: { name: string }) => c.name === clinicName);
  await page
    .getByRole("button", { name: "Usuários e acessos", exact: true })
    .click();
  await page.getByLabel("Nome", { exact: true }).fill("Admin QA " + suffix);
  await page.getByLabel("E-mail", { exact: true }).fill(email);
  await page.getByLabel("Senha inicial").fill(password);
  await page
    .getByRole("combobox", { name: "Clínica", exact: true })
    .selectOption(clinic.id);
  await page
    .getByRole("combobox", { name: "Permissão", exact: true })
    .selectOption("admin");
  const createdUser = page.waitForResponse(
    (r) =>
      r.url().endsWith("/api/platform/users") &&
      r.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Cadastrar usuário" }).click();
  const createdUserResponse = await createdUser;
  expect(createdUserResponse.status()).toBe(201);
  expect(createdUserResponse.request().postDataJSON()).toMatchObject({
    access_starts_at: null,
    access_expires_at: null,
  });
  await expect(page.getByRole("row").filter({ hasText: email })).toBeVisible({
    timeout: 15000,
  });
  const members = await (
    await page.request.get("/api/platform/users?q=" + email)
  ).json();
  const user = members[0];

  const futureEmail = "future" + suffix + "@qa.local";
  await page.getByLabel("Nome", { exact: true }).fill("Future QA " + suffix);
  await page.getByLabel("E-mail", { exact: true }).fill(futureEmail);
  await page.getByLabel("Senha inicial").fill(password);
  await page
    .getByRole("combobox", { name: "Clínica", exact: true })
    .selectOption(clinic.id);
  await page
    .getByLabel("Início individual (vazio segue clínica)")
    .fill("2099-01-15T00:30");
  const futureCreated = page.waitForResponse(
    (r) =>
      r.url().endsWith("/api/platform/users") &&
      r.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Cadastrar usuário" }).click();
  const futureResponse = await futureCreated;
  expect(futureResponse.status()).toBe(201);
  expect(futureResponse.request().postDataJSON().access_starts_at).toBe(
    "2099-01-15T03:30:00.000Z",
  );
  const futureMembers = await (
    await page.request.get("/api/platform/users?q=" + futureEmail)
  ).json();
  const futureUser = futureMembers[0];
  const futureContext = await browser.newContext({
    baseURL: process.env.E2E_BASE_URL,
    timezoneId: "America/Bahia",
  });
  const futurePage = await futureContext.newPage();
  await login(futurePage, futureEmail);
  await expect(
    futurePage.getByRole("heading", { name: "Seu acesso ainda não iniciou" }),
  ).toBeVisible();
  expect(
    (
      await page.request.patch("/api/platform/users/" + futureUser.id, {
        headers,
        data: { access_starts_at: new Date(Date.now() - 60000).toISOString() },
      })
    ).status(),
  ).toBe(200);
  await login(futurePage, futureEmail);
  await expect(futurePage.getByRole("heading", { name: /Olá,/ })).toBeVisible();
  await futureContext.close();
  const context = await browser.newContext({
    baseURL: process.env.E2E_BASE_URL,
  });
  const clinicPage = await context.newPage();
  await login(clinicPage, email);
  await expect(clinicPage.getByRole("heading", { name: /Olá,/ })).toBeVisible();
  await clinicPage
    .getByRole("button", { name: "Configurações", exact: true })
    .click();
  await clinicPage.getByLabel("Nome", { exact: true }).fill("Profissional QA");
  await clinicPage
    .getByLabel("E-mail", { exact: true })
    .fill("physio" + suffix + "@qa.local");
  await clinicPage.getByLabel("Senha inicial").fill(password);
  await clinicPage.getByRole("button", { name: "Cadastrar usuário" }).click();
  await expect(
    clinicPage.getByRole("row").filter({ hasText: "physio" + suffix }),
  ).toBeVisible();
  const patientResponse = await clinicPage.request.post("/api/patients", {
    headers,
    data: {
      name: "Paciente Fictício Comercial " + suffix,
      birth_date: "1990-01-01",
    },
  });
  expect(patientResponse.status()).toBe(201);
  const patient = await patientResponse.json();
  const assessment = await clinicPage.request.post("/api/assessments", {
    headers,
    data: { patient_id: patient.id, kind: "postural", mode: "camera" },
  });
  expect(assessment.status()).toBe(201);
  await clinicPage.reload();
  await expect(clinicPage.getByRole("heading", { name: /Olá,/ })).toBeVisible();
  await page
    .getByRole("row")
    .filter({ hasText: email })
    .getByRole("button", { name: "Gerenciar", exact: true })
    .click();
  await page
    .getByRole("combobox", { name: "Estado", exact: true })
    .selectOption("false");
  page.once("dialog", (d) => d.accept());
  await page.getByRole("button", { name: "Salvar acesso" }).click();
  await expect(
    page
      .getByRole("row")
      .filter({ hasText: email })
      .getByText("SUSPENSO", { exact: true }),
  ).toBeVisible();
  expect((await clinicPage.request.get("/api/patients")).status()).toBe(401);
  await login(clinicPage, email);
  await expect(
    clinicPage.getByRole("heading", {
      name: "Seu acesso está temporariamente suspenso.",
    }),
  ).toBeVisible();
  expect(
    (
      await page.request.patch("/api/platform/users/" + user.id, {
        headers,
        data: { is_active: true },
      })
    ).status(),
  ).toBe(200);
  await clinicPage.getByRole("button", { name: "Voltar ao login" }).click();
  await login(clinicPage, email);
  await expect(clinicPage.getByRole("heading", { name: /Olá,/ })).toBeVisible();
  expect(
    (
      await page.request.patch("/api/platform/clinics/" + clinic.id, {
        headers,
        data: {
          plan_code: "monthly",
          access_starts_at: null,
          access_expires_at: new Date(Date.now() - 60000).toISOString(),
        },
      })
    ).status(),
  ).toBe(200);
  await clinicPage.reload();
  await expect(
    clinicPage.getByRole("heading", { name: "Seu acesso ao KINUA expirou" }),
  ).toBeVisible();
  await expect(clinicPage.getByText(patient.name)).toHaveCount(0);
  await clinicPage.screenshot({
    path: "test-results/access-expired.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Clínicas", exact: true }).click();
  await page
    .getByRole("row")
    .filter({ hasText: clinicName })
    .getByRole("button", { name: "Gerenciar clínica" })
    .click();
  await page.getByRole("button", { name: "+30 dias", exact: true }).click();
  await clinicPage.getByRole("button", { name: "Voltar ao login" }).click();
  await login(clinicPage, email);
  await expect(clinicPage.getByRole("heading", { name: /Olá,/ })).toBeVisible();
  await page.getByRole("button", { name: "Auditoria", exact: true }).click();
  await expect(
    page
      .getByRole("cell", { name: "platform.user_suspended", exact: true })
      .first(),
  ).toBeVisible();
  await page.getByRole("button", { name: "Visão geral", exact: true }).click();
  await page.screenshot({
    path: "test-results/platform-admin.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 768, height: 1024 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
  expect(errors).toEqual([]);
  await context.close();
});
