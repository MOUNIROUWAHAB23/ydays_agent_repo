#!/usr/bin/env python
"""Indexe les documents de `data/` dans la base vectorielle.

Usage :
    python scripts/ingest.py
    python scripts/ingest.py --documents ./mes_docs
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from copilote.config import configure_logging, settings
from copilote.rag import build_index


def main() -> int:
    parser = argparse.ArgumentParser(description="Indexation du profil (RAG).")
    parser.add_argument(
        "--documents",
        type=Path,
        default=settings.documents_dir,
        help="Répertoire contenant CV, rapports de projet, portfolio (.pdf/.md/.txt).",
    )
    args = parser.parse_args()

    configure_logging()
    try:
        nombre = build_index(args.documents)
    except FileNotFoundError as exc:
        print(f"[Erreur] {exc}", file=sys.stderr)
        return 1

    print(f"Index reconstruit : {nombre} chunks dans {settings.chroma_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
