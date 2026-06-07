import { expect, test } from "@playwright/test";

const SECTIONS = ["synthese", "demarche", "parcours", "temps", "allers-retours", "abandons", "prediction", "business-case", "conformite", "methode"];

test.describe("rapport interactif", () => {
  test("se charge sans erreur et affiche le constat clé", async ({ page }) => {
    const errors: string[] = [];
    page.on("pageerror", (e) => errors.push(e.message));
    page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
    await page.goto("./");
    await expect(page).toHaveTitle(/Credit Process Intelligence/);
    await expect(page.locator("h1")).toContainText("99,6");
    for (const id of SECTIONS) await expect(page.locator(`#${id}`)).toHaveCount(1);
    await expect(page.locator("footer")).toContainText("Projet réalisé par Youssef Mir");
    expect(errors).toEqual([]);
  });

  test("le rejeu avance et se met en pause", async ({ page }) => {
    await page.goto("./");
    const clock = page.locator(".replay-clock");
    await expect(clock).not.toHaveText("—");
    const before = await clock.textContent();
    await page.waitForTimeout(1500);
    await expect(clock).not.toHaveText(before ?? "");
    const toggle = page.getByRole("button", { name: /Mettre en pause le rejeu/ });
    await toggle.click();
    await expect(page.getByRole("button", { name: /Lancer le rejeu|Rejouer/ })).toBeVisible();
  });

  test("la bascule de thème est mémorisée", async ({ page }) => {
    await page.goto("./");
    const html = page.locator("html");
    const initial = await html.getAttribute("data-theme");
    await page.getByRole("button", { name: /Passer au thème/ }).click();
    await expect(html).not.toHaveAttribute("data-theme", initial ?? "none");
    const chosen = await html.getAttribute("data-theme");
    await page.reload();
    await expect(html).toHaveAttribute("data-theme", chosen ?? "");
  });

  test("carte de processus, simulateur et BPMN sont interactifs", async ({ page }) => {
    await page.goto("./#parcours");
    await page.locator("#parcours").scrollIntoViewIfNeeded();
    await expect(page.locator(".react-flow__edge-path").first()).toBeVisible({ timeout: 15_000 });
    await page.getByRole("button", { name: "Performance" }).click();
    await expect(page.locator(".pm-edge-label").first()).toContainText(/h|j|min/);

    await page.locator("#business-case").scrollIntoViewIfNeeded();
    const npv = page.locator(".sim-kpis .figure-number").first();
    await expect(npv).toContainText("k€", { timeout: 15_000 });
    const before = await npv.textContent();
    const slider = page.locator("#sim-completeness-loops_avoided");
    await slider.focus();
    for (let i = 0; i < 10; i++) await slider.press("ArrowRight");
    await expect(npv).not.toHaveText(before ?? "");

    await page.locator(".bpmn-canvas").scrollIntoViewIfNeeded();
    await expect(page.locator(".bpmn-canvas svg .djs-element").first()).toBeAttached({ timeout: 15_000 });
    await page.getByRole("tab", { name: /TO-BE/ }).click();
    await expect(page.locator(".bpmn-canvas")).toContainText("pré-analyse", { timeout: 15_000 });
  });

  test("chaque graphique a sa vue tableau", async ({ page }) => {
    await page.goto("./");
    const toggle = page.getByRole("button", { name: "Voir les données" }).first();
    await toggle.scrollIntoViewIfNeeded();
    await toggle.click();
    await expect(page.locator("table.data").first()).toBeVisible();
  });

  test("pas de défilement horizontal sur mobile", async ({ browser }) => {
    const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
    await page.goto("./");
    await expect(page.locator("h1")).toBeVisible();
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow).toBeLessThanOrEqual(0);
    await page.close();
  });
});
