// P1: скриншоты запусков на GitVerse (страницы публичные, вход не нужен).
//   node research/p1/gitverse_shots.mjs <run_id>:<шаг для раскрытия>:<файл> ...
// Пример:
//   node research/p1/gitverse_shots.mjs "1797577:Строгая сборка (предупреждения = ошибки):docs/p1/fail.jpg"
// puppeteer-core берётся из research/p2/tools (там он стоит для Lighthouse), браузер — системный Chrome.
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
// puppeteer-core 25 — только ES-модуль: подключаем по пути, а не через require
const entry = path.join(here, "../p2/tools/node_modules/puppeteer-core/lib/puppeteer/puppeteer-core.js");
const { default: puppeteer } = await import(pathToFileURL(entry).href);

const CHROME = process.env.CHROME || "C:/Program Files/Google/Chrome/Application/chrome.exe";
const REPO = "https://gitverse.ru/crasavella04/python-lab3/cicd";

const browser = await puppeteer.launch({ executablePath: CHROME, headless: "new",
  defaultViewport: { width: 1280, height: 900, deviceScaleFactor: 1 } });
try {
  for (const spec of process.argv.slice(2)) {
    const [run, step, out, job] = spec.split(":");
    const page = await browser.newPage();
    await page.goto(`${REPO}/${run}${job ? `?job=${job}` : ""}`, { waitUntil: "networkidle2", timeout: 60000 });
    await page.waitForFunction(() => document.querySelector("main")?.innerText.includes("Задания"), { timeout: 30000 });
    // Баннер cookies и рекламную полосу только скрываем на время снимка — согласие не нажимаем
    await page.evaluate(() => {
      for (const e of document.querySelectorAll("body *")) {
        const t = e.textContent || "";
        const pos = getComputedStyle(e).position;
        if ((pos === "fixed" || pos === "sticky") &&
            (t.includes("Использование cookies") || t.includes("Все инструменты для разработки"))) {
          e.style.display = "none";
        }
      }
    });
    if (step) {
      // Заголовок шага — элемент без детей с точным текстом; клик раскрывает журнал шага
      const handle = await page.evaluateHandle((name) =>
        [...document.querySelectorAll("main *")].find((e) => e.childElementCount === 0 && e.textContent.trim() === name), step);
      const el = handle.asElement();
      if (!el) throw new Error(`шаг «${step}» не найден на ${run}`);
      await el.click();
      await new Promise((r) => setTimeout(r, 3000));
      // Шаг — к верху окна, чтобы его журнал поместился в кадр; над ним видны 3–4 шага
      await el.evaluate((e) => e.scrollIntoView({ block: "start" }));
      await page.evaluate(() => window.scrollBy(0, -170));
      await new Promise((r) => setTimeout(r, 500));
    }
    await page.screenshot({ path: out, type: "jpeg", quality: 80 });
    console.log(`${run} → ${out}`);
    await page.close();
  }
} finally {
  await browser.close();
}
