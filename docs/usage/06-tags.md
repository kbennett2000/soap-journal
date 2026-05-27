# 6. Tags

Tags are short labels you attach to entries to group them in ways the
Bible reference alone doesn't capture. They're **your** vocabulary —
nobody decides what tags exist except you.

Some examples from a real journal:

- `gratitude`, `lament`, `confession` — by emotional tone
- `marriage`, `parenting`, `work`, `friendship` — by area of life
- `advent`, `lent`, `easter` — by season
- `sermon` — for entries you wrote in response to something you heard
- `kids-devo` — for passages you covered with your children at the
  table

A single entry can have any number of tags. Most have one or two.

## Adding tags on an entry

The Tags field is at the bottom of the entry form:

![Tag input with chips for "love" and "grace" already added, "ho" being typed, and the autocomplete dropdown showing "hope" as a suggestion](../screenshots/usage-tag-autocomplete.png)

To add a tag:

1. Click in the input area.
2. Type the tag name.
3. Press **Enter**, **Tab**, or **,** (comma) to commit it as a chip.

To remove a tag, click the **×** on its chip.

A few details worth knowing:

- **Case-insensitive deduplication.** Typing `Grace` when you already
  have `grace` silently clears the input — the existing tag stays as
  it was. So you can't accidentally end up with both.
- **Max length** is 50 characters. Long tags don't display well in
  the entry list anyway.
- **Backspace** in an empty input removes the last chip — quicker than
  hunting for the **×**.

## Autocomplete

As you type, soap-journal looks up every tag you've used before and
shows matches as a dropdown:

- Click a suggestion to use it.
- Press **↑** / **↓** to highlight a suggestion, then **Enter** to
  commit it.
- Press **Escape** to dismiss the dropdown without picking anything.

This is the main way you keep your vocabulary tidy. If you reach for
`comfort` and the autocomplete shows you already have `comforted` and
`comfort`, you can pick the existing one and avoid splitting the
group.

## Tags are private

Tags are scoped to your account. Other users on the same instance
can't see your tags and you can't see theirs. There's no shared global
tag dictionary.

## Filtering by tag

In the [entries list](05-finding-entries.md), the **Tag** filter
dropdown lists every tag you've used. Pick one and the list narrows to
just entries with that tag.

You can also bookmark a tag URL directly:

```
/entries?tag=gratitude
```

## What happens to a tag when its last entry is deleted?

The tag itself is **not removed** — it stays in your autocomplete list.

This is deliberate. If you delete the only entry you ever wrote with
the `lament` tag, the next time you sit down to write about lament you
still want autocomplete to know about that tag. Otherwise you'd end up
re-typing slightly different spellings (`lament`, `Lamenting`,
`laments`) and your library would fragment.

If a leftover tag is genuinely bothering you, the only way to make it
vanish completely from autocomplete in v0.1 is to use it on a new
entry and then change your mind — there's no "tag manager" in v0.1.
This is on the radar for a future release.

---

Previous: [Finding entries](05-finding-entries.md) · Next: [Calendar and "on this day" →](07-calendar-and-on-this-day.md)
