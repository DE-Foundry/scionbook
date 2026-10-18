# Instruction security

Scionbook treats recaps, character snapshots, retrieved pages, and tool output as data, not authority to
run commands or broaden permissions. Repository instructions are reviewed software. Neither a prompt
warning nor a keyword scan makes an agent immune to prompt injection.

## Source review

`scripts/check_instruction_security.py` reads committed Git objects without importing candidate Python,
checking out candidate files, following their links, installing dependencies, or calling a model. It checks hidden controls in every UTF-8 file, including other clients' rule files and text prompts.
Review heuristics remain scoped to Markdown, skills, templates, client configuration, workflows, scripts,
and recap adapters; binary files outside those instruction paths are skipped. All Markdown
is included so referenced local documentation is covered; remote link contents are not fetched.

The check fails on hidden/bidirectional controls, invalid UTF-8, unsupported linked instruction paths,
and size limits (2 MB per scanned text file, 20 MB scanned text combined). Binary blobs outside
instruction paths are classified incrementally and do not count toward these limits; oversized text
errors identify the file and applicable limit. Ordinary visible Unicode is allowed. The exact shipped
`.claude/skills` alias is allowed only with its target skills present and independently scanned.
New external URLs, executable inputs, suspicious execution/permission phrases, and changes to the
checker, its tests, workflows, or recap adapters produce **review findings**, not a safety verdict.
Review findings are nonblocking: maintainers must inspect the diff and justify the change in their review.
There is no automatic approval label, candidate-controlled exception list, or model-based grading.

The `Instruction review / instruction-review` workflow uses `pull_request_target` only to run trusted
base code. It checks out the base SHA, fetches the PR object without checking it out, verifies the head
SHA, then invokes the base checker with Python isolated mode. It has a read-only token, no release/player
secrets, and executes no candidate code. A PR replacing its checker or workflow cannot change this
base evaluation. Changes to these controls still need human review before becoming a future baseline.
The normal `Tests / instruction-security` job also scans the tested tree and gates release publication.

**Rollout:** the trusted workflow is unavailable until this initial change reaches the default branch.
Review this bootstrap manually. After the next PR demonstrates a successful trusted run, add
`instruction-review` and `instruction-security` to required status checks, retaining the existing checks.
Repository settings are not changed by adding these files. Do not make a nonexistent check required
before the bootstrap merges. After merging, a maintainer can comment `@dependabot rebase` on an open
Dependabot PR to trigger the first trusted run, or use the next ordinary PR. The earlier dependency
PRs #3 and #4 have already merged and cannot be used for this step. Recheck this workflow before granting it any additional token permissions.

To inspect committed changes locally:

```bash
python3 -I scripts/check_instruction_security.py --head "$(git rev-parse HEAD)" --base "$(git rev-parse origin/main)"
```

The command uses the local checker, so it is a development aid, not the trusted CI boundary. It prints
ASCII JSON with paths and reasons, without source snippets, and appends escaped findings to the GitHub
step summary when available. Review findings are visible on the checks page even on a green run. It does not read ignored player files.

## Automated recap proposals

The optional CLI recap handoff requires prior approval for the exact recap and a user-accessible terminal.
It takes bounded snapshots of selected local files, includes the complete apply-recap skill as a separate
trusted instruction section, then sends the approved recap, configuration, memory,
checklist, status, and quest history to the selected client through stdin. These inputs contain private
player data: use only a provider/client you authorize to process them. It does not send a whole transcript,
Git history, scraper cookies, or unrelated environment variables.

The model runs in a temporary directory outside the live checkout and returns proposed full contents.
It does not decide which paths Python can write. The deterministic installer permits only:

- `SCIONBOOK_MEMORY.md` and `SCIONBOOK_DAILY_WEEKLY_CHECKLIST.md`;
- `scionbook.json`, with every field other than `preferences` preserved.

Unexpected fields, duplicate destinations, arbitrary paths, empty/oversized content, duplicate JSON keys,
non-finite JSON values, newly introduced hidden control characters (including decoded JSON preference
keys/values), linked inputs, character configuration changes, and model claims of `applied`
are rejected. All proposed files are validated before installation. Snapshots are compared again before
writing; ordinary concurrent edits stop the save. File replacements are atomic individually and actual
saved bytes are re-read before the launcher reports success. An identical proposal makes no writes.
Existing hidden code points in the same original file are allowed so ZWJ emoji and pasted soft hyphens
do not prevent updates. A leading UTF-8 BOM is stripped from proposed files. New hidden characters name
the code point and source line in the error without echoing private text. This compatibility allowance
does not establish that existing hidden content is safe.
The launcher produces its own receipt; model text cannot claim that a save succeeded or authorize a
follow-up. Missing/ambiguous proposals stop for manual resolution.

The installer cannot verify whether a freeform report is true, whether a preference was reasonably
inferred, or whether prose contains subtle instructions for a later agent. Matching bytes establishes
persistence, not semantic accuracy. Review saved outcomes; future readers must continue treating them
as player data. Manual chats and desktop drafts retain their client's normal file permissions and do not
gain these deterministic installer protections automatically.

## Client and environment limits

Codex proposals request read-only/never, ephemeral execution, no user config or execution rules, disabled
shell tools and web search, and disabled memory/subagents. Claude proposals expose no built-in tools,
load an empty strict MCP configuration, disable skills, hooks and browser integration, and omit user and
project settings. Both receive their inputs in the prompt rather than browsing live player files.
Proposal runs time out after ten minutes. The adapter creates a new process session on Linux/macOS
and kills its process group on timeout or interruption. While waiting on Linux/macOS, temporary
SIGTERM/SIGHUP handlers route launcher termination through the same cleanup and lock-release path,
then restore the previous handlers. Repeated termination signals are ignored during that cleanup.
This signal handling requires the main Python thread; SIGKILL or machine failure cannot be handled. On Windows it creates a new process group and
uses `taskkill /T /F` against the wrapper PID to terminate its tree. Cleanup precedes releasing the lock;
no proposal is installed and no follow-up starts. These controls do not contain deliberately detached
processes from a malicious client. Client stderr is captured, never streamed to the terminal. Failure
messages report only fixed network/authentication categories or a generic diagnostic; even a raw stderr
tail could expose player data. An unsupported CLI flag fails the handoff; never remove restrictions to make an older client work.
The installed clients' `--help` and official references were checked during implementation; offline tests
verify construction and validation, not live model behavior on every client version/platform.

The environment allowlist retains OS/home/temp/path, locale, certificate/proxy settings, and only the
selected client's authentication variables: `CODEX_HOME`/`OPENAI_API_KEY` for Codex;
`ANTHROPIC_API_KEY`/`CLAUDE_CODE_OAUTH_TOKEN` for Claude. Existing account login remains available through
client-managed storage. Custom provider settings and credential helpers are not inherited. Set
`SCIONBOOK_MODEL` to explicitly select the proposal model; otherwise the client's default applies because
user settings are suppressed. Normal interactive launchers keep their existing model configuration.

This is not a separate OS identity or an egress firewall. The client process, installed extensions,
managed settings, auth storage, model provider, and OS remain trusted. A temporary directory alone does
not stop a compromised executable from reading other paths or using the network. Do not claim these
controls contain a malicious client binary or hostile same-user filesystem races. Stronger isolation
requires a separately configured sandbox/account and network policy, with client authentication handled
inside that boundary.

## Interrupted saves

`.scionbook-recap.lock` prevents overlapping helper runs. An interrupted installation retains an ignored
`.scionbook-recap-*/` directory with `journal.json`, numbered new files, and available numbered old backups.
It contains private player data and must never be committed or shared. Later handoffs stop while a journal
or lock remains. Ordinary installation errors attempt rollback and remove the journal only after all affected destinations
verify against their original contents. Failed or unverifiable rollbacks retain recovery files; process/machine crashes can leave a
partially installed set because multiple replacements are not one filesystem transaction.

Before retrying, confirm no handoff process is running. Inspect the journal's ordered filenames and compare
each live file with its corresponding `old-N` backup and any remaining `new-N` proposal. Restore the intended
local state without overwriting newer manual edits. Only after reviewing the state, remove that ignored
transaction directory and any stale lock. A failed save never launches the follow-up chat automatically.

## Further work

Evaluate a pinned [Cisco Skill Scanner](https://github.com/cisco-ai-defense/skill-scanner) on source-only
synthetic fixtures before adopting it. No scanner has been installed here and no private data is uploaded
for scanning. Markdown escaping in generated reports, stronger per-client isolation validation, and semantic
injection evaluation remain separate work. See [OWASP prompt-injection guidance](https://genai.owasp.org/llmrisk/llm01-prompt-injection/).

Client references: [Codex configuration](https://developers.openai.com/codex/config-reference),
[Claude CLI flags](https://code.claude.com/docs/en/cli-reference).
