#!/usr/bin/env python
"""Genere le rapport de reconciliation (reproductible par une commande).

Usage:
    python scripts/generate_report.py [--out rapport_reconciliation.md]
"""

import argparse
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import get_connection  # noqa: E402
from app.report import generer_rapport  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="rapport_reconciliation.md")
    args = parser.parse_args()

    with get_connection() as conn:
        contenu = generer_rapport(conn)

    Path(args.out).write_text(contenu, encoding="utf-8")
    print(contenu)
    print(f"\n(ecrit dans {args.out})")


if __name__ == "__main__":
    main()
