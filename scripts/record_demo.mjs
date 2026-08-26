/**
 * Plan-driven recorder for the demo video.
 *
 * build_demo_video.py synthesizes the narration first and records how long each
 * line takes. This script drives the deployed console from that plan: it holds
 * each scene on screen for exactly that long, and writes back the wall-clock
 * offset at which the scene actually started, so the mix cannot drift.
 */
import { chromium } from "playwright";
import { readFileSync, writeFileSync } from "node:fs";

const PLAN = process.env.PLAN ?? "scratch/demo/plan.json";
const OUT = process.env.OUT ?? "scratch/demo/video";
const URL = process.env.DEMO_URL ?? "http://localhost:8080/";
const W = 1920, H = 1080;

const CSS = `
#dz-cap{position:fixed;left:0;right:0;bottom:0;z-index:2147483647;
  font:600 30px/1.35 Inter,system-ui,-apple-system,Segoe UI,Roboto,sans-serif;
  color:#fff;padding:26px 56px 34px;text-align:center;
  background:linear-gradient(to top,rgba(2,6,23,.94) 0%,rgba(2,6,23,.80) 55%,rgba(2,6,23,0) 100%);
  text-shadow:0 2px 12px rgba(0,0,0,.9);opacity:0;transition:opacity .35s ease;
  letter-spacing:.2px;pointer-events:none}
#dz-cap.on{opacity:1}
#dz-cap b{color:#22d3ee}
#dz-card{position:fixed;inset:0;z-index:2147483646;display:flex;flex-direction:column;
  align-items:center;justify-content:center;gap:22px;background:#020617;
  font-family:Inter,system-ui,-apple-system,Segoe UI,Roboto,sans-serif;color:#e2e8f0;
  opacity:0;transition:opacity .5s ease;pointer-events:none}
#dz-card.on{opacity:1}
#dz-card .t{font-size:76px;font-weight:800;letter-spacing:-1.5px}
#dz-card .t span{color:#22d3ee}
#dz-card .s{font-size:31px;color:#94a3b8;font-weight:500;max-width:1180px;text-align:center;line-height:1.4}
#dz-card .k{font-size:22px;color:#64748b;letter-spacing:3px;text-transform:uppercase;font-weight:700}
#dz-ring{position:fixed;z-index:2147483645;border:4px solid #22d3ee;border-radius:14px;
  box-shadow:0 0 0 5px rgba(34,211,238,.22),0 0 34px rgba(34,211,238,.6);
  opacity:0;transition:all .38s cubic-bezier(.4,0,.2,1);pointer-events:none}
#dz-ring.on{opacity:1}
`;

const INSTALL = () => {
  if (document.getElementById("dz-cap")) return;
  const s = document.createElement("style");
  s.textContent = window.__DZ_CSS;
  document.head.appendChild(s);
  for (const [id, html] of [
    ["dz-cap", ""],
    ["dz-card", '<div class="k"></div><div class="t"></div><div class="s"></div>'],
    ["dz-ring", ""],
  ]) {
    const el = document.createElement("div");
    el.id = id;
    el.innerHTML = html;
    document.body.appendChild(el);
  }
};

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const cap = (page, html) =>
  page.evaluate((h) => {
    const c = document.getElementById("dz-cap");
    if (!c) return;
    if (!h) { c.classList.remove("on"); return; }
    c.innerHTML = h;
    c.classList.add("on");
  }, html);

const card = (page, on, k = "", t = "", s = "") =>
  page.evaluate(([on, k, t, s]) => {
    const c = document.getElementById("dz-card");
    if (!c) return;
    if (on) {
      c.querySelector(".k").textContent = k;
      c.querySelector(".t").innerHTML = t;
      c.querySelector(".s").innerHTML = s;
      c.classList.add("on");
    } else c.classList.remove("on");
  }, [on, k, t, s]);

const ring = async (page, selector) => {
  await page.evaluate((sel) => {
    const r = document.getElementById("dz-ring");
    const t = document.querySelector(sel);
    if (!r || !t) return;
    const b = t.getBoundingClientRect();
    Object.assign(r.style, {
      left: `${b.left - 8}px`, top: `${b.top - 8}px`,
      width: `${b.width + 16}px`, height: `${b.height + 16}px`,
    });
    r.classList.add("on");
  }, selector);
};
const ringOff = (page) =>
  page.evaluate(() => document.getElementById("dz-ring")?.classList.remove("on"));

const glide = (page, selector, block = "start") =>
  page.evaluate(([sel, b]) => {
    document.querySelector(sel)?.scrollIntoView({ behavior: "smooth", block: b });
  }, [selector, block]);

/** Scrolls the trace so the newest streamed step stays in frame. */
const followTrace = (page) =>
  page.evaluate(() => {
    const cards = document.querySelectorAll("main [class*='rounded'] , main li, main article");
    const last = cards[cards.length - 1];
    last?.scrollIntoView({ behavior: "smooth", block: "center" });
  });

(async () => {
  const plan = JSON.parse(readFileSync(PLAN, "utf8"));
  const browser = await chromium.launch({ args: ["--force-color-profile=srgb"] });
  // The video's first frame lands when the page is created; the scene clock only
  // starts once the console has loaded. Measure the gap so the mix can undo it.
  const tCtx = Date.now();
  const ctx = await browser.newContext({
    viewport: { width: W, height: H },
    recordVideo: { dir: OUT, size: { width: W, height: H } },
    deviceScaleFactor: 1,
    colorScheme: "dark",
  });
  const page = await ctx.newPage();
  await page.addInitScript((css) => { window.__DZ_CSS = css; }, CSS);
  await page.goto(URL, { waitUntil: "networkidle", timeout: 120000 });
  await page.evaluate((css) => { window.__DZ_CSS = css; }, CSS);
  await page.evaluate(INSTALL);
  await sleep(1200);

  const t0 = Date.now();
  const mark = () => (Date.now() - t0) / 1000;
  const videoOffset = Number(((t0 - tCtx) / 1000).toFixed(3));
  console.log("video offset", videoOffset, "s");
  for (const scene of plan) scene.video_offset_seconds = videoOffset;

  // The agent runs once, streaming for ~90s; the trace scenes narrate it live.
  let started = false;

  for (const scene of plan) {
    scene.actual_start_seconds = Number(mark().toFixed(3));
    const hold = scene.hold_seconds * 1000;
    console.log(`[${String(scene.index).padStart(2, "0")}] ${scene.id} @${scene.actual_start_seconds}s hold ${scene.hold_seconds}s`);

    switch (scene.action) {
      case "title_card":
        await card(page, true, "Agentic Cinema · Grafana Labs Track",
          "CineOps <span>Guardian</span>",
          "Autonomous observability and incident recovery for virtual production LED volumes and robotic camera fleets");
        await sleep(hold);
        await card(page, false);
        break;

      case "show_header":
        await cap(page, scene.caption);
        await ring(page, "header");
        await sleep(hold);
        await ringOff(page);
        break;

      case "show_metrics":
        await cap(page, scene.caption);
        await glide(page, "main", "start");
        await sleep(hold);
        break;

      case "rerun_agent": {
        await cap(page, scene.caption);
        const reset = page.getByRole("button", { name: /Reset Demo/i });
        if (await reset.count()) { await reset.first().click(); await sleep(1500); }
        const rerun = page.getByRole("button", { name: /Re-Run Agent|Agent Investigating/i });
        if (await rerun.count()) { await rerun.first().click(); started = true; }
        await sleep(Math.max(hold - 1500, 500));
        break;
      }

      case "follow_trace":
        await cap(page, scene.caption);
        await followTrace(page);
        await sleep(hold);
        break;

      case "show_hypotheses": {
        await cap(page, scene.caption);
        if (started) {
          for (let i = 0; i < 60; i++) {
            const busy = await page.getByRole("button", { name: /Agent Investigating/i }).count();
            if (!busy) break;
            await sleep(500);
          }
        }
        await glide(page, "h3", "start");
        await sleep(hold);
        break;
      }

      case "open_gate": {
        await cap(page, scene.caption);
        const authorize = page.getByRole("button", { name: /Review & Authorize Action/i }).first();
        await glide(page, "main", "center");
        if (await authorize.count()) { await authorize.click(); await sleep(1200); }
        const nameBox = page.locator('input[type="text"]').last();
        if (await nameBox.count()) {
          await nameBox.click();
          await nameBox.pressSequentially("S. KWON / STAGE-A LEAD", { delay: 50 });
        }
        const chk = page.locator('input[type="checkbox"]').last();
        if (await chk.count()) await chk.check();
        await sleep(Math.max(hold - 3500, 500));
        break;
      }

      case "authorize": {
        await cap(page, scene.caption);
        const exec = page.getByRole("button", {
          name: /Authorize & Execute Recovery|Executing Recovery/i,
        }).first();
        if (await exec.count()) await exec.click();
        await sleep(2500);
        await page.evaluate(() => window.scrollTo({ top: 0, behavior: "smooth" }));
        await sleep(Math.max(hold - 2500, 500));
        break;
      }

      case "close_card":
        await cap(page, "");
        await card(page, true, "Open source · Apache-2.0",
          "From alert to <span>verified recovery</span>",
          "Two MCP servers · Grafana MCP · Loki · Foxglove Data Platform · ROS2 MCAP · Gemini 3.7 Flash on Vertex AI · BigQuery · Firestore");
        await sleep(hold);
        break;

      default:
        await cap(page, scene.caption);
        await sleep(hold);
    }
    if (scene.action !== "close_card" && scene.action !== "title_card") await cap(page, "");
    await sleep(150);
  }

  console.log("total", mark().toFixed(2), "s");
  writeFileSync(PLAN, JSON.stringify(plan, null, 1));
  const video = page.video();
  await page.close();
  await ctx.close();
  await browser.close();
  console.log("VIDEO", await video.path());
  console.log("DONE");
})().catch((e) => { console.error("ERR", e); process.exit(1); });
