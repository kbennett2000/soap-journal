import {
  readFontSize,
  readJson,
  readLastLocation,
  readLayout,
  STORAGE_KEYS,
  writeFontSize,
  writeJson,
  writeLastLocation,
  writeLayout,
  type ReaderLocation,
} from "@/lib/storage";

describe("storage", () => {
  it("round-trips a typed value via readJson/writeJson", () => {
    writeJson("test.key", { a: 1, b: "two" });
    expect(readJson<{ a: number; b: string }>("test.key", { a: 0, b: "" })).toEqual({
      a: 1,
      b: "two",
    });
  });

  it("returns the fallback when the stored value is not valid JSON", () => {
    window.localStorage.setItem("test.bad", "{not json");
    expect(readJson<{ ok: boolean }>("test.bad", { ok: false })).toEqual({ ok: false });
  });

  it("returns the fallback when the key is missing", () => {
    expect(readJson("test.missing", "fallback")).toBe("fallback");
  });

  it("reader last-location round-trips", () => {
    const value: ReaderLocation = {
      translationCode: "BSB",
      bookName: "John",
      chapterNumber: 3,
    };
    writeLastLocation(value);
    expect(readLastLocation()).toEqual(value);
  });

  it("reader last-location returns undefined for missing or malformed data", () => {
    expect(readLastLocation()).toBeUndefined();
    window.localStorage.setItem(
      STORAGE_KEYS.readerLastLocation,
      JSON.stringify({ translationCode: 42 }),
    );
    expect(readLastLocation()).toBeUndefined();
  });

  it("font size defaults to M and accepts S/L", () => {
    expect(readFontSize()).toBe("M");
    writeFontSize("L");
    expect(readFontSize()).toBe("L");
    writeFontSize("S");
    expect(readFontSize()).toBe("S");
    // Garbage falls back to default.
    window.localStorage.setItem(STORAGE_KEYS.readerFontSize, JSON.stringify("XXL"));
    expect(readFontSize()).toBe("M");
  });

  it("layout defaults to verse and accepts paragraph", () => {
    expect(readLayout()).toBe("verse");
    writeLayout("paragraph");
    expect(readLayout()).toBe("paragraph");
    window.localStorage.setItem(STORAGE_KEYS.readerLayout, JSON.stringify("strange"));
    expect(readLayout()).toBe("verse");
  });
});
