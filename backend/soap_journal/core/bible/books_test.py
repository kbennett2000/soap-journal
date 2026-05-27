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


def test_book_model_is_frozen() -> None:
    book = ALL_BOOKS[0]
    try:
        book.name = "Other"  # type: ignore[misc]
    except (TypeError, ValueError):
        return
    raise AssertionError("Book should be frozen")
