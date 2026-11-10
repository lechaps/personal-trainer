"""Deterministic, privacy-preserving synchronization with Apple Notes."""
from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unicodedata
import uuid

REPO = Path(__file__).resolve().parents[1]
DEFAULT_PRIVATE = REPO / "sport"
NOTE_DATE = re.compile(r"^(\d{4}-\d{2}-\d{2})(?:\s|\b)")
SC_ID = re.compile(r"(?m)^SC-ID: (sc-[a-f0-9-]{8,64})\s*$")


def private_dir() -> Path:
    root = Path(os.environ.get("PERSONAL_TRAINER_PRIVATE_DIR", str(DEFAULT_PRIVATE))).expanduser().resolve()
    repo = REPO.resolve()
    if (root == repo or repo in root.parents) and root != repo / "sport":
        raise ValueError("Dans le dépôt Git, seul le répertoire sport est autorisé pour les données privées")
    return root


def create_private_folder(path: Path) -> None:
    if path.exists() and path.is_symlink():
        raise ValueError("Répertoire privé symbolique refusé")
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.chmod(0o700)


def atomic_private_json(path: Path, value: dict) -> bool:
    encoded = (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
    create_private_folder(path.parent)
    if path.exists() and path.read_bytes() == encoded:
        return False
    fd, tmp = tempfile.mkstemp(prefix=".personal-trainer-", suffix=".tmp", dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(encoded)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return True


def load_snapshot(path: Path | None = None) -> dict:
    p = path or private_dir() / "notes.json"
    if not p.exists():
        return {"version": 1, "notes": {}}
    data = json.loads(p.read_text(encoding="utf-8"))
    if data.get("version") != 1 or not isinstance(data.get("notes"), dict):
        raise ValueError("Format de cache inconnu : arrêter et inspecter manuellement")
    return data


def digest(note: dict) -> str:
    # Do not use modification dates as the sole signal of change.
    b = json.dumps({"title": note["title"], "text": note["text"]}, sort_keys=True,
                   ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(b).hexdigest()


def merge_snapshot(old: dict, fetched: list[dict]) -> tuple[dict, dict]:
    if not isinstance(fetched, list):
        raise ValueError("Réponse Notes invalide")
    updated = dict(old["notes"])
    seen = set()
    stats = {"new": 0, "changed": 0, "unchanged": 0, "missing": 0}
    for note in fetched:
        if not isinstance(note, dict):
            raise ValueError("Note invalide")
        for key in ("id", "title", "text", "modified"):
            if not isinstance(note.get(key), str):
                raise ValueError(f"Propriété requise manquante : {key}")
        nid = note["id"]
        if not nid or nid in seen:
            raise ValueError("ID Notes manquant ou répété ; import annulé")
        seen.add(nid)
        h = digest(note)
        prior = old["notes"].get(nid)
        if not prior:
            stats["new"] += 1
        elif prior["digest"] == h and not prior.get("missing", False):
            stats["unchanged"] += 1
        else:
            stats["changed"] += 1
        updated[nid] = {**note, "digest": h, "missing": False}
    for nid, prior in old["notes"].items():
        if nid not in seen:
            updated[nid] = {**prior, "missing": True}
            stats["missing"] += 1
    return {"version": 1, "notes": dict(sorted(updated.items()))}, stats


def run_notes_jxa(operation: str, req: dict) -> dict:
    if sys.platform != "darwin":
        raise RuntimeError("Accès réel à Apple Notes disponible uniquement sur macOS")
    create_private_folder(private_dir())
    fd, req_name = tempfile.mkstemp(prefix=".request-", suffix=".json", dir=private_dir())
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(req, f, ensure_ascii=False)
        result = subprocess.run(
            ["osascript", "-l", "JavaScript", str(REPO / "jxa" / "notes.js"), operation, req_name],
            capture_output=True, text=True, timeout=90, check=False,
        )
        if result.returncode:
            # Avoid including application text/details in public logs by default.
            raise RuntimeError("Apple Notes a refusé l'opération. Vérifier le compte, le dossier et les permissions Automatisation.")
        return json.loads(result.stdout.strip())
    finally:
        Path(req_name).unlink(missing_ok=True)


def notes_request() -> dict:
    return {
        "account": os.environ.get("PERSONAL_TRAINER_ACCOUNT", "iCloud"),
        "folder": os.environ.get("PERSONAL_TRAINER_FOLDER", "Sport"),
    }


def import_notes(*, apply: bool, fixture: Path | None = None) -> dict:
    if fixture:
        fetched = json.loads(fixture.read_text(encoding="utf-8"))["notes"]
    else:
        fetched = run_notes_jxa("list", notes_request())["notes"]
    old = load_snapshot()
    merged, stats = merge_snapshot(old, fetched)
    if apply:
        stats["cache_written"] = atomic_private_json(private_dir() / "notes.json", merged)
    return stats


def normalized_status(text: str) -> str:
    lines = text.splitlines()
    for line in lines[:18]:
        if re.match(r"^\s*Statut\s*:", line, flags=re.IGNORECASE):
            value = line.split(":", 1)[1].strip().lower()
            value = "".join(c for c in unicodedata.normalize("NFD", value) if unicodedata.category(c) != "Mn")
            if value in {"terminee", "realisee", "fait", "faite"}:
                return "terminee"
            if value in {"prevue", "planifiee"}:
                return "prevue"
            if value in {"en cours", "encours"}:
                return "en_cours"
            if value in {"annulee", "reportee"}:
                return "annulee"
    return "non_confirmee"


def context_text(*, last: int = 6) -> str:
    notes = [x for x in load_snapshot()["notes"].values() if not x.get("missing")]
    sections = []
    for name in ("Profil & Objectifs", "Programme"):
        matches = [n for n in notes if n["title"].strip().casefold() == name.casefold()]
        if len(matches) > 1:
            raise ValueError(f"Plusieurs notes '{name}' : résolution manuelle requise")
        if matches:
            sections.append(f"## {name}\n{matches[0]['text']}")
    sessions = []
    for note in notes:
        match = NOTE_DATE.match(note["title"])
        if match:
            try:
                date.fromisoformat(match.group(1))
            except ValueError:
                continue
            sessions.append((match.group(1), note))
    sessions.sort(key=lambda x: (x[0], x[1]["title"]), reverse=True)
    for _, note in sessions[:last]:
        status = normalized_status(note["text"])
        sections.append(f"## {note['title']} [statut={status}]\n{note['text']}")
    return ("# CONTEXTE PRIVÉ PERSONAL-TRAINER — NE PAS COMMITER\n\n" +
            "Ne jamais confondre les objectifs prévus avec les résultats réalisés. "
            "Une note non_confirmée n'atteste pas d'une séance réalisée.\n\n" +
            "\n\n".join(sections) + "\n")


def slug(value: str) -> str:
    value = "".join(c for c in unicodedata.normalize("NFD", value.lower())
                    if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "-", value).strip("-")[:45] or "seance"


def new_draft(on: str, kind: str) -> Path:
    date.fromisoformat(on)
    uid = "sc-" + str(uuid.uuid4())
    draft_dir = private_dir() / "drafts"
    create_private_folder(draft_dir)
    path = draft_dir / f"{on}-{slug(kind)}-{uid}.txt"
    body = (f"{on} — {kind}\nSC-ID: {uid}\nStatut: prévue\n\n"
            "PROGRAMME PRÉVU\n- Exercice : séries x répétitions, charge, repos, RIR\n\n"
            "RÉSULTATS RÉELS (à compléter sur iPhone)\n- Exercice :\n\n"
            "Ressenti :\nFatigue :\n")
    with path.open("x", encoding="utf-8") as f:
        f.write(body)
    path.chmod(0o600)
    return path


def parse_draft(path: Path) -> dict:
    p = path.expanduser().resolve()
    drafts = (private_dir() / "drafts").resolve()
    if drafts not in p.parents or p.suffix != ".txt":
        raise ValueError("La proposition doit être un brouillon .txt de l'espace privé")
    text = p.read_text(encoding="utf-8")
    ids = SC_ID.findall(text)
    if len(ids) != 1 or text.count("SC-ID:") != 1:
        raise ValueError("Un seul marqueur SC-ID valide est requis")
    first = text.splitlines()[0].strip()
    if not NOTE_DATE.match(first):
        raise ValueError("Première ligne attendue : AAAA-MM-JJ — Type de séance")
    date.fromisoformat(first[:10])
    if normalized_status(text) != "prevue":
        raise ValueError("Seul un brouillon au statut 'prévue' peut être publié")
    return {"sc_id": ids[0], "title": first, "text": text}


def publish(*, path: Path, apply: bool) -> dict:
    record = parse_draft(path)
    record["title"] = f"{datetime.now(ZoneInfo('Europe/Paris')).date().isoformat()} draft"
    if not apply:
        return {"status": "dry_run", "sc_id": record["sc_id"], "title": record["title"]}
    result = run_notes_jxa("create", {**notes_request(), **record})
    if result.get("status") not in {"created", "already_exists"}:
        raise RuntimeError("Réponse Notes de publication inconnue")
    return result
