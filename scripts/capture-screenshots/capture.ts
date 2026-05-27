// Playwright capture script for soap-journal documentation screenshots.
//
// Flow:
//   1. Visit the login page on a fresh instance → install-login-page.png
//   2. Click Register, fill in alice/password123 (DON'T SUBMIT yet)
//      → install-register-tab.png
//   3. Submit → install-dashboard-first-time.png (empty dashboard)
//   4. Seed bob + a bunch of entries via the API using the live session
//      cookie from the browser.
//   5. Reload and walk through every other screen, taking shots.
//   6. Switch to a phone viewport and grab mobile-* shots.
//
// Prerequisites: a fresh soap-journal instance running on BASE_URL with
// an empty database. Reset with:
//   docker compose down -v && docker compose up -d
// then wait for `docker compose ps` to show "(healthy)".
//
// Usage:
//   npx playwright install chromium
//   BASE_URL=http://localhost:8080 npx tsx capture.ts

import {
  chromium,
  request as playwrightRequest,
  type APIRequestContext,
  type Page,
} from "@playwright/test";
import { mkdir } from "node:fs/promises";
import * as path from "node:path";
import { fileURLToPath } from "node:url";

import {
  ADMIN,
  SECOND_USER,
  buildAdminEntries,
  type EntryDraft,
} from "./seed.js";

const BASE_URL = process.env.BASE_URL ?? "http://localhost:8080";
const HERE = path.dirname(fileURLToPath(import.meta.url));
const OUT_DIR = path.resolve(HERE, "..", "..", "docs", "screenshots");

const DESKTOP_VIEWPORT = { width: 1280, height: 800 };
const MOBILE_VIEWPORT = { width: 390, height: 844 };

const captured: string[] = [];

async function shot(page: Page, name: string, opts: { fullPage?: boolean } = {}): Promise<void> {
  const file = path.join(OUT_DIR, `${name}.png`);
  await page.screenshot({ path: file, fullPage: opts.fullPage ?? false });
  captured.push(name);
  console.log(`  captured ${name}.png`);
}

async function seedViaBrowser(
  request: APIRequestContext,
  entries: EntryDraft[],
): Promise<void> {
  // Create bob via the admin route (open registration stays off the way it
  // ships). The browser context is already logged in as alice (admin), so
  // its cookies authorize this request automatically.
  const createBob = await request.post(`${BASE_URL}/api/v1/admin/users`, {
    data: {
      username: SECOND_USER.username,
      password: SECOND_USER.password,
      is_admin: false,
    },
  });
  if (createBob.status() !== 201) {
    throw new Error(`create bob: HTTP ${createBob.status()}: ${await createBob.text()}`);
  }

  for (const draft of entries) {
    const res = await request.post(`${BASE_URL}/api/v1/entries`, {
      data: { ...draft, translation_code: "BSB" },
    });
    if (res.status() !== 201) {
      throw new Error(
        `create entry "${draft.scripture_ref}": HTTP ${res.status()}: ${await res.text()}`,
      );
    }
  }

  // Log bob in with a separate request context so alice's session in
  // the main browser is left untouched, then create one entry as bob.
  const bobCtx = await playwrightRequest.newContext({ baseURL: BASE_URL });
  try {
    const bobLogin = await bobCtx.post(`/api/v1/auth/login`, { data: SECOND_USER });
    if (bobLogin.status() !== 200) {
      throw new Error(`bob login: HTTP ${bobLogin.status()}: ${await bobLogin.text()}`);
    }
    const bobEntry = await bobCtx.post(`/api/v1/entries`, {
      data: {
        title: undefined,
        entry_date: new Date().toISOString().slice(0, 10),
        scripture_ref: "Psalm 1:1-3",
        translation_code: "BSB",
        observation:
          "The blessed one delights in the law of the Lord and meditates on it day and night.",
        application: "I will pick one verse to chew on through the day.",
        prayer: "Plant me by Your stream, Lord.",
        tags: ["meditation"],
      },
    });
    if (bobEntry.status() !== 201) {
      throw new Error(`bob entry: HTTP ${bobEntry.status()}: ${await bobEntry.text()}`);
    }
  } finally {
    await bobCtx.dispose();
  }
}

async function gotoAndSettle(page: Page, url: string): Promise<void> {
  await page.goto(url, { waitUntil: "networkidle" });
}

async function ensureLightTheme(page: Page): Promise<void> {
  // The theme toggle persists to localStorage; if a previous run left it
  // dark, force-light before any screenshot.
  await page.evaluate(() => {
    document.documentElement.classList.remove("dark");
    try {
      localStorage.setItem("theme", "light");
    } catch {
      /* localStorage may be unavailable */
    }
  });
}

async function captureInstallAndAdminFlow(): Promise<void> {
  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: DESKTOP_VIEWPORT,
    baseURL: BASE_URL,
    colorScheme: "light",
  });
  const page = await context.newPage();

  // ---- install path -----------------------------------------------------

  console.log("desktop: install flow");
  await gotoAndSettle(page, "/login");
  await ensureLightTheme(page);
  await page.waitForSelector("text=soap-journal");
  await shot(page, "install-login-page");

  // Switch to the Register tab. The tab buttons render as <button> with
  // exact text "Log in" / "Register" — first match is the tab; the
  // submit button below also reads "Register" once the mode switches.
  await page.getByRole("button", { name: "Register", exact: true }).first().click();
  await page.locator("#username").fill(ADMIN.username);
  await page.locator("#password").fill(ADMIN.password);
  // Park the mouse away from the tabs so the hover state on "Log in"
  // doesn't bleed into the screenshot and confuse readers about which
  // tab is selected.
  await page.mouse.move(0, 0);
  await shot(page, "install-register-tab");

  // Submit the form. The submit button shares text "Register" with the
  // tab — narrow with type=submit.
  await Promise.all([
    page.waitForURL("**/", { waitUntil: "networkidle" }),
    page.locator("button[type=submit]").click(),
  ]);
  await page.waitForSelector(`text=Welcome, ${ADMIN.username}.`);
  // Wait for both "Recent entries" and "On this day" panels to resolve
  // from skeleton to empty state — otherwise the screenshot catches the
  // loading shimmer instead of the friendly empty message.
  await page.getByTestId("dash-recent-empty").waitFor({ state: "visible" });
  await page.getByTestId("dash-onthisday-empty").waitFor({ state: "visible" });
  await page.mouse.move(0, 0);
  await shot(page, "install-dashboard-first-time");

  // ---- seed data via the live browser session --------------------------

  console.log("seeding data via API (alice session)");
  await seedViaBrowser(context.request, buildAdminEntries());

  // ---- usage path -------------------------------------------------------

  console.log("desktop: usage flow");

  // Dashboard populated — recent entries + "on this day"
  await gotoAndSettle(page, "/");
  await page.waitForSelector("text=Recent entries");
  // Give react-query a tick to settle.
  await page.waitForLoadState("networkidle");
  await shot(page, "usage-dashboard-populated", { fullPage: true });
  // The "on this day" panel is part of the dashboard; capture a viewport
  // shot framed around that region too for chapter 07.
  await shot(page, "usage-on-this-day", { fullPage: true });

  // Reader — John 3 BSB
  await gotoAndSettle(page, "/read/BSB/John/3");
  await page.waitForSelector("text=John 3");
  // Wait for verses to render
  await page.waitForFunction(() => {
    return document.body.textContent?.includes("For God so loved the world") ?? false;
  });
  await shot(page, "usage-reader-john-3");

  // Reader settings popover
  await page.getByRole("button", { name: "Reader settings" }).click();
  await page.waitForSelector('text=Font size');
  await shot(page, "usage-reader-settings");
  // Close popover
  await page.keyboard.press("Escape");

  // Jump bar → John 3:16-20 (will highlight verses for a few seconds)
  const jumpInput = page.getByLabel("Jump to reference").first();
  await jumpInput.fill("John 3:16-20");
  await Promise.all([
    page.waitForLoadState("networkidle"),
    page.getByRole("button", { name: "Go", exact: true }).first().click(),
  ]);
  // The highlight class shows immediately; grab the shot before it fades.
  await page.waitForTimeout(150);
  await shot(page, "usage-jump-bar-result");

  // Entry form from verse click — back to John 3, click verse 16.
  await gotoAndSettle(page, "/read/BSB/John/3");
  await page.waitForFunction(() => {
    return document.body.textContent?.includes("For God so loved the world") ?? false;
  });
  // Verses are clickable; the simplest target is the verse number "16".
  // Each verse has a clickable wrapper; the verse number text is the
  // most-unique label.
  await Promise.all([
    page.waitForURL("**/entries/new", { waitUntil: "networkidle" }),
    page.getByTestId("verse-16").first().click(),
  ]);
  await page.waitForSelector("#entry-ref");
  await shot(page, "usage-entry-form-from-verse", { fullPage: true });

  // Entry form with tags + autocomplete open. The TagInput is a search
  // field with id "entry-tags-input" (or similar). Type a single
  // character that matches existing tags to trigger autocomplete.
  await page.locator("#entry-observation").fill(
    "Sample observation for the screenshot.",
  );
  await page.locator("#entry-application").fill(
    "Sample application for the screenshot.",
  );
  await page.locator("#entry-prayer").fill(
    "Sample prayer for the screenshot.",
  );

  const tagInput = page.getByLabel("Tags");
  // Add a couple confirmed tags
  await tagInput.fill("love");
  await page.keyboard.press("Enter");
  await tagInput.fill("grace");
  await page.keyboard.press("Enter");
  // Then start typing a partial to open autocomplete
  await tagInput.fill("ho");
  await page.waitForTimeout(300);
  await shot(page, "usage-tag-autocomplete", { fullPage: true });
  // And the full form view
  await page.keyboard.press("Enter");
  await tagInput.fill("");
  await page.waitForTimeout(150);
  await shot(page, "usage-entry-form-with-tags", { fullPage: true });

  // Don't actually save the test entry — cancel back out.
  await gotoAndSettle(page, "/entries");

  // Entries list
  await page.waitForSelector("text=Your entries");
  await page.waitForLoadState("networkidle");
  await shot(page, "usage-entries-list", { fullPage: true });

  // Entries list with a filter applied (filter by tag "love")
  await gotoAndSettle(page, "/entries?tag=love");
  await page.waitForLoadState("networkidle");
  await shot(page, "usage-entries-filtered", { fullPage: true });

  // Entry detail — pick the first entry link
  await gotoAndSettle(page, "/entries");
  await page.waitForLoadState("networkidle");
  const firstEntry = page.locator("a[href^='/entries/']").filter({
    hasNotText: "+ New entry",
  }).first();
  await Promise.all([
    page.waitForURL("**/entries/*", { waitUntil: "networkidle" }),
    firstEntry.click(),
  ]);
  await page.waitForSelector("h1");
  await shot(page, "usage-entry-detail", { fullPage: true });

  // Calendar
  await gotoAndSettle(page, "/calendar");
  await page.waitForSelector("text=Calendar");
  await page.waitForLoadState("networkidle");
  await shot(page, "usage-calendar", { fullPage: true });

  // Admin users
  await gotoAndSettle(page, "/admin/users");
  await page.waitForSelector("text=Admin");
  await page.waitForLoadState("networkidle");
  await shot(page, "usage-admin-users", { fullPage: true });

  // Admin create-user dialog
  await page.getByRole("button", { name: "New user" }).click();
  await page.waitForSelector("[data-testid='create-user-dialog']");
  await page.locator("#new-user-username").fill("charlie");
  await page.locator("#new-user-password").fill("an-example-password");
  await shot(page, "usage-admin-create-user", { fullPage: true });
  // Close dialog without creating
  await page.getByRole("button", { name: "Cancel" }).click();

  // Admin settings
  await gotoAndSettle(page, "/admin/settings");
  await page.waitForLoadState("networkidle");
  await shot(page, "usage-admin-settings", { fullPage: true });

  await context.close();
  await browser.close();
}

async function captureMobile(): Promise<void> {
  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: MOBILE_VIEWPORT,
    baseURL: BASE_URL,
    colorScheme: "light",
    deviceScaleFactor: 2,
    isMobile: true,
    hasTouch: true,
    userAgent:
      "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
  });
  const page = await context.newPage();

  console.log("mobile: capturing");

  // Login screen on mobile
  await gotoAndSettle(page, "/login");
  await ensureLightTheme(page);
  await page.waitForSelector("text=soap-journal");
  await shot(page, "mobile-login");

  // Log in as alice (the install flow already created her in the previous
  // browser; the API call works fine across browser contexts).
  await page.locator("#username").fill(ADMIN.username);
  await page.locator("#password").fill(ADMIN.password);
  await Promise.all([
    page.waitForURL("**/", { waitUntil: "networkidle" }),
    page.locator("button[type=submit]").click(),
  ]);
  await page.waitForSelector(`text=Welcome, ${ADMIN.username}.`);
  await shot(page, "mobile-dashboard");

  // Reader
  await gotoAndSettle(page, "/read/BSB/John/3");
  await page.waitForFunction(() => {
    return document.body.textContent?.includes("For God so loved the world") ?? false;
  });
  await shot(page, "mobile-reader");

  // Entry form (start from "+ New entry")
  await gotoAndSettle(page, "/entries/new");
  await page.waitForSelector("#entry-ref");
  await shot(page, "mobile-entry-form");

  await context.close();
  await browser.close();
}

async function main(): Promise<void> {
  await mkdir(OUT_DIR, { recursive: true });
  console.log(`writing screenshots to ${OUT_DIR}`);
  console.log(`target: ${BASE_URL}`);

  await captureInstallAndAdminFlow();
  await captureMobile();

  console.log(`\ncaptured ${captured.length} screenshots:`);
  for (const name of captured) console.log(`  - ${name}.png`);
}

main().catch((err) => {
  console.error("\ncapture failed:", err);
  process.exit(1);
});
