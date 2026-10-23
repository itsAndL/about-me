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
import { spawn } from "node:child_process";
import { mkdtempSync, readFileSync, writeFileSync, rmSync, existsSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const [mode, chrome, url, out, scheme = "light"] = process.argv.slice(2);
if (!["tab", "phone"].includes(mode) || !chrome || !url || !out) {
  console.error("usage: node cdp.mjs tab <chrome> <url> <out-dir> | phone <chrome> <url> <out.png> [light|dark]");
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
      msg.error ? reject(new Error(msg.error.message)) : resolve(msg.result);
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
  return new Promise((resolve, reject) => {
    ws.onopen = () => resolve({ send, once, close: () => ws.close() });
    ws.onerror = () => reject(new Error(`cannot open ${wsUrl}`));
  });
}

async function open(cdp, target) {
  await cdp.send("Page.enable");
  const loaded = cdp.once("Page.loadEventFired");
  await cdp.send("Page.navigate", { url: target });
  await loaded;
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
  const shot = await cdp.send("Page.captureScreenshot", { format: "png", captureBeyondViewport: true,
    clip: await fullPage(cdp) });
  writeFileSync(out, Buffer.from(shot.data, "base64"));
  console.log(`PASS  phone screenshot (390px, ${scheme}) → ${out}`);
  return true;
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
      return mode === "tab" ? await firstTab(cdp) : await phone(cdp);
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
