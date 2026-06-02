"""Registry of all PDFMaker-format Bible translations.

Single source of truth for translation metadata.  Used by per-translation
parser shims and the Docker bootstrap script.
"""

from __future__ import annotations

from soap_journal.parsers.pdfmaker_format import PdfMakerTranslationConfig

PDFMAKER_CONFIGS: dict[str, PdfMakerTranslationConfig] = {
    "KJV": PdfMakerTranslationConfig(
        code="KJV",
        name="King James Version",
        language="en",
        copyright="The King James Version is in the public domain.",
        footer_marker="KJV  [Online]",
    ),
    "AKJV": PdfMakerTranslationConfig(
        code="AKJV",
        name="American King James Version",
        language="en",
        copyright="The American King James Version is in the public domain.",
        footer_marker="AKJV  [Online]",
    ),
    "ASV": PdfMakerTranslationConfig(
        code="ASV",
        name="American Standard Version",
        language="en",
        copyright="The American Standard Version (1901) is in the public domain.",
        footer_marker="ASV  [Online]",
    ),
    "CPDV": PdfMakerTranslationConfig(
        code="CPDV",
        name="Catholic Public Domain Version",
        language="en",
        copyright=(
            "Catholic Public Domain Version, by Ronald L. Conte Jr. "
            "Released into the public domain."
        ),
        footer_marker="CPDV  [Online]",
    ),
    "DBT": PdfMakerTranslationConfig(
        code="DBT",
        name="Darby Bible Translation",
        language="en",
        copyright="The Darby Bible Translation (1890) is in the public domain.",
        footer_marker="DBT  [Online]",
    ),
    "DRB": PdfMakerTranslationConfig(
        code="DRB",
        name="Douay-Rheims Bible",
        language="en",
        copyright=("Douay-Rheims Bible, Challoner Revision. Public domain."),
        footer_marker="DRB  [Online]",
    ),
    "ERV": PdfMakerTranslationConfig(
        code="ERV",
        name="English Revised Version",
        language="en",
        copyright="The English Revised Version (1885) is in the public domain.",
        footer_marker="ERV  [Online]",
    ),
    "JPS": PdfMakerTranslationConfig(
        code="JPS",
        name="JPS Tanakh / Weymouth NT",
        language="en",
        copyright=(
            "JPS Tanakh (1917) and Weymouth New Testament (1903). Both are in the public domain."
        ),
        footer_marker="JPS  [Online]",
    ),
    "SLT": PdfMakerTranslationConfig(
        code="SLT",
        name="Smith's Literal Translation",
        language="en",
        copyright="Smith's Literal Translation (1876) is in the public domain.",
        footer_marker="SLT  [Online]",
    ),
    "WBT": PdfMakerTranslationConfig(
        code="WBT",
        name="Webster's Bible Translation",
        language="en",
        copyright="Webster's Bible Translation (1833) is in the public domain.",
        footer_marker="WBT  [Online]",
    ),
    "WEB": PdfMakerTranslationConfig(
        code="WEB",
        name="World English Bible",
        language="en",
        copyright="The World English Bible is in the public domain.",
        footer_marker="WEB  [Online]",
    ),
    "YLT": PdfMakerTranslationConfig(
        code="YLT",
        name="Young's Literal Translation",
        language="en",
        copyright="Young's Literal Translation (1898) is in the public domain.",
        footer_marker="YLT  [Online]",
    ),
}


def get_config(code: str) -> PdfMakerTranslationConfig:
    """Return the config for a PDFMaker translation by code."""
    return PDFMAKER_CONFIGS[code]
