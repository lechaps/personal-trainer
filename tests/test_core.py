import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from personal_trainer.core import (
    context_text, digest, import_notes, load_snapshot, merge_snapshot,
    new_draft, normalized_status, parse_draft, private_dir, publish,
)


def note(id, title, text, modified="2026-11-09T10:00:00Z"):
    return {"id": id, "title": title, "text": text, "modified": modified}


class PersonalTrainerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.private = Path(self.tmp.name) / "private"
        self.env = patch.dict(os.environ, {"PERSONAL_TRAINER_PRIVATE_DIR": str(self.private)})
        self.env.start()
        self.addCleanup(self.env.stop)

    def fixture(self, notes):
        path = Path(self.tmp.name) / "fixture.json"
        path.write_text(json.dumps({"notes": notes}, ensure_ascii=False), encoding="utf-8")
        return path

    def test_idempotent_sync_does_not_rewrite_unchanged_cache(self):
        n = note("apple-1", "2026-11-09 — Jambes", "Statut: terminée\nSquat 3x8")
        file = self.fixture([n])
        first = import_notes(apply=True, fixture=file)
        self.assertEqual(first["new"], 1)
        self.assertTrue(first["cache_written"])
        before = (self.private / "notes.json").read_bytes()
        second = import_notes(apply=True, fixture=file)
        self.assertEqual(second["unchanged"], 1)
        self.assertFalse(second["cache_written"])
        self.assertEqual((self.private / "notes.json").read_bytes(), before)

    def test_modified_note_is_reimported_without_duplicate(self):
        original = note("apple-1", "2026-11-09 — Jambes", "Statut: prévue")
        import_notes(apply=True, fixture=self.fixture([original]))
        updated = note("apple-1", "2026-11-09 — Jambes", "Statut: terminée\n3x8", "later")
        stats = import_notes(apply=True, fixture=self.fixture([updated]))
        self.assertEqual(stats["changed"], 1)
        self.assertEqual(len(load_snapshot()["notes"]), 1)
        self.assertIn("3x8", load_snapshot()["notes"]["apple-1"]["text"])

    def test_absent_note_is_not_deleted_from_cache(self):
        import_notes(apply=True, fixture=self.fixture([note("a", "Profil & Objectifs", "Texte privé")]))
        stats = import_notes(apply=True, fixture=self.fixture([]))
        self.assertEqual(stats["missing"], 1)
        self.assertTrue(load_snapshot()["notes"]["a"]["missing"])
        self.assertNotIn("Texte privé", context_text())

    def test_duplicate_ids_abort_without_touching_cache(self):
        n = note("dup", "Profil & Objectifs", "x")
        f = self.fixture([n, n])
        with self.assertRaises(ValueError):
            import_notes(apply=True, fixture=f)
        self.assertFalse((self.private / "notes.json").exists())

    def test_dry_run_never_creates_cache(self):
        result = import_notes(apply=False, fixture=self.fixture([note("x", "Profil & Objectifs", "Confidentiel")]))
        self.assertEqual(result["new"], 1)
        self.assertFalse((self.private / "notes.json").exists())

    def test_context_never_claims_unknown_session_completed(self):
        import_notes(apply=True, fixture=self.fixture([
            note("p", "Profil & Objectifs", "Sport amateur"),
            note("s", "2026-11-09 — Haut du corps", "Développé 3x8"),
        ]))
        c = context_text()
        self.assertIn("[statut=non_confirmee]", c)
        self.assertIn("Sport amateur", c)

    def test_context_includes_combined_profile_and_optional_programme(self):
        import_notes(apply=True, fixture=self.fixture([
            note("p", "  PROFIL & OBJECTIFS  ", "Synthetic profile and goals"),
            note("plan", "Programme", "Synthetic training plan"),
        ]))
        context = context_text()
        self.assertIn("## Profil & Objectifs\nSynthetic profile and goals", context)
        self.assertIn("## Programme\nSynthetic training plan", context)

    def test_context_rejects_duplicate_combined_profiles(self):
        import_notes(apply=True, fixture=self.fixture([
            note("p1", "Profil & Objectifs", "Synthetic profile A"),
            note("p2", "profil & objectifs", "Synthetic profile B"),
        ]))
        with self.assertRaises(ValueError):
            context_text()

    def test_draft_publish_and_dry_run(self):
        draft = new_draft("2026-11-10", "Haut du corps")
        record = parse_draft(draft)
        self.assertIn("SC-ID", record["text"])
        self.assertEqual(normalized_status(record["text"]), "prevue")
        self.assertEqual(publish(path=draft, apply=False)["status"], "dry_run")
        with patch("personal_trainer.core.run_notes_jxa", return_value={"status": "created", "note_id": "n-1"}) as mocked:
            result = publish(path=draft, apply=True)
        self.assertEqual(result["status"], "created")
        self.assertEqual(mocked.call_args.args[0], "create")

    def test_reject_draft_outside_private_area(self):
        file = Path(self.tmp.name) / "stranger.txt"
        file.write_text("2026-11-10 — x\nSC-ID: sc-12345678\nStatut: prévue", encoding="utf8")
        with self.assertRaises(ValueError):
            parse_draft(file)

    def test_reject_private_root_inside_git(self):
        from personal_trainer.core import REPO
        with patch.dict(os.environ, {"PERSONAL_TRAINER_PRIVATE_DIR": str(REPO / "private")}):
            with self.assertRaises(ValueError):
                private_dir()

    def test_default_storage_is_sport_in_repository(self):
        from personal_trainer.core import REPO
        with patch.dict(os.environ):
            os.environ.pop("PERSONAL_TRAINER_PRIVATE_DIR", None)
            self.assertEqual(private_dir(), REPO / "sport")

    def test_sport_directory_is_allowed_in_repository(self):
        from personal_trainer.core import REPO
        with patch.dict(os.environ, {"PERSONAL_TRAINER_PRIVATE_DIR": str(REPO / "sport")}):
            self.assertEqual(private_dir(), REPO / "sport")

    def test_status_parses_accents(self):
        self.assertEqual(normalized_status("Statut: terminée"), "terminee")
        self.assertEqual(normalized_status("Statut: prévue"), "prevue")
        self.assertEqual(normalized_status("Sans statut"), "non_confirmee")


if __name__ == "__main__":
    unittest.main()
