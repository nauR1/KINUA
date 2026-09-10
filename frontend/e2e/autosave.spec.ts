import { test, expect } from "@playwright/test";
test("protocol conclusion autosave serializes delayed responses", async ({
  page,
}) => {
  test.skip(
    process.env.E2E_ISOLATED !== "1" || !process.env.E2E_PASSWORD,
    "Isolated QA required",
  );
  page.setDefaultTimeout(15000);
  await page.goto("/");
  await page.getByLabel("E-mail", { exact: true }).fill(process.env.E2E_EMAIL!);
  await page
    .getByLabel("Senha", { exact: true })
    .fill(process.env.E2E_PASSWORD!);
  await page.getByRole("button", { name: "Entrar na plataforma" }).click();
  await page.getByRole("button", { name: "Protocolos", exact: true }).click();
  await page.getByRole("combobox", { name: /^Categoria/ }).selectOption("knee");
  await page
    .getByRole("button", { name: "Iniciar protocolo", exact: true })
    .click();
  let started: () => void = () => {};
  const first = new Promise<void>((resolve) => {
    started = resolve;
  });
  let writes = 0;
  await page.route("**/api/assessments/*", async (route) => {
    if (route.request().method() !== "PATCH") return route.continue();
    writes++;
    if (writes === 1) {
      started();
      await new Promise((r) => setTimeout(r, 1800));
    }
    await route.continue();
  });
  await page
    .getByLabel("Conclusão do protocolo", { exact: true })
    .fill("First draft");
  await first;
  await page
    .getByLabel("Conclusão do protocolo", { exact: true })
    .fill("Latest draft");
  await expect(
    page.getByRole("button", { name: "Protocolos", exact: true }),
  ).toBeEnabled({ timeout: 10000 });
  const last = await page.request.get("/api/protocols/pending");
  const id = (await last.json())[0].assessment.id;
  const result = await page.request.get("/api/assessments/" + id);
  expect((await result.json()).conclusion).toBe("Latest draft");
  expect(writes).toBe(2);
});
