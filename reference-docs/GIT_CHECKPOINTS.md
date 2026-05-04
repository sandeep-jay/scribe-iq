# Git checkpoints (revert / reference)

Use a **named branch + commit** before large UI or information-architecture experiments so you can return to a known state without hunting through history.

## Create a checkpoint

```bash
git checkout -b checkpoint/<short-label>
git add -A
# Optional: unstage generated dirs (e.g. backend/scribe_iq_backend.egg-info/) if they are not gitignored
git commit -m "checkpoint: describe what you are about to change"
```

- Keep **`.env`** and other secrets **gitignored**; do not commit real keys.
- Prefer **`*.egg-info/`** and similar build outputs in `.gitignore` so they never enter a checkpoint commit.

## Revert options

**Drop the experiment and work from `main` again:**

```bash
git checkout main
# Optional: remove the local checkpoint branch
git branch -D checkpoint/<short-label>
```

**Reset a feature branch back to a specific checkpoint commit:**

```bash
git checkout your-feature-branch
git reset --hard <checkpoint-commit-sha>
```

**Push the checkpoint to the remote for backup:**

```bash
git push -u origin checkpoint/<short-label>
```

**Continue development without moving the checkpoint needle:** branch from the checkpoint commit, for example:

```bash
git checkout -b feature/your-work checkpoint/<short-label>
# or: git checkout -b feature/your-work <checkpoint-commit-sha>
```

## Recorded checkpoint (this repository)

| Item | Value |
|------|--------|
| Branch | `checkpoint/pre-read-sources-codes-ui` |
| Commit | `aae2a40` — snapshot before **Read / Sources / Codes & map** patient IA work |

To return exactly to that tree: `git checkout checkpoint/pre-read-sources-codes-ui` or `git reset --hard aae2a40` on a disposable branch (do not reset shared `main` without team agreement).
