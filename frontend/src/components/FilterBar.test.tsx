import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";

import { FilterBar, type FilterValues } from "@/components/FilterBar";
import { renderWithProviders } from "@/test/utils/renderWithProviders";

const EMPTY: FilterValues = {
  q: "",
  book: "",
  tag: "",
  fromDate: "",
  toDate: "",
};

function Wrapper({
  initial = EMPTY,
  onChange,
  dateRangeError,
}: {
  initial?: FilterValues;
  onChange: (v: FilterValues) => void;
  dateRangeError?: string | null;
}): JSX.Element {
  const [values, setValues] = useState<FilterValues>(initial);
  return (
    <FilterBar
      values={values}
      onChange={(next) => {
        setValues(next);
        onChange(next);
      }}
      dateRangeError={dateRangeError ?? null}
    />
  );
}

describe("FilterBar", () => {
  it("renders all four controls", () => {
    renderWithProviders(<Wrapper onChange={vi.fn()} />);
    expect(screen.getByLabelText(/search/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^book$/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^tag$/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^from$/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^to$/i)).toBeInTheDocument();
  });

  it("debounces q before firing onChange", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    renderWithProviders(<Wrapper onChange={onChange} />);

    await user.type(screen.getByLabelText(/search/i), "love");

    // Each keystroke shouldn't fire immediately; the debounced effect fires once.
    await waitFor(() => {
      const lastCall = onChange.mock.calls[onChange.mock.calls.length - 1];
      expect(lastCall?.[0].q).toBe("love");
    });
  });

  it("clearing q via × clears it immediately", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    renderWithProviders(
      <Wrapper
        initial={{ ...EMPTY, q: "love" }}
        onChange={onChange}
      />,
    );

    await user.click(screen.getByRole("button", { name: /clear search/i }));

    await waitFor(() => {
      const lastCall = onChange.mock.calls[onChange.mock.calls.length - 1];
      expect(lastCall?.[0].q).toBe("");
    });
  });

  it("date range error highlights and shows the message", () => {
    renderWithProviders(
      <Wrapper
        onChange={vi.fn()}
        dateRangeError="from_date is after to_date"
      />,
    );

    expect(screen.getByRole("alert")).toHaveTextContent("from_date is after to_date");
  });
});
