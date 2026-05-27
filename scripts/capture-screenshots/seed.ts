// Seed the running soap-journal instance with predictable data so the
// screenshot capture script always produces the same shots regardless of
// when it runs. Talks to the HTTP API directly — no database access, no
// container internals — so it works against any reachable instance.
//
// Assumes the target is FRESH (no users, no entries). Run after
// `docker compose down -v && docker compose up -d` (wait for healthy).
//
// Standalone usage (registers alice as admin + seeds everything):
//   BASE_URL=http://localhost:8080 npx tsx seed.ts
//
// Library usage (capture.ts imports these helpers and drives the admin
// registration through the UI so the install screenshots are real):
//   import { createSecondUser, seedAdminEntries, ADMIN, ... } from "./seed";

export const ADMIN = { username: "alice", password: "password123" };
export const SECOND_USER = { username: "bob", password: "password123" };

const DEFAULT_BASE_URL = "http://localhost:8080";

type Cookie = string;

interface Json {
  [k: string]: unknown;
}

type RequestOpts = { body?: Json; cookie?: Cookie };

async function request(
  baseUrl: string,
  method: string,
  path: string,
  opts: RequestOpts = {},
): Promise<{ status: number; body: Json; setCookie: string | null }> {
  const headers: Record<string, string> = { Accept: "application/json" };
  if (opts.body !== undefined) headers["Content-Type"] = "application/json";
  if (opts.cookie) headers["Cookie"] = opts.cookie;

  const res = await fetch(`${baseUrl}${path}`, {
    method,
    headers,
    body: opts.body === undefined ? undefined : JSON.stringify(opts.body),
    redirect: "manual",
  });
  const setCookie = res.headers.get("set-cookie");
  let body: Json = {};
  if (res.status !== 204 && res.headers.get("content-type")?.includes("application/json")) {
    body = (await res.json()) as Json;
  }
  return { status: res.status, body, setCookie };
}

export function extractSessionCookie(setCookie: string | null): Cookie {
  if (!setCookie) throw new Error("expected a Set-Cookie header but got none");
  const match = setCookie.match(/soap_session=[^;,]+/);
  if (!match) throw new Error(`no soap_session cookie in: ${setCookie}`);
  return match[0];
}

async function expectStatus(
  promise: ReturnType<typeof request>,
  expected: number,
  context: string,
): Promise<{ body: Json; setCookie: string | null }> {
  const res = await promise;
  if (res.status !== expected) {
    throw new Error(
      `${context}: expected HTTP ${expected}, got ${res.status} — ${JSON.stringify(res.body)}`,
    );
  }
  return { body: res.body, setCookie: res.setCookie };
}

export interface EntryDraft {
  title?: string;
  entry_date: string;
  scripture_ref: string;
  observation: string;
  application: string;
  prayer: string;
  tags: string[];
}

export async function createEntry(
  baseUrl: string,
  cookie: Cookie,
  draft: EntryDraft,
): Promise<void> {
  await expectStatus(
    request(baseUrl, "POST", "/api/v1/entries", {
      cookie,
      body: { ...draft, translation_code: "BSB" },
    }),
    201,
    `create entry "${draft.scripture_ref}"`,
  );
}

export async function loginViaApi(
  baseUrl: string,
  creds: { username: string; password: string },
): Promise<Cookie> {
  const res = await expectStatus(
    request(baseUrl, "POST", "/api/v1/auth/login", { body: creds }),
    200,
    `login ${creds.username}`,
  );
  return extractSessionCookie(res.setCookie);
}

export async function registerAdminViaApi(baseUrl: string): Promise<Cookie> {
  const res = await expectStatus(
    request(baseUrl, "POST", "/api/v1/auth/register", { body: ADMIN }),
    201,
    "register admin",
  );
  return extractSessionCookie(res.setCookie);
}

export async function createSecondUser(baseUrl: string, adminCookie: Cookie): Promise<void> {
  await expectStatus(
    request(baseUrl, "POST", "/api/v1/admin/users", {
      cookie: adminCookie,
      body: { username: SECOND_USER.username, password: SECOND_USER.password, is_admin: false },
    }),
    201,
    "create second user",
  );
}

function isoDaysAgo(days: number): string {
  const d = new Date();
  d.setUTCDate(d.getUTCDate() - days);
  return d.toISOString().slice(0, 10);
}

function isoYearsAgo(years: number): string {
  const d = new Date();
  d.setUTCFullYear(d.getUTCFullYear() - years);
  return d.toISOString().slice(0, 10);
}

export function buildAdminEntries(): EntryDraft[] {
  const today = isoDaysAgo(0);
  const todayLastYear = isoYearsAgo(1);
  const todayTwoYearsAgo = isoYearsAgo(2);

  return [
    {
      title: "Belovedness",
      entry_date: today,
      scripture_ref: "John 3:16-17",
      observation:
        "God so loved the world that He sent His only Son. The motive is love; the outcome is rescue, not condemnation.",
      application:
        "When I'm tempted to think of God as reluctant or distant, this passage reframes the whole story. He moved first, at cost.",
      prayer:
        "Father, thank You for loving me before I knew I needed loving. Teach me to live like someone who has been rescued.",
      tags: ["love", "grace", "gospel"],
    },
    {
      entry_date: isoDaysAgo(1),
      scripture_ref: "Psalm 23:1-4",
      observation:
        "The Lord is my shepherd — present tense, personal. Even in the darkest valley the comfort is His presence, not absence of trouble.",
      application:
        "I keep waiting for the valley to end before I can rest. The psalm says the rod and staff are *in* the valley.",
      prayer:
        "Shepherd, I won't pretend to feel brave. I will sit down where You've made me lie down.",
      tags: ["comfort", "trust"],
    },
    {
      title: "Renewed strength",
      entry_date: isoDaysAgo(2),
      scripture_ref: "Isaiah 40:28-31",
      observation:
        "The everlasting God does not grow tired. He gives strength to the weary — not to the strong.",
      application:
        "My weakness is the qualifying credential, not the disqualifying one. Waiting is active, not passive.",
      prayer: "Lord, renew my strength today. I'm tired in a way sleep can't touch.",
      tags: ["hope", "strength"],
    },
    {
      entry_date: isoDaysAgo(4),
      scripture_ref: "Romans 8:28-30",
      observation:
        "All things work together for good — not all things are good, but God weaves them. The chain runs from foreknown to glorified.",
      application:
        "Today's frustration is not a detour from God's purpose. It is part of the weaving.",
      prayer:
        "Father, I trust You with the threads I can't see. Make me patient with the pattern.",
      tags: ["sovereignty", "trust", "hope"],
    },
    {
      entry_date: isoDaysAgo(6),
      scripture_ref: "Philippians 4:6-7",
      observation:
        "Anxiety yields to prayer + thanksgiving — both, not either. The peace that follows is custodial: it guards heart and mind.",
      application:
        "I will not wait until I 'feel grateful' to give thanks. Thanks is the on-ramp, not the destination.",
      prayer:
        "Lord, here is what I'm anxious about. Here is what I am grateful for. Trade me Your peace for my worry.",
      tags: ["prayer", "anxiety", "peace"],
    },
    {
      title: "First and great",
      entry_date: isoDaysAgo(8),
      scripture_ref: "Matthew 22:37-39",
      observation:
        "Two commands carry the weight of the Law and Prophets. Love God with all of yourself; love your neighbor like yourself.",
      application:
        "I can be religiously busy and still miss both. Today I will name one person to love concretely.",
      prayer: "Teach me to love what You love, in the order You love it.",
      tags: ["love", "discipleship"],
    },
    {
      entry_date: isoDaysAgo(10),
      scripture_ref: "Proverbs 3:5-6",
      observation:
        "Trust with the whole heart; lean not on your own understanding. Acknowledge Him — He makes the paths straight.",
      application:
        "My instinct is to figure things out and then ask God to bless the plan. The proverb reverses the order.",
      prayer: "I acknowledge You over today's decisions, before I rehearse them.",
      tags: ["trust", "wisdom"],
    },
    {
      entry_date: isoDaysAgo(13),
      scripture_ref: "1 Corinthians 13:4-7",
      observation:
        "Love is what love does: patient, kind, slow to anger, quick to bear. It is a verb here, not a feeling.",
      application:
        "If I substitute my name for 'love' in these verses, the result is honest and painful. The point is to grow into the verses, not to score them.",
      prayer:
        "Father, grow patience in me where I am still quick. Grow kindness where I am tired.",
      tags: ["love"],
    },
    {
      entry_date: isoDaysAgo(17),
      scripture_ref: "James 1:2-4",
      observation:
        "Trials are joy because they produce endurance, and endurance finishes its work.",
      application:
        "I tend to ask God to remove what He plans to use. The harder prayer is to let the work finish.",
      prayer: "Lord, finish the work in me. Don't let me run from what is forming me.",
      tags: ["endurance", "hope"],
    },
    {
      entry_date: isoDaysAgo(22),
      scripture_ref: "Ephesians 2:8-10",
      observation:
        "Grace through faith, the gift of God — not from works. And then: we are His workmanship, *created for* good works.",
      application:
        "Works don't earn the gift; they're the natural shape of a gifted life. The grace did the heavy lifting.",
      prayer: "Thank You for the gift. Show me the good works prepared for today.",
      tags: ["grace", "gospel"],
    },
    // "On this day" entries — same month+day, prior years.
    {
      title: "Be still",
      entry_date: todayLastYear,
      scripture_ref: "Psalm 46:10",
      observation:
        '"Be still and know that I am God." The stillness is not passive — it is a deliberate stopping in order to know.',
      application: "Today I will close one tab and sit with one verse instead of skimming five.",
      prayer: "Quiet me, Lord. I will be still long enough to know You are God.",
      tags: ["stillness", "trust"],
    },
    {
      entry_date: todayTwoYearsAgo,
      scripture_ref: "Lamentations 3:22-23",
      observation:
        "His mercies are new every morning — great is His faithfulness. Yesterday's mercy doesn't exhaust today's supply.",
      application: "I will not borrow tomorrow's troubles. Today's mercies are sized for today.",
      prayer: "Thank You for new mercies. Help me receive today's portion.",
      tags: ["mercy", "hope"],
    },
  ];
}

export async function seedAdminEntries(baseUrl: string, adminCookie: Cookie): Promise<void> {
  for (const draft of buildAdminEntries()) {
    await createEntry(baseUrl, adminCookie, draft);
  }
}

export async function seedSecondUserEntries(baseUrl: string): Promise<void> {
  const cookie = await loginViaApi(baseUrl, SECOND_USER);
  await createEntry(baseUrl, cookie, {
    entry_date: isoDaysAgo(0),
    scripture_ref: "Psalm 1:1-3",
    observation:
      "The blessed one delights in the law of the Lord and meditates on it day and night.",
    application: "I will pick one verse to chew on through the day.",
    prayer: "Plant me by Your stream, Lord.",
    tags: ["meditation"],
  });
}

async function ensureFresh(baseUrl: string): Promise<void> {
  // A fresh instance returns 400 (validation: username too short / password
  // too short) for this probe. A populated one returns 403 (registration
  // closed) or 409 (username taken). 201 means we accidentally created the
  // first user — bail loudly so the next run starts clean.
  const probe = await request(baseUrl, "POST", "/api/v1/auth/register", {
    body: { username: "__probe__", password: "throwaway-not-used" },
  });
  if (probe.status === 201) {
    throw new Error(
      "Probe registered a user. Run `docker compose down -v && docker compose up -d` to reset.",
    );
  }
  if (probe.status === 403) {
    throw new Error(
      "Instance already has users. Run `docker compose down -v && docker compose up -d`, wait for healthy, then re-run.",
    );
  }
  if (probe.status === 409) {
    throw new Error("Username conflict on probe. Reset the DB and re-run.");
  }
  if (probe.status !== 400 && probe.status !== 422) {
    throw new Error(`Unexpected probe status ${probe.status}: ${JSON.stringify(probe.body)}`);
  }
}

export async function runStandaloneSeed(): Promise<void> {
  const baseUrl = process.env.BASE_URL ?? DEFAULT_BASE_URL;
  console.log(`seeding against ${baseUrl}`);

  await ensureFresh(baseUrl);

  const adminCookie = await registerAdminViaApi(baseUrl);
  console.log(`  registered admin: ${ADMIN.username}`);

  await createSecondUser(baseUrl, adminCookie);
  console.log(`  created second user: ${SECOND_USER.username}`);

  await seedAdminEntries(baseUrl, adminCookie);
  console.log(`  created ${buildAdminEntries().length} entries for ${ADMIN.username}`);

  await seedSecondUserEntries(baseUrl);
  console.log(`  created 1 entry for ${SECOND_USER.username}`);

  console.log("seed complete");
}

if (import.meta.url === `file://${process.argv[1]}`) {
  runStandaloneSeed().catch((err) => {
    console.error(err);
    process.exit(1);
  });
}
