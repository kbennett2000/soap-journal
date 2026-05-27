from soap_journal.core.bible.books import (
    ALL_BOOKS,
    book_count,
    get_book_by_name,
)


def test_all_books_has_66_entries() -> None:
    assert book_count() == 66
    assert len(ALL_BOOKS) == 66


def test_order_indices_are_1_to_66_in_sequence() -> None:
    assert [b.order_index for b in ALL_BOOKS] == list(range(1, 67))


def test_first_and_last_canonical_names() -> None:
    assert ALL_BOOKS[0].name == "Genesis"
    assert ALL_BOOKS[-1].name == "Revelation"


def test_testament_split_is_39_27() -> None:
    ot = [b for b in ALL_BOOKS if b.testament == "OT"]
    nt = [b for b in ALL_BOOKS if b.testament == "NT"]
    assert len(ot) == 39
    assert len(nt) == 27


def test_lookup_by_canonical_name() -> None:
    book = get_book_by_name("Genesis")
    assert book is not None
    assert book.name == "Genesis"


def test_lookup_is_case_insensitive() -> None:
    assert get_book_by_name("GENESIS") is get_book_by_name("genesis")
    assert get_book_by_name("genesis").name == "Genesis"


def test_lookup_by_abbreviation() -> None:
    assert get_book_by_name("Gen").name == "Genesis"
    assert get_book_by_name("1 Cor").name == "1 Corinthians"
    assert get_book_by_name("Rev").name == "Revelation"


def test_lookup_by_alias() -> None:
    assert get_book_by_name("Psalm").name == "Psalms"
    assert get_book_by_name("Song of Songs").name == "Song of Solomon"
    assert get_book_by_name("Canticles").name == "Song of Solomon"
    assert get_book_by_name("Apocalypse").name == "Revelation"
    assert get_book_by_name("First Corinthians").name == "1 Corinthians"


def test_lookup_is_whitespace_tolerant() -> None:
    assert get_book_by_name("1Cor").name == "1 Corinthians"
    assert get_book_by_name("1cor").name == "1 Corinthians"
    assert get_book_by_name("  John  ").name == "John"


def test_lookup_unknown_returns_none() -> None:
    assert get_book_by_name("Book of Mormon") is None
    assert get_book_by_name("") is None
    assert get_book_by_name("   ") is None


def test_unique_canonical_names() -> None:
    names = [b.name for b in ALL_BOOKS]
    assert len(set(names)) == len(names)


def test_all_66_nkjv_abbreviations_resolve() -> None:
    nkjv_abbrs = [
        "Gen",
        "Exo",
        "Lev",
        "Num",
        "Deu",
        "Jos",
        "Jdg",
        "Rut",
        "1Sa",
        "2Sa",
        "1Ki",
        "2Ki",
        "1Ch",
        "2Ch",
        "Ezr",
        "Neh",
        "Est",
        "Job",
        "Psa",
        "Pro",
        "Ecc",
        "Sol",
        "Isa",
        "Jer",
        "Lam",
        "Eze",
        "Dan",
        "Hos",
        "Joe",
        "Amo",
        "Oba",
        "Jon",
        "Mic",
        "Nah",
        "Hab",
        "Zep",
        "Hag",
        "Zec",
        "Mal",
        "Mat",
        "Mar",
        "Luk",
        "Joh",
        "Act",
        "Rom",
        "1Co",
        "2Co",
        "Gal",
        "Eph",
        "Phi",
        "Col",
        "1Th",
        "2Th",
        "1Ti",
        "2Ti",
        "Tit",
        "Phm",
        "Heb",
        "Jam",
        "1Pe",
        "2Pe",
        "1Jo",
        "2Jo",
        "3Jo",
        "Jud",
        "Rev",
    ]
    assert len(nkjv_abbrs) == 66
    for abbr in nkjv_abbrs:
        book = get_book_by_name(abbr)
        assert book is not None, f"NKJV abbreviation {abbr!r} not found"


def test_nkjv_new_aliases_resolve_correctly() -> None:
    expected = {
        "Deu": "Deuteronomy",
        "Rut": "Ruth",
        "Sol": "Song of Solomon",
        "Joe": "Joel",
        "Amo": "Amos",
        "Oba": "Obadiah",
        "Mat": "Matthew",
        "Mar": "Mark",
        "Joh": "John",
        "Phi": "Philippians",
        "Jam": "James",
    }
    for abbr, name in expected.items():
        book = get_book_by_name(abbr)
        assert book is not None, f"{abbr} should resolve"
        assert book.name == name, f"{abbr} -> {book.name}, expected {name}"


def test_all_17_nlt_ordinal_aliases_resolve() -> None:
    expected = {
        "1st Samuel": "1 Samuel",
        "2nd Samuel": "2 Samuel",
        "1st Kings": "1 Kings",
        "2nd Kings": "2 Kings",
        "1st Chronicles": "1 Chronicles",
        "2nd Chronicles": "2 Chronicles",
        "1st Corinthians": "1 Corinthians",
        "2nd Corinthians": "2 Corinthians",
        "1st Thessalonians": "1 Thessalonians",
        "2nd Thessalonians": "2 Thessalonians",
        "1st Timothy": "1 Timothy",
        "2nd Timothy": "2 Timothy",
        "1st Peter": "1 Peter",
        "2nd Peter": "2 Peter",
        "1st John": "1 John",
        "2nd John": "2 John",
        "3rd John": "3 John",
    }
    assert len(expected) == 17
    for alias, name in expected.items():
        book = get_book_by_name(alias)
        assert book is not None, f"ordinal alias {alias!r} should resolve"
        assert book.name == name, f"{alias} -> {book.name}, expected {name}"


def test_book_model_is_frozen() -> None:
    book = ALL_BOOKS[0]
    try:
        book.name = "Other"  # type: ignore[misc]
    except (TypeError, ValueError):
        return
    raise AssertionError("Book should be frozen")
