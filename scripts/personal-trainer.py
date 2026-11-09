#!/usr/bin/env python3
"""CLI from repository root: python3 scripts/personal-trainer.py --help"""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from personal_trainer.core import context_text, import_notes, new_draft, publish  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Pont privé Apple Notes ↔ Codex")
    sub = parser.add_subparsers(dest="command", required=True)
    sync = sub.add_parser("sync", help="Importer les notes vers le cache privé local")
    sync.add_argument("--apply", action="store_true", help="Écrire le cache ; sinon dry-run")
    sync.add_argument("--fixture", type=Path, help="Fichier JSON fictif pour essais hors macOS")
    context = sub.add_parser("context", help="Afficher du contexte privé pour Codex")
    context.add_argument("--last", type=int, default=6)
    draft = sub.add_parser("new-draft", help="Créer un brouillon privé avant génération")
    draft.add_argument("--date", required=True)
    draft.add_argument("--type", required=True)
    pub = sub.add_parser("publish", help="Créer une note Apple Notes sans écraser l'existant")
    pub.add_argument("--draft", type=Path, required=True)
    pub.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "sync":
            print(import_notes(apply=args.apply, fixture=args.fixture))
        elif args.command == "context":
            if not (1 <= args.last <= 100):
                raise ValueError("--last doit être compris entre 1 et 100")
            print(context_text(last=args.last))
        elif args.command == "new-draft":
            print(new_draft(args.date, args.type))
        elif args.command == "publish":
            print(publish(path=args.draft, apply=args.apply))
    except (ValueError, RuntimeError, FileNotFoundError, OSError) as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
