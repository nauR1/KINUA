import { test, expect } from "@playwright/test";

test("guided knee protocol, autosave, real ROM video, professional review, resume and report", async ({
  page,
}) => {
  test.skip(
    process.env.E2E_ISOLATED !== "1" ||
      !process.env.E2E_PASSWORD ||
      !process.env.E2E_CAMERA_FILE,
    "Requires explicitly isolated QA database and camera fixture.",
  );
  test.setTimeout(240000);
  page.setDefaultTimeout(15000);
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await page.getByLabel("E-mail", { exact: true }).fill(process.env.E2E_EMAIL!);
  await page
    .getByLabel("Senha", { exact: true })
    .fill(process.env.E2E_PASSWORD!);
  await page.getByRole("button", { name: "Entrar na plataforma" }).click();
  await expect(page.getByRole("heading", { name: /Olá,/ })).toBeVisible();
  const patient = await page.request.post("/api/patients", {
    headers: {
      "X-Requested-With": "Biometria",
      Origin: process.env.E2E_BASE_URL!,
    },
    data: { name: "QA Protocolos ROM " + Date.now(), birth_date: "1990-01-01" },
  });
  expect(patient.ok()).toBeTruthy();
  const p = await patient.json();
  // Refresh the catalog of patients without introducing any live-clinic data.
  await page.reload();
  await page.getByRole("button", { name: "Protocolos", exact: true }).click();
  await page.getByLabel("Paciente do protocolo").selectOption(p.id);
  await page.getByRole("combobox", { name: /^Categoria/ }).selectOption("knee");
  await page
    .getByRole("button", { name: "Iniciar protocolo", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Protocolo de joelho", exact: true }),
  ).toBeVisible();
  await page
    .getByLabel("Resultado da etapa", { exact: true })
    .fill(
      "Registro de QA: texto salvo automaticamente, sem informação clínica real.",
    );
  await expect(
    page.getByText("Alterações salvas", { exact: true }),
  ).toBeVisible();
  await page.getByLabel("Estado da etapa").selectOption("completed");
  await page.getByRole("button", { name: "Salvar etapa", exact: true }).click();
  await expect(
    page.getByText("Alterações salvas", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Protocolos", exact: true }).click();
  await page
    .getByRole("row")
    .filter({ hasText: p.name })
    .getByRole("button", { name: "Continuar", exact: true })
    .click();
  const nav = page.getByRole("navigation", { name: "Etapas do protocolo" });
  await nav.getByRole("button", { name: /Amplitude de movimento/ }).click();
  await page
    .getByRole("combobox", { name: /^Movimento ROM/ })
    .selectOption("knee_flexion");
  await page.getByRole("button", { name: "Iniciar captura da etapa" }).click();
  await page.getByLabel("Conferi a câmera fixa e nivelada.").check();
  await page.getByLabel("Confirmei o plano do movimento.").check();
  await page
    .getByRole("button", { name: "Gravar movimento", exact: true })
    .click();
  await expect(page.locator(".rom-live")).toBeVisible();
  await expect(page.locator(".rom-live strong").first()).toBeVisible({
    timeout: 45000,
  });
  await page
    .getByRole("button", { name: "Parar gravação", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Processar vídeo", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Joelho — flexão", exact: true }),
  ).toBeVisible({ timeout: 90000 });
  await expect(page.locator(".rom-summary")).toContainText(
    "Excursão observada",
  );
  await page.getByRole("button", { name: /Ver pico · frame/ }).click();
  await expect(page.locator(".phase-card")).toContainText("Frame");
  const finding = page.locator(".finding").first();
  await finding.locator("summary").click();
  await finding
    .getByRole("button", { name: "Confirmar medida", exact: true })
    .click();
  await expect(finding.locator("summary")).toContainText("Confirmado");
  await page
    .getByLabel("Conclusão profissional", { exact: true })
    .fill("Teste de integração ROM. Sem validação clínica.");
  await page
    .getByRole("button", { name: "Concluir avaliação", exact: true })
    .click();
  await expect(page.locator(".assessment-heading")).toContainText("Concluída");
  await page
    .getByRole("button", { name: "Voltar ao protocolo", exact: true })
    .click();
  await nav.getByRole("button", { name: /Amplitude de movimento/ }).click();
  await page.getByLabel("Estado da etapa").selectOption("completed");
  await page.getByRole("button", { name: "Salvar etapa", exact: true }).click();
  await expect(
    page.getByText("Alterações salvas", { exact: true }),
  ).toBeVisible();
  for (const name of [
    "Mapa da dor",
    "Avaliação postural",
    "Agachamento bilateral",
    "Agachamento unipodal",
    "Step-down",
    "Comparação direita/esquerda",
    "Testes clínicos manuais",
  ]) {
    await nav.getByRole("button", { name: new RegExp(name) }).click();
    await page
      .getByLabel("Observação / justificativa", { exact: true })
      .fill("Não realizado nesta sessão de QA; escopo restrito a ROM.");
    await page.getByLabel("Estado da etapa").selectOption("skipped");
    await page
      .getByRole("button", { name: "Salvar etapa", exact: true })
      .click();
    await expect(
      page.getByText("Alterações salvas", { exact: true }),
    ).toBeVisible();
  }
  for (const name of ["Resultados", "Revisão profissional"]) {
    await nav.getByRole("button", { name: new RegExp(name) }).click();
    await page
      .getByLabel("Resultado da etapa", { exact: true })
      .fill("Revisão de engenharia registrada; sem diagnóstico.");
    await page.getByLabel("Estado da etapa").selectOption("completed");
    await page
      .getByRole("button", { name: "Salvar etapa", exact: true })
      .click();
    await expect(
      page.getByText("Alterações salvas", { exact: true }),
    ).toBeVisible();
  }
  const download = page.waitForEvent("download");
  await page
    .getByRole("button", { name: "Baixar relatório do protocolo", exact: true })
    .click();
  expect((await download).suggestedFilename()).toMatch(/^protocolo-.*\.pdf$/);
  await nav.getByRole("button", { name: /Relatório/ }).click();
  await page
    .getByLabel("Resultado da etapa", { exact: true })
    .fill("Relatório gerado para conferência.");
  await page.getByLabel("Estado da etapa").selectOption("completed");
  await page.getByRole("button", { name: "Salvar etapa", exact: true }).click();
  await expect(
    page.getByText("Alterações salvas", { exact: true }),
  ).toBeVisible();
  await page
    .getByLabel("Conclusão do protocolo", { exact: true })
    .fill("Protocolo de QA concluído; não é avaliação clínica.");
  await page
    .getByRole("button", { name: "Concluir protocolo", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Protocolo concluído", exact: true }),
  ).toBeDisabled();
  const finalPDF = page.waitForEvent("download");
  await page
    .getByRole("button", { name: "Baixar relatório do protocolo", exact: true })
    .click();
  await (await finalPDF).saveAs("test-results/protocol-completed.pdf");
  await page.screenshot({
    path: "test-results/protocol-completed.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Histórico", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Movimento ao longo do tempo" }),
  ).toBeVisible();
  expect(errors).toEqual([]);
});
