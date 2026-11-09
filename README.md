# Personal Trainer — Apple Notes ↔ Codex, with no personal data in Git

[Version française](README.fr.md)

## Architecture

- **Apple Notes / Sport (iCloud)**: source of truth; a `Profil & Objectifs` note, an optional `Programme` note, then one dated note per session. Use the exact titles described under Note format.
- **Git**: source code, `AGENTS.md` instructions, the Codex Skill, and tests. **No real sessions or health information.**
- **Codex**: creates proposals in a private draft, then asks for approval before publishing.

## Requirements

- A Mac with Notes.app synced with your iPhone through iCloud.
- A regular folder named `Sport` directly under the `iCloud` Notes account, not a Smart Folder.
- Python 3.10+ (check with `python3 --version`).
- `osascript` on macOS, with permission for Terminal and/or Codex to control Notes under **Automation → Notes**.
- Local Codex access to the project and its private `sport/` folder.
- Text notes in Apple Notes: attachments, native tables, drawings, and locked notes are not supported in V1.

## Installation

1. Open the `personal-trainer` repository in Codex, then open a terminal at its root. No extra Python packages are needed.

```bash
python3 --version
python3 -m unittest discover -s tests -v
```

2. In Apple Notes, under the `iCloud` account, create a regular folder named `personal-trainer-Test` with sample notes named `Profil & Objectifs` and `2026-11-09 — Test`. Set up the terminal and test reading:

```bash
export PERSONAL_TRAINER_ACCOUNT="iCloud"
export PERSONAL_TRAINER_FOLDER="personal-trainer-Test"
python3 scripts/personal-trainer.py sync
```

On first access, allow Terminal or Codex to control Notes if macOS asks. If access is denied, check **System Settings → Privacy & Security → Automation**. Stop if syncing fails.

3. Follow the **Mac tests** section below, including publishing in the test folder, before using real data.

4. In Apple Notes, prepare your real `Sport` folder, with one note named `Profil & Objectifs`, and optionally `Programme`. Select that folder and import the notes:

```bash
export PERSONAL_TRAINER_FOLDER="Sport"
python3 scripts/personal-trainer.py sync --apply
```

The cache is saved in `sport/notes.json`, which is excluded from Git. Importing does not change Apple Notes. These environment variables apply to the current terminal; the defaults are `iCloud` and `Sport`.

To ask Codex for an analysis or a session, tell it to read `.agents/skills/personal-trainer/SKILL.md` and use the imported context. **Analyzing the context with Codex may send private data to the model service.** Publishing must wait for your explicit approval.

Installation does not require a commit. Enable the protection hook for this repository:

```bash
chmod +x hooks/pre-commit
git config --local core.hooksPath hooks
```

The hook runs `python3 scripts/git_guard.py` before each commit and blocks paths outside the allowlist, including `sport/`. It does not detect private data copied into an allowed file: stage only the files you need, explicitly, and always review their contents with `git diff --cached`. This setting is local and must be repeated for each new clone.

## Using this repository with Codex

Open this repository in Codex and ask in plain language, in French or English. Ask Codex to use the `personal-trainer` Skill in `.agents/skills/personal-trainer/SKILL.md`. It uses your `Profil & Objectifs` note and recent sessions to suggest training or review progress. Before a new analysis, update the history from Apple Notes; stop if syncing fails. Include your current fatigue, any pain, available time, and equipment when asking for training. Clearly confirm which sessions you completed: a planned note is not a completed workout.

Useful prompts:

- **Update the history:** “Import the latest Apple Notes into the private cache without changing the original notes.”
- **Next session:** “Use the personal-trainer Skill to prepare my next session from my latest history. I have 60 minutes at the gym, normal energy, and no pain. Include starting weights when supported by my history, sets, reps, rest, and target effort.”
- **Weekly plan:** “Use the personal-trainer Skill to plan this week. I can train Tuesday and Thursday for one hour and Sunday for 90 minutes. Balance strength, endurance, and recovery. No mountain biking this week.”
- **Performance review:** “Use the personal-trainer Skill to review my last four weeks. Compare confirmed results, highlight progress and fatigue, and state what the available data cannot tell us.”
- **Session feedback:** “I completed today's session. Here are my actual sets, reps, weights, duration, overall effort /10, and any pain: […]. Compare the plan with what I did, without preparing the next session yet.”
- **Save a draft:** “Save this proposal as a private draft in sport/drafts/, without publishing it.”
- **Publish an approved session:** “I approve this session. Publish it to Apple Notes.”

Codex may ask for essential missing details. Review the full session before approving publication. Publishing creates a new note; it does not update an existing one. Record your actual results in Apple Notes and set `Statut: terminée`, then update the history. Private context read by Codex may be sent to the model service, even though `sport/` is excluded from Git.

## Daily commands

```bash
# Read all notes in the folder (dry run: does not save the cache)
python3 scripts/personal-trainer.py sync

# Update the private cache in sport/notes.json (excluded from Git)
python3 scripts/personal-trainer.py sync --apply

# Private context for Codex analysis; keep any copies inside sport/
python3 scripts/personal-trainer.py context --last 10

# Create a proposal in sport/drafts/ and print its path
python3 scripts/personal-trainer.py new-draft --date 2026-11-10 --type "Upper body"

# Edit this PRIVATE draft with Codex, then check its format
python3 scripts/personal-trainer.py publish --draft "/PRIVATE/PATH/draft.txt"

# After explicit approval, publish to Apple Notes
python3 scripts/personal-trainer.py publish --draft "/PRIVATE/PATH/draft.txt" --apply
```

If you edit the published note on your iPhone (`Statut: terminée` plus results), the next `sync --apply` detects the change. The script **never replaces** an existing Apple Note. Publishing the same draft again with `--apply` returns `already_exists` when its SC-ID is found.

## Note format

The names and status values below stay in French because the code expects them. Translating this documentation does not change the parser.

### Profile and goals

Create one note named exactly `Profil & Objectifs`. A `Programme` note is optional. Include only the personal data you need.

### Session

The title must start with an ISO date, for example `2026-11-10 — Upper body`. For new sessions created by Codex, keep the `SC-ID: sc-...` line unchanged.

After completing a planned session, enter the results and replace `Statut: prévue` with `Statut: terminée` **in Apple Notes**.

Older notes without a status are marked `non_confirmee` (unconfirmed). The system does not assume they were completed.

## Configuration

Environment variables:

```bash
export PERSONAL_TRAINER_ACCOUNT="iCloud"
export PERSONAL_TRAINER_FOLDER="Sport"
# Default: sport/ at the project root; an external location is also possible
# export PERSONAL_TRAINER_PRIVATE_DIR="$HOME/Library/Application Support/personal-trainer"
```

## Mac tests — required before real use

1. In Apple Notes (iCloud account), create `personal-trainer-Test` with two sample notes: `Profil & Objectifs` and `2026-11-09 — Test`.
2. In Terminal, run `export PERSONAL_TRAINER_FOLDER=personal-trainer-Test`.
3. Run `sync --apply` twice and check that the second run reports `unchanged`.
4. Edit the test note on your iPhone, wait for iCloud to sync, then check that a new import reports `changed`.
5. Create a draft with `new-draft`, edit it locally, then publish to the test folder **after approval**.
6. Run `publish --apply` again for the same draft: it should return `already_exists`, with no duplicate.
7. Read the published note on your iPhone and check line breaks and accented characters. The JXA bridge may need changes depending on your Notes/macOS version.
8. Once the tests pass, set `PERSONAL_TRAINER_FOLDER=Sport` again.

## Privacy and limits

- Imports are stored in `sport/notes.json` and drafts in `sport/drafts/`. Git ignores `sport/`, and the commit guard rejects it.
- Old files in `~/Library/Application Support/personal-trainer/` are not moved automatically. The next `sync --apply` creates the cache at the new location unless `PERSONAL_TRAINER_PRIVATE_DIR` is set.
- The Git hook uses a path allowlist, but cannot prevent someone from copying sensitive content into an allowed source file. Always review `git diff --cached`.
- The local cache is a snapshot: it keeps notes that have disappeared, marks them `missing`, and leaves them out of the active context. Permanent deletion also requires handling local copies and backups.
- The cache is plain text in `sport/` by default (file permissions 0600, folder permissions 0700). Use FileVault and a suitable backup policy.
- Asking Codex to analyze the context may send data to the model provider. Keeping data out of Git does not keep it out of the AI service.
- Access to Apple Notes through JXA is not a stable official API. Check permissions, accounts, locked notes, and behavior on your macOS version.
- The script returns text only; rich content would need a V2.
- Duplicate detection when publishing depends on the `SC-ID` marker. If you change or remove it in Apple Notes, detection is no longer guaranteed.
- iCloud sync delays may make an existing note appear to be missing. Do not try creating it again until Notes has finished syncing on the Mac.
