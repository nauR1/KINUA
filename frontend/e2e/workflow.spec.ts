import { test, expect } from "@playwright/test";

test("login, patient, real pose inference, review, history and PDF", async ({
  page,
}) => {
  test.skip(
    !process.env.E2E_PASSWORD || !process.env.E2E_IMAGE,
    "Set E2E_PASSWORD and E2E_IMAGE for real model integration.",
  );
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
  await page.getByRole("button", { name: "Pacientes", exact: true }).click();
  await page
    .getByRole("button", { name: "Cadastrar paciente", exact: true })
    .click();
  const name = "Paciente QA " + Date.now();
  await page.getByLabel("Nome completo").fill(name);
  await page.getByLabel("Data de nascimento").fill("1991-03-11");
  await page
    .getByLabel("Queixa principal")
    .fill("Teste automatizado com imagem pública de demonstração.");
  await page
    .getByRole("button", { name: "Cadastrar paciente", exact: true })
    .click();
  await expect(page.getByRole("heading", { name, exact: true })).toBeVisible();
  await page
    .getByRole("button", { name: "Avaliar paciente", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Iniciar captura", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Enquadre o corpo inteiro" }),
  ).toBeVisible();
  await page.locator("input[type=file]").setInputFiles(process.env.E2E_IMAGE!);
  await page.getByLabel("Conferi o nivelamento da câmera.").check();
  await page.getByLabel("Confirmei a vista anterior.").check();
  await page.getByRole("button", { name: "Analisar e salvar captura" }).click();
  await expect(
    page.getByRole("heading", { name: "Resultados da avaliação" }),
  ).toBeVisible({ timeout: 60000 });
  await expect(page.locator(".measure-value").first()).toBeVisible();
  await expect(page.locator(".result-image canvas")).toBeVisible();
  const findings = page.locator(".finding");
  const count = await findings.count();
  expect(count).toBeGreaterThan(0);
  for (let index = 0; index < count; index++) {
    const finding = findings.nth(index);
    await finding.locator("summary").click();
    await finding
      .getByLabel("Observação do fisioterapeuta")
      .fill("Revisão automatizada de QA, sem conclusão clínica.");
    await finding.getByRole("button", { name: "Confirmar medida" }).click();
    await expect(finding.locator("summary")).toContainText("Confirmado");
  }
  await page
    .getByLabel("Conclusão profissional", { exact: true })
    .fill("Registro de teste de engenharia. Não é avaliação clínica.");
  await page
    .getByRole("button", { name: "Concluir avaliação", exact: true })
    .click();
  await expect(page.locator(".assessment-heading")).toContainText("Concluída");
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Baixar relatório PDF" }).click();
  expect((await download).suggestedFilename()).toMatch(/avaliacao-.*\.pdf/);
  await page.getByRole("button", { name: "Histórico", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Histórico de avaliações" }),
  ).toBeVisible();
  await expect(page.locator("table")).toContainText("Concluída");
  expect(errors).toEqual([]);
});

test("responsive login does not overflow", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(
    page.getByRole("button", { name: "Entrar na plataforma" }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
});

test("camera stream, real skeleton, capture and persist", async ({ page }) => {
  test.skip(
    !process.env.E2E_CAMERA_FILE || !process.env.E2E_PASSWORD,
    "Requires explicit camera fixture and demo credentials.",
  );
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
    .getByRole("button", { name: "Iniciar captura", exact: true })
    .click();
  await page.getByRole("button", { name: "Abrir câmera", exact: true }).click();
  await expect(page.getByText("CÂMERA ATIVA", { exact: true })).toBeVisible();
  await expect
    .poll(
      async () =>
        page.locator("canvas.skeleton").evaluate((node) => {
          const c = node as HTMLCanvasElement,
            context = c.getContext("2d");
          if (!context || !c.width) return 0;
          const pixels = context.getImageData(0, 0, c.width, c.height).data;
          let count = 0;
          for (let index = 3; index < pixels.length; index += 4)
            if (pixels[index]) count++;
          return count;
        }),
      { timeout: 45000 },
    )
    .toBeGreaterThan(100);
  await page
    .getByRole("button", { name: "Capturar imagem", exact: true })
    .click();
  await expect(
    page.getByAltText("Imagem capturada para avaliação"),
  ).toBeVisible();
  expect(
    await page
      .locator("video")
      .evaluate((v) =>
        ((v as HTMLVideoElement).srcObject as MediaStream)
          .getTracks()
          .every((t) => t.readyState === "ended"),
      ),
  ).toBe(true);
  await page.getByLabel("Conferi o nivelamento da câmera.").check();
  await page.getByLabel("Confirmei a vista anterior.").check();
  await page.getByRole("button", { name: "Analisar e salvar captura" }).click();
  await expect(
    page.getByRole("heading", { name: "Resultados da avaliação" }),
  ).toBeVisible({ timeout: 60000 });
  await expect(page.locator(".measure-value").first()).toBeVisible();
});
