// Drive headless Chrome over the DevTools protocol for the checks the plain
// `--screenshot` / `--dump-dom` flags cannot do.
//
// Usage:
//   node cdp.mjs tab   <chrome> <url> <out-dir>
//     Press a real Tab key once; write keyboard-first-tab.{png,json}. Exits 0 only
//     when focus lands on a visible "Skip to content" link pointing at #main.
//   node cdp.mjs phone <chrome> <url> <out.png> [light|dark]
//     Emulate a 390px-wide phone viewport (headless windows cannot go below ~500px)
//     and save a full-page screenshot.
//   node cdp.mjs theme <chrome> <url> <out-dir>
//     Drive the theme toggle (features/theme.md): click it, reload, check data-theme,
//     aria-pressed and localStorage, the 390px scroll width, hydration warnings and a
//     JS-off load. Writes theme-check.json and theme-*.png.
import { spawn } from "node:child_process";
import { mkdtempSync, readFileSync, writeFileSync, rmSync, existsSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const [mode, chrome, url, out, scheme = "light"] = process.argv.slice(2);
if (!["tab", "phone", "theme"].includes(mode) || !chrome || !url || !out) {
  console.error("usage: node cdp.mjs tab|theme <chrome> <url> <out-dir> | phone <chrome> <url> <out.png> [light|dark]");
  process.exit(2);
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const profile = mkdtempSync(join(tmpdir(), "verify-app-chrome-"));
const proc = spawn(chrome, [
  "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
  "--remote-debugging-port=0", `--user-data-dir=${profile}`,
  "--window-size=1280,800", "about:blank",
], { stdio: "ignore" });

async function devtoolsPort() {
  const file = join(profile, "DevToolsActivePort");
  for (let i = 0; i < 100; i++) {
    if (existsSync(file)) {
      const port = readFileSync(file, "utf8").split("\n")[0];
      if (port) return port;
    }
    await sleep(100);
  }
  throw new Error("Chrome never wrote DevToolsActivePort");
}

function connect(wsUrl) {
  const ws = new WebSocket(wsUrl);
  let id = 0;
  const pending = new Map();
  const waiters = [];
  ws.onmessage = ({ data }) => {
    const msg = JSON.parse(data);
    if (msg.id && pending.has(msg.id)) {
      const { resolve, reject } = pending.get(msg.id);
      pending.delete(msg.id);
      if (msg.error) reject(new Error(msg.error.message));
      else resolve(msg.result);
    } else if (msg.method) {
      for (const w of waiters.filter((w) => w.method === msg.method)) {
        waiters.splice(waiters.indexOf(w), 1);
        w.resolve(msg.params);
      }
    }
  };
  const send = (method, params = {}) => new Promise((resolve, reject) => {
    pending.set(++id, { resolve, reject });
    ws.send(JSON.stringify({ id, method, params }));
  });
  const once = (method) => new Promise((resolve) => waiters.push({ method, resolve }));
  const events = [];
  const record = ws.onmessage;
  ws.onmessage = (e) => {
    const msg = JSON.parse(e.data);
    if (["Runtime.consoleAPICalled", "Runtime.exceptionThrown", "Log.entryAdded"].includes(msg.method)) events.push(msg);
    record(e);
  };
  return new Promise((resolve, reject) => {
    ws.onopen = () => resolve({ send, once, events, close: () => ws.close() });
    ws.onerror = () => reject(new Error(`cannot open ${wsUrl}`));
  });
}

async function open(cdp, target) {
  await cdp.send("Page.enable");
  const loaded = cdp.once("Page.loadEventFired");
  await cdp.send("Page.navigate", { url: target });
  await loaded;
}

const evaluate = async (cdp, expression) =>
  (await cdp.send("Runtime.evaluate", { returnByValue: true, expression })).result.value;

// The theme toggle renders hidden until React hydrates; wait for it (or give up after 5s).
async function hydrated(cdp) {
  for (let i = 0; i < 50; i++) {
    if (await evaluate(cdp, `!!document.querySelector(".theme-toggle:not([hidden])")`)) return true;
    await sleep(100);
  }
  return false;
}

async function firstTab(cdp) {
  await open(cdp, url);
  for (const type of ["keyDown", "keyUp"]) {
    await cdp.send("Input.dispatchKeyEvent", {
      type, key: "Tab", code: "Tab", windowsVirtualKeyCode: 9, nativeVirtualKeyCode: 9,
    });
  }
  const { result } = await cdp.send("Runtime.evaluate", {
    returnByValue: true,
    expression: `(() => {
      const el = document.activeElement;
      const r = el.getBoundingClientRect();
      return { tag: el.tagName, text: el.textContent.trim(), href: el.getAttribute("href"),
               className: el.className, width: r.width, height: r.height };
    })()`,
  });
  const focused = result.value;
  const pass = focused.tag === "A" && focused.text === "Skip to content" && focused.href === "#main"
    && focused.width > 1 && focused.height > 1;
  const shot = await cdp.send("Page.captureScreenshot", { format: "png" });
  writeFileSync(join(out, "keyboard-first-tab.png"), Buffer.from(shot.data, "base64"));
  writeFileSync(join(out, "keyboard-first-tab.json"), JSON.stringify({ action: "first Tab", focused, pass }, null, 2));
  console.log(`${pass ? "PASS" : "FAIL"}  first Tab focuses ${JSON.stringify(focused)}`);
  return pass;
}

async function phone(cdp) {
  await cdp.send("Emulation.setDeviceMetricsOverride", { width: 390, height: 844, deviceScaleFactor: 1, mobile: true });
  await cdp.send("Emulation.setEmulatedMedia", { features: [{ name: "prefers-color-scheme", value: scheme }] });
  await open(cdp, url);
  await hydrated(cdp);
  const shot = await cdp.send("Page.captureScreenshot", { format: "png", captureBeyondViewport: true,
    clip: await fullPage(cdp) });
  writeFileSync(out, Buffer.from(shot.data, "base64"));
  console.log(`PASS  phone screenshot (390px, ${scheme}) → ${out}`);
  return true;
}

async function theme(cdp) {
  const results = [];
  const check = (name, pass, detail) => {
    results.push({ name, pass, detail });
    console.log(`${pass ? "PASS" : "FAIL"}  ${name} ${JSON.stringify(detail)}`);
  };
  const state = () => evaluate(cdp, `(() => {
    const b = document.querySelector(".theme-toggle");
    let stored = null;
    try { stored = localStorage.getItem("theme"); } catch {}
    return { dataTheme: document.documentElement.dataset.theme ?? null, stored,
             ariaPressed: b && b.getAttribute("aria-pressed"), name: b && b.getAttribute("aria-label"),
             hidden: !b || b.hidden || b.getBoundingClientRect().width === 0,
             bg: getComputedStyle(document.body).backgroundColor };
  })()`);
  const shot = async (name) => {
    const { data } = await cdp.send("Page.captureScreenshot", { format: "png" });
    writeFileSync(join(out, name), Buffer.from(data, "base64"));
  };

  await cdp.send("Runtime.enable");
  await cdp.send("Log.enable");
  await cdp.send("Emulation.setEmulatedMedia", { features: [{ name: "prefers-color-scheme", value: "light" }] });
  await open(cdp, url);
  await evaluate(cdp, `localStorage.removeItem("theme")`);
  await open(cdp, url);
  check("toggle visible once hydrated", await hydrated(cdp), {});
  const before = await state();
  check("system light: no data-theme, aria-pressed=false", before.dataTheme === null && before.ariaPressed === "false", before);

  // A real mouse click at the button's centre.
  const box = await evaluate(cdp, `(() => { const r = document.querySelector(".theme-toggle").getBoundingClientRect();
    return { x: r.x + r.width / 2, y: r.y + r.height / 2 }; })()`);
  for (const type of ["mousePressed", "mouseReleased"]) {
    await cdp.send("Input.dispatchMouseEvent", { type, x: box.x, y: box.y, button: "left", clickCount: 1 });
  }
  await sleep(200);
  const clicked = await state();
  check("click → data-theme=dark, aria-pressed=true, localStorage.theme=dark",
    clicked.dataTheme === "dark" && clicked.ariaPressed === "true" && clicked.stored === "dark", clicked);
  await shot("theme-after-click.png");

  // Reload with Next's JS bundles blocked (CSS still loads): only the inline <head> script can
  // set the theme, so this proves it is applied before React (and its useLayoutEffect) runs.
  await cdp.send("Network.enable");
  await cdp.send("Network.setBlockedURLs", { urls: ["*/_next/static/*.js*"] });
  await open(cdp, url);
  const headOnly = await state();
  check("head script alone sets data-theme=dark and the dark background (bundles blocked)",
    headOnly.dataTheme === "dark" && headOnly.bg === "rgb(17, 19, 18)", headOnly);
  await cdp.send("Network.setBlockedURLs", { urls: [] });

  cdp.events.length = 0;
  await open(cdp, url);
  await hydrated(cdp);
  const reloaded = await state();
  check("reload keeps data-theme=dark with aria-pressed=true",
    reloaded.dataTheme === "dark" && reloaded.ariaPressed === "true", reloaded);
  await shot("theme-after-reload.png");
  const texts = cdp.events.map((e) => e.params.entry?.text
    ?? e.params.exceptionDetails?.exception?.description ?? e.params.exceptionDetails?.text
    ?? (e.params.args || []).map((a) => a.value ?? a.description ?? "").join(" "));
  // Production React reports hydration mismatches as minified errors #418, #419, #423-#425.
  const hydration = texts.filter((t) => /hydrat|#41[89]\b|#42[3-5]\b/i.test(t));
  check("no hydration warnings in the console", hydration.length === 0, { console: texts });

  await cdp.send("Emulation.setDeviceMetricsOverride", { width: 390, height: 844, deviceScaleFactor: 1, mobile: true });
  await open(cdp, url);
  await hydrated(cdp);
  const scrollWidth = await evaluate(cdp, `document.documentElement.scrollWidth`);
  check("390px: scrollWidth <= 390", scrollWidth <= 390, { scrollWidth });
  await cdp.send("Emulation.clearDeviceMetricsOverride");
  await evaluate(cdp, `localStorage.removeItem("theme")`);

  // JS off: the page must render in full, follow the system theme and show no toggle.
  await cdp.send("Emulation.setScriptExecutionDisabled", { value: true });
  for (const scheme of ["light", "dark"]) {
    await cdp.send("Emulation.setEmulatedMedia", { features: [{ name: "prefers-color-scheme", value: scheme }] });
    await open(cdp, url);
    const s = await state();
    const projects = await evaluate(cdp, `document.querySelectorAll(".project").length`);
    const want = scheme === "dark" ? "rgb(17, 19, 18)" : "rgb(251, 250, 247)";
    check(`JS off, system ${scheme}: full page, ${want} background, toggle hidden`,
      projects === 4 && s.bg === want && s.hidden, { projects, ...s });
    await shot(`theme-js-off-${scheme}.png`);
  }
  await cdp.send("Emulation.setScriptExecutionDisabled", { value: false });

  const pass = results.every((r) => r.pass);
  writeFileSync(join(out, "theme-check.json"), JSON.stringify({ pass, results }, null, 2));
  return pass;
}

async function fullPage(cdp) {
  const { cssContentSize } = await cdp.send("Page.getLayoutMetrics");
  return { x: 0, y: 0, width: 390, height: Math.ceil(cssContentSize.height), scale: 1 };
}

const TIMEOUT_MS = 30000;
let ok = false;
try {
  if (typeof WebSocket !== "function") throw new Error("needs node 22+ (global WebSocket)");
  const run = async () => {
    const port = await devtoolsPort();
    const targets = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
    const cdp = await connect(targets.find((t) => t.type === "page").webSocketDebuggerUrl);
    try {
      return mode === "tab" ? await firstTab(cdp) : mode === "theme" ? await theme(cdp) : await phone(cdp);
    } finally {
      cdp.close();
    }
  };
  const timeout = new Promise((_, reject) =>
    setTimeout(() => reject(new Error(`timed out after ${TIMEOUT_MS / 1000}s`)), TIMEOUT_MS).unref());
  ok = await Promise.race([run(), timeout]);
} catch (err) {
  console.log(`FAIL  cdp ${mode}: ${err.message}`);
} finally {
  proc.kill();
  await sleep(300);
  rmSync(profile, { recursive: true, force: true });
}
process.exit(ok ? 0 : 1);
