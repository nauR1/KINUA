import { test, expect } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { randomBytes } from "node:crypto";

test("PostgreSQL demo CLI password rotation authenticates through the real frontend proxy", async ({
  page,
}) => {
  test.skip(
    process.env.E2E_ISOLATED !== "1" ||
      !process.env.E2E_DEMO_DATABASE?.startsWith("postgresql") ||
      !process.env.E2E_PLATFORM_PASSWORD,
    "Requires dedicated PostgreSQL auth QA and external credentials",
  );
  test.setTimeout(120000);
  const [a, b, c] = [0, 1, 2].map(
    () => randomBytes(24).toString("base64url") + "!$",
  );
  const email = `demo-${Date.now()}@qa.local`;
  const other = `other-${Date.now()}@qa.local`;
  const headers = {
    "X-Requested-With": "Biometria",
    Origin: process.env.E2E_BASE_URL!,
  };
  function seed(address: string, password: string, reset = false) {
    execFileSync(
      process.env.E2E_PYTHON!,
      [
        "-m",
        "app.demo_seed",
        "--email",
        address,
        ...(reset ? ["--reset"] : []),
      ],
      {
        cwd: process.env.E2E_BACKEND!,
        stdio: "pipe",
        env: {
          ...process.env,
          PYTHONUTF8: "1",
          DATABASE_URL: process.env.E2E_DEMO_DATABASE!,
          STORAGE_DIR: process.env.E2E_DEMO_STORAGE!,
          ALLOW_DEMO_SEED: "true",
          DEMO_PASSWORD: password,
        },
      },
    );
  }
  async function login(address: string, password: string) {
    return page.request.post("/api/auth/login", {
      headers,
      data: { email: address, password },
    });
  }
  seed(email, a);
  expect((await login(email, a)).status()).toBe(200);
  expect(() => seed(email, b)).toThrow();
  seed(email, b, true);
  expect((await login(email, a)).status()).toBe(401);
  expect((await login(email, b)).status()).toBe(200);
  await page.context().clearCookies();
  await page.goto("/");
  await page.getByLabel("E-mail", { exact: true }).fill(email);
  await page.getByLabel("Senha", { exact: true }).fill(b);
  await page.getByRole("button", { name: "Entrar na plataforma" }).click();
  await expect(page.getByRole("heading", { name: /Olá,/ })).toBeVisible();
  await expect(page.locator(".demo-banner")).toBeVisible();
  seed(other, c);
  expect((await login(other, c)).status()).toBe(200);
  expect(
    (await login(process.env.E2E_EMAIL!, process.env.E2E_PASSWORD!)).status(),
  ).toBe(200);
  expect(
    (
      await login("platform@qa.local", process.env.E2E_PLATFORM_PASSWORD!)
    ).status(),
  ).toBe(200);
});
