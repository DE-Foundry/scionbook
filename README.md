# Scionbook

![Scionbook logo](assets/scionbook-logo.jpg)

AI-assisted session planner and progress tracker for FFXIV, built on your Lodestone data.

Works through file-based prompts with your chosen assistant; no AI-provider SDK or model API key is required.
See [assistant setup](docs/assistant-setup.md) for capabilities and optional client integrations.

Includes character setup, saved snapshots, progress recaps, and skills for inventory, markets, gearing,
and hunts. One character per checkout; no player data ships with the project. English Lodestone markup
is supported. Private data requires the player's own authenticated session.

## Lodestone endpoint and language

Scionbook deliberately uses `https://na.finalfantasyxiv.com/lodestone` for setup and scraping. This is
an English website choice, not a restriction to NA character Worlds; home World and data center still
come from the verified profile. Official regional profile URLs are accepted as character-ID input, then
looked up on the NA English host. The endpoint and request identity are shared in `scionbook_http.py`.

Sign in on **na.finalfantasyxiv.com** and obtain the session cookie there for private data. Other regional
endpoints and localized quest/job names have not been validated by these parsers and are not configurable
in this release. Do not replace the hostname and assume localized parsing or authentication will work.
All Python HTTP clients identify themselves as `Scionbook/1.0`; the scraper does not impersonate Chrome.

## Disclaimer

Scionbook is not affiliated with or endorsed by Square Enix. Users must provide their own
authenticated Lodestone session to access private character data. Scraping and use of this tool are
at your own risk.

## Choose an installation method

Use a **release ZIP** if you want to run Scionbook with an agent without managing Git, or a **personal
fork** if you want your own source repository and upstream updates. Both keep character data local and
untracked. Contributors use a separate clone and policy-named development branches.
See [installation and updates](docs/installation.md) for steps, agent prompts, and preserving saved state.

## Get started

Requirements: Python 3.10+ with IANA timezone data, internet access, and an assistant able to read the local
workflow instructions and saved files. Workflows live in `.agents/skills/` and can be read directly;
native skill discovery is optional.
Codex discovers `.agents/skills/`; Claude Code uses `.claude/skills` (a link in Git checkouts, ordinary files in release ZIPs) and `CLAUDE.md`,
with `/setup` instead of `$setup`. Other clients can read the named file directly.
The requirements install `tzdata` on Windows for IANA timezone support. Open the repository folder in your
assistant and run the following from that folder. Skills are instructions for the assistant, not shell commands.

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

Windows PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Use the virtual environment's Python for every helper below. If activation is unavailable, invoke
`.venv/bin/python` directly, or `.\.venv\Scripts\python.exe` on Windows. In an activated Windows environment,
use `python` in place of `python3`. Optional client launchers have their own requirements; the portable workflow needs none of them.
The optional CLI launchers require Bash and the selected Codex or Claude Code CLI.

Open a fresh **Repository Maintainer** chat with repository read/write access and send:

```text
Read AGENTS.md and follow .agents/skills/setup/SKILL.md for Character Name on Home World.
```

Setup resolves the exact name/home-world match using Lodestone, verifies its profile, saves the character
ID and world/data center, collects timezone/preferences, initializes neutral local files, and performs the
first validated refresh. A profile URL is accepted if search is unavailable or ambiguous. It does not guess
from a partial match. Repeating setup preserves reports; another character needs another checkout.

The helper can also be used directly (it initializes configuration; `$sync` performs the refresh):

```bash
python3 scionbook_setup.py --name "Character Name" --world "Home World" --lookup-only
python3 scionbook_setup.py --name "Character Name" --world "Home World" --timezone UTC --mode full
```

Choose `--mode public` for public profile/job information and available public collections/achievements
without a cookie. Public mode cannot establish private quests, currencies, or retainer holdings. For full
mode, follow [authentication](#authentication) before the first sync. The assistant's `$setup` includes that
first sync; running `scionbook_setup.py` alone does not. Setup is session-ready only after the chosen refresh
validates; a configured character alone is not a fresh snapshot.

On a setup rerun, retain the existing timezone, mode, preferences and reports unless the user changes them.
To change characters, use a separate checkout and setup there. To change full/public mode for the same
character, rerun setup with the requested mode; retained private history remains historical in public mode.

## Two independent chats

Use the same assistant or different providers for each role; shared local files carry durable state.

- **Session Planner:** open a fresh chat with read-only file access and send
  `Read AGENTS.md and follow .agents/skills/start-session/SKILL.md.` New gameplay reports stay in
  that conversation. Follow recap-session when finished to produce a recap for review.
- **Repository Maintainer:** use a separate chat with repository read/write access. Follow
  `.agents/skills/apply-recap/SKILL.md` with the supplied recap to save reports. Follow
  `.agents/skills/sync/SKILL.md` only when explicitly requesting a refresh; setup includes its first refresh.

Neither role reads the other's transcript or uses cross-chat memory. Copy only the approved recap into
apply-recap, then use a fresh startup prompt for the next role. A prompt is not a save or a launched chat.
See [manual handoffs](docs/chat-handoffs.md) and [assistant setup](docs/assistant-setup.md), including
what to do when the assistant only supports uploaded files. Optional [Codex launchers and draft links](docs/integrations/codex.md)
are separate conveniences. They are not required by the Python tools or shared workflows.

Optional CLI examples (run in a user-accessible terminal):

```bash
SCIONBOOK_CLIENT=claude bash scripts/scionbook-chat session
python3 scionbook_handoff.py session --client claude --confirmed
```

Use `--confirmed` only after explicit approval of that transition. See [Claude Code](CLAUDE.md)
and [handoffs](docs/chat-handoffs.md) for permission and save-verification boundaries.

## Everyday workflow

See the [skill guide](docs/skills.md) for all 11 skills, copyable example prompts, required inputs,
which chat to use, and what gets saved. `$name` below is optional shorthand: in any assistant,
send `Read .agents/skills/<name>/SKILL.md and follow it` with your request.

| Step | Where | Action and result |
|---|---|---|
| First use | Maintainer, file read/write | `$setup Character Name on Home World` initializes local files and validates the first snapshot. |
| Begin or continue play | Session, read-only | `$start-session` reads saved sources; `$tasks` tracks new progress in this conversation. |
| Review inventory or markets | Either role, analysis only | `$inventory-cleanup` or `$market-update` reads saved holdings and protection; public prices may be checked separately. |
| End play | Session | `$recap-session` produces the complete recap and offers the available handoff. Nothing is saved by generating a recap. |
| Save reports | Maintainer | `$apply-recap` with the recap saves reports/preferences/checklist outcomes. Paste the recap into the destination chat before submitting. |
| Refresh character data | Maintainer | Request `$sync` after Lodestone updates. It validates and reconciles the snapshot, history, report, and configured crafting protection. |
| Return to play | Fresh Session chat | Open a fresh read-only chat and submit the Session startup prompt. |

In a chat already assigned a role, invoking the other role's skill does not reset context. Open a fresh
chat using the handoff instead. Reusing an existing Session chat is also possible: ask it to reload updated
files, preserving its newer conversation reports. This is a reload, not a clean-context transition.

For a first crafting keep list, ask Maintainer to **set up crafting-material protection from my saved levels
and quest history**. It researches the missing references once and saves the version 2 plan. Request sync
explicitly to produce the matching cleanup report; see [crafting protection](docs/crafting-protection.md).
A request to apply a recap and sync together authorizes both; a recap merely mentioning a needed sync does not.

## Specialist skills

| Skill | Use it for |
|---|---|
| `$inventory-cleanup` | Storage review, consolidation, material protection, keep/sell/vendor/discard advice |
| `$market-update` | Listings, current prices, recent sales, repricing and per-retainer capacity |
| `$gear-planner` | Intended-job upgrades, item-level gates, currency costs and acquisition paths |
| `$hunt-planner` | Hunts ordered to reduce travel, with levels, locations, entry points and job suitability |

These skills analyze and recommend; they do not execute in-game actions. Private character refresh belongs
to Maintainer sync. Public market/game-reference lookups can support either role. Personal policies such as
liquidation, retainer ordering, platform/controller, spoiler tolerance, and goals live in local preferences.

## Local state and privacy

`scionbook.json` contains version, character_id, name, world, data_center, timezone, mode, and preferences.
The Python tools read configured identity by default. The report also reads the configured mode:
`public` skips credentials and private pages; `full` requires a nonblank cookie. `--mode full` or
`--mode public` overrides mode for one run without changing configuration; `--anon` is an alias for
`--mode public`. Supplying `--id`, `--world`, and `--dc` together uses a standalone identity and defaults
to full mode unless explicitly overridden. Cookie options conflict with public mode and cause an error;
an ambient LODESTONE_COOKIE is simply unused in public mode. The standalone quest-history scraper
also requires configured full mode for `--cookie-env`; `--from-status` can render saved complete history
without authenticating.
`scionbook_report.py` accepts `--config PATH` or an explicit complete
`--id ID --world WORLD --dc DC` triple; partial identity overrides are rejected to avoid mixed-character pricing.

Ignored player files:

- `scionbook.json`: identity and preferences, never credentials.
- `status.json`: generated snapshot; check fetched_at_utc, notes, and still_not_available.
- `cleanup.md`: matching generated inventory/pricing report (empty if there is no report).
- `quest_history.md`: complete private quest history, generated only from a validated full pull.
- `SCIONBOOK_MEMORY.md`: dated player reports and goals, initialized from templates/.
- `SCIONBOOK_DAILY_WEEKLY_CHECKLIST.md`: reusable routines and separate dated outcomes, initialized from templates/.
- `quest_turnins.json`: persistent crafting quest research, verified turn-ins, and explicit keeps.
- `quest_mats.json`: current protected materials with reasons, quest states, and reusable recipe cache.
- `.scionbook-tmp/` and `raw/`: refresh staging and optional debug dumps.
- `local/`: custom persistent outputs, recap exports, and backups with arbitrary filenames.
- `.cache/` and `cache/`: repository-local caches; the scraper's default item cache lives outside the repo
  at `~/.cache/scionbook/`.

The player filenames above are ignored at any directory depth, including suffix backups such as
`status.json.bak` and `cleanup.md~`. Only the two exact neutral source files under `templates/` are
exceptions, together with synthetic files under `tests/fixtures/`. Never put player data in that fixture
directory. Put custom-named outputs from `--out`, `--report`, `--cache`, `--config`, or `--dump` under
`local/` (create it first), or use `.scionbook-tmp/` for refresh staging. Git cannot recognize player data
by its contents; an arbitrary filename elsewhere needs its own ignore rule.

Shared instructions, skills, code, neutral templates, and player-independent unlocks.json are tracked.
There is no asks.md/decisions.md workflow. Sync saves locally by default; no automatic commit or push.
Never commit character identities, profile links, account data, personal information, preferences, or
player reports, including on private branches. Backups must remain outside this repository and its history.

For a clean, player-free repository, use `python3 scripts/export_release.py DESTINATION`. It exports only the
committed tree at HEAD into a new repository with no prior history, refuses tracked player-state files, and
scans for identifying terms taken from your local configuration and snapshot plus any denylist you supply.
Pushing or copying `.git` carries the full history. See [releasing](docs/releasing.md).

## Move to a new directory without another sync

To continue with the **same character and saved snapshot**, copy the project source into the new directory,
then bring over the local player files below. A clone or Git archive alone does not include them because
they are ignored. Copy from the working directory that actually contains your saved state, not an empty
or cleaned checkout.

| File | When to copy |
|---|---|
| `scionbook.json` | Required: character ID, home World, mode, timezone, and preferences. |
| `status.json` | Required: the last validated character snapshot. |
| `SCIONBOOK_MEMORY.md` | Required: saved progress, goals, and player reports. |
| `SCIONBOOK_DAILY_WEEKLY_CHECKLIST.md` | Required: routines and dated outcomes. |
| `quest_history.md` | Copy with a full-mode snapshot; it may be absent in public mode. |
| `cleanup.md` | Copy the matching generated inventory/market report when present. |
| `quest_turnins.json` | Copy if crafting protection is configured: researched quests and explicit keeps. |
| `quest_mats.json` | Copy with the crafting plan: protected materials, reasons, and cached recipes. |

1. Finish any active save or sync in the original directory. If progress exists only in a Session chat,
   use `$recap-session` and apply that recap in Maintainer before copying; applying it does not require sync.
2. Copy the files above into the **root of the new project**, alongside its Python files. Keep them together
   from the same checkout so the snapshot, history, cleanup report, and crafting protection match. Use a
   fresh destination without another character's state; do not overwrite newer reports with an older copy.
3. Recreate the Python environment using [Get started](#get-started). Keep the shared source files,
   including `.agents/`, `.claude/`, `.codex/`, `CLAUDE.md`, `.gitignore`, `SCIONBOOK_INSTRUCTIONS.md`, and `standards.md`.
   Do not copy `.venv`, `.git`, credentials, raw dumps, or temporary handoff/staging files. Custom saved
   outputs under `local/` are optional; carry over only those you want to retain.
4. Open the new directory in a fresh read-only chat and send `$start-session`. It loads the copied state;
   **neither `$setup` nor `$sync` is needed merely because the directory changed**. A Lodestone session
   cookie is not needed to read saved files; authenticate again only when a later full sync is requested.

Copying preserves the original snapshot timestamp; it does not make stale data fresh or update an old
report to new code behavior. A later sync may still be needed after gameplay changes. If the required
files are missing, recover them from your existing working copy or backup; the neutral templates do not
contain your progress. If no saved snapshot exists, complete setup and its initial sync instead.

## Authentication

Log into the English Lodestone as the intended character. In browser developer tools, find the `ldst_sess`
cookie for `na.finalfantasyxiv.com`. It provides access to private pages; keep it out of chat, configuration,
files, logs, Git, and shell history. Set LODESTONE_COOKIE with hidden input, for example in Bash:

```bash
read -r -s -p 'Lodestone cookie: ' LODESTONE_COOKIE
export LODESTONE_COOKIE
```

In zsh, use `read -r -s 'LODESTONE_COOKIE?Lodestone cookie: '` then export it. An environment variable is
available to commands started from that shell; setting it there does not update an already-running desktop
app. Start a local-capable assistant from that shell if it supports environment inheritance. For the optional
Codex CLI adapter, `bash scripts/scionbook-chat maintainer` does this. The Session Planner does not need the cookie; run it from a shell without that variable.
Do not paste a cookie into an app chat to work around missing environment inheritance.

Alternatively, run the scraper yourself in a visible terminal without `--cookie-env`; its hidden prompt
works without storing a cookie in shell history. Blank input or an empty credential option aborts a full
refresh before any network request or output write. Public mode must be configured or explicitly selected;
there is no automatic downgrade. Have Maintainer validate staged outputs before installing them.
The helper may expose `--cookie`, but do not use it: command arguments/history can retain the credential.
A missing or expired cookie must be replaced for full mode. A pricing/network/markup failure alone does
not establish that the cookie expired.

## Scraper tools

Run commands from the repository root. The sync skill stages and validates outputs before replacing the
canonical set. Use the [sync skill](.agents/skills/sync/SKILL.md) for the complete validation/install
procedure. Direct helpers do not reconcile prose reports, install a complete validated set, or offer handoffs.
For an independent full-mode development fetch, create `.scionbook-tmp/` first and run:

```bash
python3 scionbook_report.py --cookie-env --quest-pages 100 --recent-quests 0 --out .scionbook-tmp/status.json --report .scionbook-tmp/cleanup.md --quest-mats-out .scionbook-tmp/quest_mats.json
python3 scionbook_quest_history.py --from-status --status .scionbook-tmp/status.json --out .scionbook-tmp/quest_history.md
```

For a public development fetch, use a separate output name and do not render private history:

```bash
python3 scionbook_report.py --anon --no-retainers --out .scionbook-tmp/public-status.json --report .scionbook-tmp/public-cleanup.md
```

These commands leave the canonical snapshot/report/history untouched. Inspect the staged results before
replacement; a zero exit status alone does not prove authenticated completeness. `--quest-mats-out` is
written only when a version 2 plan successfully reconciles; never install a leftover from an earlier run.

`--quest-pages` is a bound, not a completeness guarantee. Increase it until retained quests equal the known
total. The history renderer refuses incomplete data and preserves its previous output. Additional flags:
`--fast` skips achievements/collections, `--no-pricing` keeps unpriced inventory unknown, `--refresh-items`
refreshes the shared item-name cache, and `--dump raw --probe` captures diagnostic HTML locally.
The report is always rewritten when `--report` is supplied, including when no inventory report exists.

The snapshot includes jobs, equipped-job gear attribution, quests, currencies/reputation, collections,
retainer inventory/listings/sales/ventures, pricing verdicts, and run-specific availability notes. Missing
fields do not prove zero. Unequipped gear, bags/armory/saddlebag/dresser contents, and many weekly states are
not exposed. Public profile data may lag gameplay even after a fresh fetch.

Inventory and current listings are disjoint; recent sales are already gone. Market capacity is per
retainer. Realistic proceeds are constrained by sale depth, not simply price multiplied by all stock.
Treat unresolved items and missing pricing evidence as unknown in cleanup advice; lack of a market price
is not proof that an item is worthless. Known market-prohibited items may still have vendor value. The
scraper filters pricing requests by Universalis marketability and warns if the marketability list is
unavailable. Selling proceeds and liquidity estimates use the configured home World only. When its price
is missing, a usable DC price is labeled **Non-home-World price**, with its source and unit price. You can
use it as a provisional starting listing price on your home World; local proceeds and sale speed remain
unestimated. If neither scope has a usable price, the item remains unknown. Other Worlds/DCs are never
selling destinations. Existing saved reports retain their old output until the next explicitly requested sync.
Material protection must match confirmed or inferred unfinished quests and explicit crafting keeps.

## Optional quest-material protection

Crafting materials are saved data, not conversation context. `quest_turnins.json` version 2 records
researched quest IDs, levels, prerequisites, turn-ins, source links, and explicit keeps. `quest_mats.json`
stores the recipe cache and current keep list with a reason for each material. See the
[data format and workflow](docs/crafting-protection.md).

Full sync automatically reconciles a version 2 plan with job levels and complete quest history: newly
eligible quests add materials; completed quests release their unique materials; shared materials stay
protected while another quest or explicit keep needs them. Level-limited keeps expire at their target level.
A level increase alone does not complete an older quest. Missing references are researched once and saved.

To reconcile an existing complete snapshot without scraping Lodestone:

```bash
python3 scionbook_quest_mats.py --status status.json --turnins quest_turnins.json --out quest_mats.json
```

Cached recipes are reused; only missing recipes are fetched. Use `--refresh-recipes` for a deliberate
recipe-data refresh. Invalid/incomplete history or failed recipe lookups preserve the prior protection file.
The standalone command updates protection only; the next authorized sync generates matching inventory advice.
Legacy job -> level -> item-name mappings still work without `--status`, but cannot automatically retire
completed quests; migrate them using verified quest references, never invented IDs.
`unlocks.json` remains separate shared reference data. See the [coverage review and contribution rules](docs/unlock-coverage.md); absence from this partial mapping never means content is locked.

## When a workflow cannot finish

- **Character lookup is ambiguous or blocked:** supply the official Lodestone profile URL; do not choose a fuzzy match.
- **Setup has configuration but no validated snapshot:** resume `$sync` in Maintainer after resolving credentials or fetch errors; do not reinitialize progress.
- **Quest history is incomplete:** increase the page limit and validate the known total. Preserve the last complete canonical files.
- **Crafting references have gaps:** research only missing tiers/items, preserve explicit keeps, and disclose uncovered special quests. Missing coverage is not permission to discard materials.
- **A supported client draft opens without recap text:** paste the displayed recap after “Recap to apply:” before Send. The link intentionally carries no gameplay data.
- **A save or sync fails:** report any partial work, preserve previous validated sources, and resolve the failure before a success handoff. Do not treat a prepared link as a completed save.

## Development

```bash
python3 -m pip install -r requirements-dev.txt
python3 -m pytest tests/
```

Tests use synthetic HTML fixtures retaining parser edge cases without captured accounts, buyers, inventory,
or quest history. Setup tests cover exact matches, ambiguous/missing profiles, configuration, repeat setup,
and prevention of cross-character overwrites. External services: Lodestone, Universalis, the Teamcraft item
name database, and XIVAPI for optional recipe/vendor data. No credentials are needed for the test suite.

[GitHub Actions](.github/workflows/tests.yml) runs the suite on pushes, pull requests, and manual dispatch:
Python 3.10 and 3.14 on Ubuntu, plus Python 3.14 on macOS and Windows. The workflow installs `requirements-dev.txt`
and runs `python -m pytest tests/ -q` with read-only repository permissions and no account secrets.
Workflow linting, dependency auditing, Conventional Commit PR-title validation, and extracted-ZIP
installation checks on Linux/Windows supplement the test suite. Tests also run weekly; CodeQL scans
Python and Actions through GitHub default setup. See [public-release controls](docs/public-release.md).
After tests, quality checks, and package checks pass on a push to `main`, a separate job with write permission publishes the versioned ZIP and
checksum, starting at `0.1.0`, and retains the current plus three previous releases. PRs, feature branches,
and personal forks do not publish releases. See [automatic publication](docs/releasing.md#automatic-publication-after-merge).
These are offline fixture tests, not live Lodestone compatibility checks. The optional Bash launchers
(Codex and Claude Code, using stub executables) are tested on Linux and macOS; Windows skips those
adapter tests and the POSIX symlink fixture, while testing Python tools and actual ZIP extraction.

Releases are versioned ZIP archives with checksums; keep the current version plus three previous
versions. Build and review them using [releasing](docs/releasing.md). A fresh-history export is optional for
checkouts whose history should not be published.

## Contributing and public releases

See [CONTRIBUTING.md](CONTRIBUTING.md) for development and provider-neutral workflow conventions,
[SECURITY.md](SECURITY.md) for private reporting guidance, and [release preparation](docs/releasing.md)
for publication checks. Any imported development history needs a privacy review before public release;
current ignore rules do not remove earlier player data.

## License

Licensed under the [MIT License](LICENSE). Copyright (c) 2026 DE Foundry.
