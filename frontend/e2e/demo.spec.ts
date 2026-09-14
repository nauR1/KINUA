import { test, expect, Page } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { writeFileSync } from "node:fs";
import path from "node:path";
test("isolated demo seed, visible warnings, marked PDF, commercial exclusion and safe reset", async ({
  page,
  browser,
}) => {
  test.skip(
    process.env.E2E_ISOLATED !== "1" ||
      !process.env.E2E_DEMO_DATABASE ||
      !process.env.E2E_PASSWORD,
    "Requires isolated demo QA database",
  );
  test.setTimeout(120000);
  const password = process.env.E2E_PASSWORD!;
  const headers = {
    "X-Requested-With": "Biometria",
    Origin: process.env.E2E_BASE_URL!,
  };
  const childEnv = {
    ...process.env,
    PYTHONUTF8: "1",
    DATABASE_URL: process.env.E2E_DEMO_DATABASE!,
    STORAGE_DIR: process.env.E2E_DEMO_STORAGE!,
    ALLOW_DEMO_SEED: "true",
    DEMO_PASSWORD: password,
    APP_MODE: "demo",
  };
  function seed(reset = false) {
    execFileSync(
      process.env.E2E_PYTHON!,
      [
        "-m",
        "app.demo_seed",
        "--email",
        "demo@qa.local",
        ...(reset ? ["--reset"] : []),
      ],
      { cwd: process.env.E2E_BACKEND!, env: childEnv, stdio: "pipe" },
    );
  }
  async function login(p: Page, email: string) {
    await p.context().clearCookies();
    await p.goto("/");
    await p.getByLabel("E-mail", { exact: true }).fill(email);
    await p.getByLabel("Senha", { exact: true }).fill(password);
    await p.getByRole("button", { name: "Entrar na plataforma" }).click();
  }
  await login(page, process.env.E2E_EMAIL!);
  await expect(page.getByRole("heading", { name: /Olá,/ })).toBeVisible();
  const created = await page.request.post("/api/patients", {
    headers,
    data: {
      name: "QA Produção Controlada " + Date.now(),
      birth_date: "1990-01-01",
    },
  });
  expect(created.status()).toBe(201);
  const before = await (await page.request.get("/api/patients")).json();
  const platformContext = await browser.newContext({
    baseURL: process.env.E2E_BASE_URL,
  });
  const platform = await platformContext.newPage();
  await login(platform, "platform@kinua.local");
  await expect(
    platform.getByRole("heading", { name: "Gestão de acessos" }),
  ).toBeVisible();
  const commercialBefore = await (
    await platform.request.get("/api/platform/dashboard")
  ).json();
  seed();
  const demoContext = await browser.newContext({
    baseURL: process.env.E2E_BASE_URL,
  });
  const demo = await demoContext.newPage();
  await login(demo, "demo@qa.local");
  await expect(
    demo.getByText(
      "AMBIENTE DE DEMONSTRAÇÃO — todos os dados apresentados são fictícios.",
      { exact: true },
    ),
  ).toBeVisible();
  await expect(demo.getByRole("heading", { name: /Olá,/ })).toBeVisible();
  expect((await demo.request.get("/api/platform/dashboard")).status()).toBe(
    403,
  );
  await demo.getByRole("button", { name: "Pacientes", exact: true }).click();
  await expect(
    demo.getByText("Ana Demonstração", { exact: true }).first(),
  ).toBeVisible();
  await demo
    .getByRole("button", { name: "Cadastrar paciente", exact: true })
    .click();
  await expect(
    demo.getByText(
      "Este é um ambiente de demonstração. Não insira dados reais de pacientes.",
      { exact: true },
    ),
  ).toBeVisible();
  await demo
    .getByLabel("Nome completo", { exact: true })
    .fill("Registro Sintético Cancelado");
  await demo
    .getByLabel("Data de nascimento", { exact: true })
    .fill("1990-01-01");
  const confirmation = demo.waitForEvent("dialog");
  const submission = demo
    .getByRole("button", { name: "Cadastrar paciente", exact: true })
    .click();
  const dialog = await confirmation;
  expect(dialog.message()).toContain("Não insira dados reais");
  await dialog.dismiss();
  await submission;
  const patients = await (await demo.request.get("/api/patients")).json();
  expect(patients).toHaveLength(3);
  const history = await (
    await demo.request.get(
      "/api/patients/" +
        patients.find((p: { name: string }) => p.name === "Ana Demonstração")
          .id +
        "/assessments",
    )
  ).json();
  const completed = history.find(
    (a: { status: string }) => a.status === "completed",
  );
  expect(completed).toBeTruthy();
  const started = await demo.request.post("/api/assessments", {
    headers,
    data: { patient_id: patients[0].id, kind: "postural", mode: "camera" },
  });
  expect(started.status()).toBe(201);
  const pdf = await demo.request.get(
    "/api/assessments/" + completed.id + "/report",
  );
  expect(pdf.status()).toBe(200);
  const pdfPath = path.resolve("test-results/demo-report.pdf");
  writeFileSync(pdfPath, await pdf.body());
  const marked = execFileSync(
    process.env.E2E_PYTHON!,
    [
      "-c",
      "from pypdf import PdfReader; import sys; print(all('DEMONSTRAÇÃO — DADOS FICTÍCIOS' in p.extract_text() for p in PdfReader(sys.argv[1]).pages))",
      pdfPath,
    ],
    { env: childEnv, encoding: "utf8" },
  );
  expect(marked.trim()).toBe("True");
  await demo.getByRole("button", { name: "Cancelar", exact: true }).click();
  await demo.screenshot({
    path: "test-results/demo-patients.png",
    fullPage: true,
  });
  await demo.getByRole("button", { name: "Sair", exact: true }).click();
  await platform.reload();
  await platform.getByRole("button", { name: "Clínicas", exact: true }).click();
  await platform
    .getByRole("combobox", { name: "Tipo de ambiente" })
    .selectOption("demo");
  await expect(
    platform
      .getByRole("row")
      .filter({ hasText: "KINUA — Ambiente de Demonstração" })
      .getByText("DEMO", { exact: true }),
  ).toBeVisible();
  const after = await (
    await platform.request.get("/api/platform/dashboard")
  ).json();
  for (const key of [
    "active_clinics",
    "expired_subscriptions",
    "expiring_7",
    "expiring_30",
    "active_users",
    "production_clinics",
  ]) {
    expect(after[key]).toBe(commercialBefore[key]);
  }
  expect(after.demo_clinics).toBe(Math.max(1, commercialBefore.demo_clinics));
  seed(true);
  await login(demo, "demo@qa.local");
  await expect(demo.getByRole("heading", { name: /Olá,/ })).toBeVisible();
  expect((await (await demo.request.get("/api/patients")).json()).length).toBe(
    3,
  );
  expect(await (await page.request.get("/api/patients")).json()).toEqual(
    before,
  );
  await demo.setViewportSize({ width: 768, height: 1024 });
  await expect(demo.locator(".demo-banner")).toBeVisible();
  expect(
    await demo.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
  await demoContext.close();
  await platformContext.close();
});
