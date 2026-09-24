---
description: Update the OpenAPI spec and regenerate/validate client libraries for a new Sonatype IQ Server version
argument-hint: <iq-version> <iq-server-url>
allowed-tools: Bash, Read, Edit, Write, WebFetch
---

## Inputs

- `$1` — Sonatype IQ Server version this update targets, e.g. `205.3` (matches the `1.<version>-01` shown in `spec/openapi.yaml`'s `info.version` and the `feat/iq-<version>` branch naming used by this repo's `detect-iq-release` workflow).
- `$2` — Base URL of a **running** Sonatype IQ Server instance to pull the spec from, e.g. `https://admin:password@iq.example.com:8071`. Embed credentials as `user:pass@host` in the URL — `update-spec.py` uses `requests`, which extracts and sends them as HTTP Basic Auth automatically. Never print, log, or commit this URL.

If either argument is missing, ask the user for it before doing anything else.

## Context to load first

Read these before making any changes, so you understand the established conventions instead of guessing:

- `update-spec.py` — the patch script. Note the `# vNNN Updates` comment blocks near the bottom: each past IQ release that broke client generation got a small, targeted, conditional patch (guarded by `if 'x' in json_spec[...]`) appended in its own block. You will likely need to add a new block in this same style, never rewrite earlier ones.
- `.github/workflows/detect-iq-release.yaml` — the automated version of this exact workflow (downloads IQ, starts it, runs `update-spec.py`, opens a PR). Mirror its branch name, commit message, and PR body conventions since this command does by hand what that workflow does against a throwaway CI-started server.
- `.github/workflows/build.yaml` — shows exactly how each of the three client libraries (go, python, typescript) is generated and validated (build + generated test suite). You need to reproduce these steps locally to confirm the new spec actually generates working clients before opening a PR.
- `go.yaml`, `python.yaml`, `typescript.yaml`, `common.yaml` — the `openapi-generator` batch configs used by `build.yaml`.
- `README.md` "Known Issues" section — points back at `update-spec.py` as the source of truth for spec quirks.

## Steps

1. **Pre-flight checks.**
   - `git status` — the working tree must be clean before creating a branch. If it isn't, stop and ask the user how to proceed (stash vs. commit vs. abort) rather than discarding anything.
   - Confirm you're on `main` and it's up to date with `origin/main`.
   - Confirm `docker`, `gh`, and `python` (with `requests` + `pyyaml` installed, per `detect-iq-release.yaml`'s `pip install requests pyyaml`) are available.
   - Sanity-check IQ Server reachability without leaking credentials into your visible output, e.g. `curl -sf -o /dev/null -w '%{http_code}' "$2/api/v2/endpoints/public"` and confirm it returns `200`.

2. **Create the working branch.**
   ```
   git checkout -b "feat/iq-$1"
   ```

3. **Fetch and patch the spec.**
   ```
   python update-spec.py "$2" "$1"
   ```
   This overwrites `spec/openapi.yaml`. Confirm the file's `info.version` now reads `1.$1-01` (or similar) and that the script printed no unexpected errors.

4. **Review the spec diff for new breakage, the same categories every prior `vNNN Updates` block in `update-spec.py` exists to fix:**
   - `git diff spec/openapi.yaml` — scan for: schemas referenced by `$ref` but not defined (or removed but still referenced), responses keyed only by `default` with no `200`, fields that flipped between nullable/non-nullable in a way that breaks strongly-typed clients, `date-time`-formatted fields (these have repeatedly needed downgrading to plain `string`), and duplicate `tags` entries.
   - Also diff against the *previous* version's spec (`git show HEAD:spec/openapi.yaml` before your branch, or `git log --oneline -- spec/openapi.yaml` to find the last `feat: Generated Spec from IQ ...` commit) to see what actually changed release-to-release, not just cosmetic reordering from the YAML dump.
   - Don't guess blindly — the fastest signal is step 5: let the generator and its test suite tell you what's actually broken, then patch precisely that.

5. **Regenerate and validate all three client libraries locally**, reproducing `build.yaml`:
   ```
   mkdir -p out/go out/python out/typescript
   docker run --rm -v "$(pwd):/local" openapitools/openapi-generator-cli:v7.16.0 batch --clean /local/go.yaml /local/python.yaml /local/typescript.yaml
   ```
   Then, matching `build.yaml`'s `validate-*` jobs:
   - **Go**: `cd out/go && go build -v ./ && go get github.com/stretchr/testify/assert && go test -v ./test/`
   - **Python**: `cd out/python && poetry install --no-root && poetry build && pip install -r test-requirements.txt && poetry run pytest`
   - **TypeScript**: `cd out/typescript && npm i && npm run build`

6. **If any generation, build, or test step fails**, diagnose whether the root cause is a spec defect in the same family as an existing `vNNN Updates` block (missing/incomplete schema, bad nullability, unsupported format, duplicate tag, etc.). If so:
   - Add a new, clearly-labeled `# v$1 Updates` block to `update-spec.py`, following the exact structure and defensive `if`-guards of the existing blocks (never delete or restructure earlier blocks — IQ Server versions are cumulative and older instances may still be run against this same script).
   - Re-run step 3 (`update-spec.py`) and step 5 (regenerate + validate) until all three libraries build and their generated test suites pass.
   - If a failure looks unrelated to the spec (e.g. Docker/network/tooling issue), fix the environment instead of patching the spec.

7. **Clean up generated output** — `out/` is not meant to be committed (confirm via `.gitignore`); remove or leave it untracked, but do not `git add` it.

8. **Stage and commit.**
   - `git add spec/openapi.yaml` and, if you touched it, `update-spec.py`.
   - Double-check `git status`/`git diff --staged` shows only those files — never stage `out/`, the IQ credentials, or unrelated local changes.
   - Commit message, matching the existing history's convention exactly:
     ```
     feat: Generated Spec from IQ $1
     ```

9. **Push and open a PR** — this is visible, shared-state work, so confirm with the user before this step (branch name, target IQ version, and whether `update-spec.py` was patched) unless they've already told you to proceed autonomously:
   ```
   git push -u origin "feat/iq-$1"
   gh pr create --title "feat: Generated Spec from IQ $1" --base main --body "$(cat <<'EOF'
   ## Sonatype IQ Server Spec Update

   Manually generated via the `/update-iq-version` command against a local Sonatype IQ Server v$1 instance.

   | | |
   |---|---|
   | **Sonatype IQ Server version** | $1 |

   ### Before merging

   - [ ] Review `spec/openapi.yaml` diff for unexpected changes
   - [ ] Confirm all CI checks pass below
   EOF
   )"
   ```
   If `update-spec.py` was patched, call that out explicitly in the PR body/description (what broke, what you changed) so the reviewer isn't surprised by a diff outside `spec/openapi.yaml`.

10. **Report back**: summarize the new version, whether `update-spec.py` needed a new patch block (and why), and the PR URL. Do not merge the PR yourself — this repo's actual releases happen via `semantic-release` off commits to `main` per `README.md`, after human review.

## Guardrails

- Never echo the IQ Server URL or credentials from `$2` back into command output, commit messages, or the PR.
- Don't touch `.github/workflows/detect-iq-release.yaml`, `build.yaml`, or `release.yaml` as part of this task unless the user separately asks you to change the automation itself.
- Don't add new `openapi-generator` languages, bump the pinned `OPEN_API_GENERATOR_VERSION`, or restructure `update-spec.py`'s existing patch blocks — stay scoped to landing this one IQ version bump the same way every prior one in `git log` was landed.
