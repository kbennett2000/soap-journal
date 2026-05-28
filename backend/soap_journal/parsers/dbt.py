"""DBT parser CLI. Uses the shared PDFMaker-format algorithm.

Usage
-----
    python -m soap_journal.parsers.dbt <source.pdf> --out <output.json>
"""

from soap_journal.parsers._pdfmaker_translations import get_config
from soap_journal.parsers.pdfmaker_format import make_cli_main

_CONFIG = get_config("DBT")

main = make_cli_main(_CONFIG)

if __name__ == "__main__":  # pragma: no cover - thin shell
    raise SystemExit(main())
