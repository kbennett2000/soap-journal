"""Canonical book list for the Protestant 66-book Bible.

The single source of truth for book names, ordering, and accepted aliases.
The canonical JSON schema validates against this list; the BSB parser
reconciles source book names against it; the future reference parser
("John 3:16", "Jn 3:16", "1 Cor 13") will consume the alias table.

Adding aliases is cheap and additive — extend `aliases` as new ones come up.
Renaming a canonical `name` is a breaking change: it shifts what gets stored
in the `books` table and what the schema validator expects.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

Testament = Literal["OT", "NT"]


class Book(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    abbreviation: str
    aliases: tuple[str, ...]
    testament: Testament
    order_index: int


def _b(
    name: str,
    abbreviation: str,
    testament: Testament,
    order_index: int,
    *aliases: str,
) -> Book:
    return Book(
        name=name,
        abbreviation=abbreviation,
        aliases=aliases,
        testament=testament,
        order_index=order_index,
    )


# Order matters: this is the canonical order_index 1..66.
ALL_BOOKS: tuple[Book, ...] = (
    # ---- Old Testament -----------------------------------------------------
    _b("Genesis", "Gen", "OT", 1, "Gn", "Ge"),
    _b("Exodus", "Exod", "OT", 2, "Ex", "Exo"),
    _b("Leviticus", "Lev", "OT", 3, "Lv", "Le"),
    _b("Numbers", "Num", "OT", 4, "Nm", "Nu", "Nb"),
    _b("Deuteronomy", "Deut", "OT", 5, "Dt", "De", "Deu"),
    _b("Joshua", "Josh", "OT", 6, "Jos", "Jsh"),
    _b("Judges", "Judg", "OT", 7, "Jdg", "Jgs"),
    _b("Ruth", "Ruth", "OT", 8, "Ru", "Rth", "Rut"),
    _b("1 Samuel", "1 Sam", "OT", 9, "1Sam", "1 Sm", "1Sm", "First Samuel", "1Sa", "1st Samuel"),
    _b("2 Samuel", "2 Sam", "OT", 10, "2Sam", "2 Sm", "2Sm", "Second Samuel", "2Sa", "2nd Samuel"),
    _b("1 Kings", "1 Kgs", "OT", 11, "1Kgs", "1 Ki", "1Ki", "First Kings", "1st Kings"),
    _b("2 Kings", "2 Kgs", "OT", 12, "2Kgs", "2 Ki", "2Ki", "Second Kings", "2nd Kings"),
    _b(
        "1 Chronicles",
        "1 Chr",
        "OT",
        13,
        "1Chr",
        "1 Ch",
        "1Ch",
        "First Chronicles",
        "1st Chronicles",
    ),
    _b(
        "2 Chronicles",
        "2 Chr",
        "OT",
        14,
        "2Chr",
        "2 Ch",
        "2Ch",
        "Second Chronicles",
        "2nd Chronicles",
    ),
    _b("Ezra", "Ezra", "OT", 15, "Ezr", "Ez"),
    _b("Nehemiah", "Neh", "OT", 16, "Ne"),
    _b("Esther", "Esth", "OT", 17, "Est", "Es"),
    _b("Job", "Job", "OT", 18, "Jb"),
    _b("Psalms", "Ps", "OT", 19, "Psalm", "Pss", "Psa", "Pslm"),
    _b("Proverbs", "Prov", "OT", 20, "Prv", "Pr", "Pro"),
    _b("Ecclesiastes", "Eccl", "OT", 21, "Ecc", "Ec", "Qoh", "Qoheleth"),
    _b(
        "Song of Solomon",
        "Song",
        "OT",
        22,
        "Song of Songs",
        "SoS",
        "SS",
        "Sg",
        "Sng",
        "Canticles",
        "Cant",
        "Sol",
    ),
    _b("Isaiah", "Isa", "OT", 23, "Is"),
    _b("Jeremiah", "Jer", "OT", 24, "Je", "Jr"),
    _b("Lamentations", "Lam", "OT", 25, "La"),
    _b("Ezekiel", "Ezek", "OT", 26, "Eze", "Ezk"),
    _b("Daniel", "Dan", "OT", 27, "Dn", "Da"),
    _b("Hosea", "Hos", "OT", 28, "Ho"),
    _b("Joel", "Joel", "OT", 29, "Jl", "Joe"),
    _b("Amos", "Amos", "OT", 30, "Am", "Amo"),
    _b("Obadiah", "Obad", "OT", 31, "Ob", "Oba"),
    _b("Jonah", "Jonah", "OT", 32, "Jon", "Jnh"),
    _b("Micah", "Mic", "OT", 33, "Mc"),
    _b("Nahum", "Nah", "OT", 34, "Na"),
    _b("Habakkuk", "Hab", "OT", 35, "Hb"),
    _b("Zephaniah", "Zeph", "OT", 36, "Zep", "Zp"),
    _b("Haggai", "Hag", "OT", 37, "Hg"),
    _b("Zechariah", "Zech", "OT", 38, "Zec", "Zc"),
    _b("Malachi", "Mal", "OT", 39, "Ml"),
    # ---- New Testament -----------------------------------------------------
    _b("Matthew", "Matt", "NT", 40, "Mt", "Mat"),
    _b("Mark", "Mark", "NT", 41, "Mk", "Mrk", "Mar"),
    _b("Luke", "Luke", "NT", 42, "Lk", "Luk"),
    _b("John", "John", "NT", 43, "Jn", "Jhn", "Joh"),
    _b("Acts", "Acts", "NT", 44, "Ac", "Act"),
    _b("Romans", "Rom", "NT", 45, "Ro", "Rm"),
    _b(
        "1 Corinthians",
        "1 Cor",
        "NT",
        46,
        "1Cor",
        "1 Co",
        "1Co",
        "First Corinthians",
        "1st Corinthians",
    ),
    _b(
        "2 Corinthians",
        "2 Cor",
        "NT",
        47,
        "2Cor",
        "2 Co",
        "2Co",
        "Second Corinthians",
        "2nd Corinthians",
    ),
    _b("Galatians", "Gal", "NT", 48, "Ga"),
    _b("Ephesians", "Eph", "NT", 49, "Ephes"),
    _b("Philippians", "Phil", "NT", 50, "Php", "Pp", "Phi"),
    _b("Colossians", "Col", "NT", 51, "Co"),
    _b(
        "1 Thessalonians",
        "1 Thess",
        "NT",
        52,
        "1Thess",
        "1 Th",
        "1Th",
        "First Thessalonians",
        "1st Thessalonians",
    ),
    _b(
        "2 Thessalonians",
        "2 Thess",
        "NT",
        53,
        "2Thess",
        "2 Th",
        "2Th",
        "Second Thessalonians",
        "2nd Thessalonians",
    ),
    _b("1 Timothy", "1 Tim", "NT", 54, "1Tim", "1 Ti", "1Ti", "First Timothy", "1st Timothy"),
    _b("2 Timothy", "2 Tim", "NT", 55, "2Tim", "2 Ti", "2Ti", "Second Timothy", "2nd Timothy"),
    _b("Titus", "Titus", "NT", 56, "Ti", "Tit"),
    _b("Philemon", "Phlm", "NT", 57, "Phm", "Pm"),
    _b("Hebrews", "Heb", "NT", 58, "He"),
    _b("James", "Jas", "NT", 59, "Jm", "Jam"),
    _b("1 Peter", "1 Pet", "NT", 60, "1Pet", "1 Pe", "1Pe", "First Peter", "1st Peter"),
    _b("2 Peter", "2 Pet", "NT", 61, "2Pet", "2 Pe", "2Pe", "Second Peter", "2nd Peter"),
    _b("1 John", "1 John", "NT", 62, "1Jn", "1 Jn", "1Jo", "1 Jo", "First John", "1st John"),
    _b("2 John", "2 John", "NT", 63, "2Jn", "2 Jn", "2Jo", "2 Jo", "Second John", "2nd John"),
    _b("3 John", "3 John", "NT", 64, "3Jn", "3 Jn", "3Jo", "3 Jo", "Third John", "3rd John"),
    _b("Jude", "Jude", "NT", 65, "Jud", "Jd"),
    _b("Revelation", "Rev", "NT", 66, "Re", "Rv", "Apocalypse", "Apoc"),
)


def _build_lookup() -> dict[str, Book]:
    """Lowercase-keyed lookup spanning every name, abbreviation, and alias.

    Built once at import time. Each Book is reachable through every form it
    declares, including a normalized form that collapses internal whitespace
    (so "1Corinthians" matches "1 Corinthians" if a caller forgets the space).
    """
    table: dict[str, Book] = {}
    for book in ALL_BOOKS:
        forms = {book.name, book.abbreviation, *book.aliases}
        for form in forms:
            normalized = form.lower()
            collapsed = normalized.replace(" ", "")
            table[normalized] = book
            table[collapsed] = book
    return table


_LOOKUP: dict[str, Book] = _build_lookup()


def get_book_by_name(name: str) -> Book | None:
    """Return the canonical Book for any accepted name/abbreviation/alias.

    Lookup is case-insensitive and whitespace-tolerant: "1cor", "1 Cor",
    "1Cor", "1 Corinthians", and "First Corinthians" all resolve to the
    same Book. Returns None when nothing matches.
    """
    if not name:
        return None
    key = name.strip().lower()
    if not key:
        return None
    if key in _LOOKUP:
        return _LOOKUP[key]
    collapsed = key.replace(" ", "")
    return _LOOKUP.get(collapsed)


def book_count() -> int:
    return len(ALL_BOOKS)
