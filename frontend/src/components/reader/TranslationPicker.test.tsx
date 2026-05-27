import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { TranslationPicker } from "@/components/reader/TranslationPicker";
import type { TranslationSummary } from "@/types/api";

const BSB: TranslationSummary = {
  code: "BSB",
  name: "Berean Standard Bible",
  language: "en",
  copyright: "Public domain.",
};

const KJV: TranslationSummary = {
  code: "KJV",
  name: "King James Version",
  language: "en",
  copyright: "Public domain.",
};

describe("TranslationPicker", () => {
  it("renders a non-interactive pill when only one translation", () => {
    render(
      <TranslationPicker translations={[BSB]} currentCode="BSB" onChange={vi.fn()} />,
    );
    expect(screen.getByTestId("translation-pill")).toHaveTextContent("BSB");
    expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
  });

  it("renders a select when two or more translations", () => {
    render(
      <TranslationPicker
        translations={[BSB, KJV]}
        currentCode="BSB"
        onChange={vi.fn()}
      />,
    );
    expect(screen.getByRole("combobox", { name: /translation/i })).toBeInTheDocument();
    expect(screen.queryByTestId("translation-pill")).not.toBeInTheDocument();
  });

  it("select value matches currentCode", () => {
    render(
      <TranslationPicker
        translations={[BSB, KJV]}
        currentCode="KJV"
        onChange={vi.fn()}
      />,
    );
    expect(screen.getByRole("combobox", { name: /translation/i })).toHaveValue("KJV");
  });

  it("calls onChange when a different translation is selected", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(
      <TranslationPicker
        translations={[BSB, KJV]}
        currentCode="BSB"
        onChange={onChange}
      />,
    );
    await user.selectOptions(
      screen.getByRole("combobox", { name: /translation/i }),
      "KJV",
    );
    expect(onChange).toHaveBeenCalledWith("KJV");
  });
});
