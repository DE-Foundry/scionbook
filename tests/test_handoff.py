"""Confirmed transitions without launching live agents or reading chat storage."""
import io
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import scionbook_handoff as handoff


@pytest.mark.parametrize("recap", ["", "   ", "x" * (handoff.MAX_RECAP + 1)],
                         ids=["empty", "blank", "too-long"])
def test_invalid_recap_never_starts_an_agent_or_creates_staging(tmp_path, monkeypatch, recap):
    monkeypatch.setattr(handoff.subprocess, "run", lambda *a, **k: pytest.fail("agent started"))
    with pytest.raises(ValueError):
        handoff.apply_recap(recap, tmp_path)
    assert not list(tmp_path.iterdir())


@pytest.fixture(autouse=True)
def configured_repo(request, tmp_path):
    if request.node.name.startswith(("test_apply_pipes", "test_non_success", "test_missing_or", "test_nonzero", "test_claude_apply")):
        config = {"version": 1, "character_id": "123456", "name": "Example Hero",
                  "world": "Example", "data_center": "Example", "timezone": "UTC", "mode": "public"}
        (tmp_path / "scionbook.json").write_text(json.dumps(config))
        skill = tmp_path / ".agents/skills/apply-recap/SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text("Synthetic skill: dated outcomes stay separate from routine boxes.\n")
        preferences = tmp_path / "docs" / "gameplay-preferences.md"
        preferences.parent.mkdir()
        preferences.write_text("Synthetic preference precedence rules.")


def proposal():
    return {"status": "proposed", "changes": [
        {"path": "SCIONBOOK_MEMORY.md", "content": "# Memory (v5)\nSession 2026-10-18: Report saved.\n"}]}


def fake_apply(monkeypatch, receipt=None, code=0, raw=None):
    calls = []
    def run(command, **kwargs):
        calls.append((command, kwargs))
        result = Path(command[command.index("--output-last-message") + 1])
        if raw is not None:
            result.write_text(raw)
        elif receipt is not None:
            result.write_text(json.dumps(receipt))
        return SimpleNamespace(returncode=code)
    monkeypatch.setattr(handoff, "run_proposal", run)
    return calls


def test_apply_pipes_only_approved_recap_and_checks_receipt(tmp_path, monkeypatch):
    recap = "What's worth saving: Item $(touch do-not-run); `echo no`; new line\nMore reports"
    receipt = proposal()
    calls = fake_apply(monkeypatch, receipt)
    monkeypatch.setenv("LODESTONE_COOKIE", "test-only-value")
    assert handoff.apply_recap(recap, tmp_path)["status"] == "applied"
    command, kwargs = calls[0]
    assert "exec" in command and "--ephemeral" in command and command[-1] == "-"
    assert not any(word in command for word in ("resume", "fork", "--last"))
    assert recap not in " ".join(command)
    assert json.dumps(recap, ensure_ascii=False) in kwargs["input"]
    assert "LODESTONE_COOKIE" not in kwargs["env"]
    assert command[command.index("--sandbox") + 1] == "read-only"
    assert command[command.index("--ask-for-approval") + 1] == "never"
    assert "memories.use_memories=false" in command
    assert "memories.generate_memories=false" in command
    assert "agents.enabled=false" in command
    assert not list(tmp_path.glob(".scionbook-*"))


@pytest.mark.parametrize("receipt", [
    {"status": "needs_input", "summary": "Confirm the session date."},
    {"status": "failed", "summary": "Write failed."},
    {"status": "pending", "summary": "Not applied."},
    {"status": "applied", "summary": None}, [],
])
def test_non_success_or_invalid_receipt_stops_handoff(tmp_path, monkeypatch, receipt):
    fake_apply(monkeypatch, receipt)
    with pytest.raises(RuntimeError, match="stopped"):
        handoff.apply_recap("Approved recap", tmp_path)
    assert not list(tmp_path.glob(".scionbook-*"))


@pytest.mark.parametrize("raw", [None, "not JSON"])
def test_missing_or_malformed_result_is_not_success(tmp_path, monkeypatch, raw):
    fake_apply(monkeypatch, raw=raw)
    with pytest.raises(RuntimeError, match="could not be verified"):
        handoff.apply_recap("Approved recap", tmp_path)


def test_nonzero_exit_is_failure_even_with_success_receipt(tmp_path, monkeypatch):
    fake_apply(monkeypatch, {"status": "applied", "summary": "Claims success"}, code=1)
    with pytest.raises(RuntimeError, match="failed"):
        handoff.apply_recap("Approved recap", tmp_path)


def test_no_confirmation_never_checks_terminal_or_launches(monkeypatch):
    monkeypatch.setattr(handoff, "open_terminal", lambda: pytest.fail("opened terminal"))
    with pytest.raises(SystemExit) as error:
        handoff.main(["recap"])
    assert error.value.code == 2


def test_no_terminal_stops_before_applying(monkeypatch):
    monkeypatch.setattr(handoff.shutil, "which", lambda _: "/fake/tool")
    def no_terminal():
        raise OSError("No terminal")
    monkeypatch.setattr(handoff, "open_terminal", no_terminal)
    monkeypatch.setattr(handoff, "apply_recap", lambda *a: pytest.fail("applied"))
    with pytest.raises(SystemExit) as error:
        handoff.main(["recap", "--confirmed"])
    assert error.value.code == 1


def mock_terminal(monkeypatch):
    monkeypatch.setattr(handoff.shutil, "which", lambda _: "/fake/tool")
    monkeypatch.setattr(handoff, "open_terminal", lambda: io.StringIO())


@pytest.mark.parametrize("status", ["applied", "unchanged"])
def test_success_applies_then_starts_maintainer_without_payload(monkeypatch, status):
    mock_terminal(monkeypatch)
    events = []
    monkeypatch.setattr(sys, "stdin", io.StringIO("Only approved recap"))
    def apply(text, **_):
        events.append(("apply", text))
        return {"status": status, "summary": "Done"}
    def start(role, terminal, **_):
        events.append(("start", role))
        return 0
    monkeypatch.setattr(handoff, "apply_recap", apply)
    monkeypatch.setattr(handoff, "start_chat", start)
    handoff.main(["recap", "--confirmed"])
    assert events == [("apply", "Only approved recap"), ("start", "maintainer")]


def test_apply_failure_does_not_launch_or_retry(monkeypatch):
    mock_terminal(monkeypatch)
    monkeypatch.setattr(sys, "stdin", io.StringIO("Approved recap"))
    calls = []
    def fail(text, **_):
        calls.append(text)
        raise RuntimeError("Needs clarification")
    monkeypatch.setattr(handoff, "apply_recap", fail)
    monkeypatch.setattr(handoff, "start_chat", lambda *a: pytest.fail("started chat"))
    with pytest.raises(SystemExit) as error:
        handoff.main(["recap", "--confirmed"])
    assert error.value.code == 1
    assert calls == ["Approved recap"]


def test_session_transition_only_starts_session(monkeypatch):
    mock_terminal(monkeypatch)
    monkeypatch.setattr(handoff, "apply_recap", lambda *a: pytest.fail("applied recap"))
    calls = []
    monkeypatch.setattr(handoff, "start_chat", lambda role, terminal, **_: calls.append(role) or 0)
    handoff.main(["session", "--confirmed"])
    assert calls == ["session"]


def test_launch_failure_is_reported(monkeypatch):
    mock_terminal(monkeypatch)
    monkeypatch.setattr(handoff, "start_chat", lambda *a, **k: 3)
    with pytest.raises(SystemExit) as error:
        handoff.main(["session", "--confirmed"])
    assert error.value.code == 3


@pytest.mark.parametrize("role,sandbox,approval,skill", [
    ("session", "workspace-write", "on-request", "$start-session"),
    ("maintainer", "workspace-write", "on-request", "$start-maintenance"),
])
@pytest.mark.skipif(os.name == "nt", reason="Bash adapters are supported on Linux/macOS")
def test_actual_launcher_uses_new_context_and_role_permissions(tmp_path, role, sandbox, approval, skill):
    # Execute the real Bash launcher with a fake codex executable; no live agent.
    executable = tmp_path / "codex"
    executable.write_text("#!/bin/sh\nprintf '%s\\n' \"$@\"\n")
    executable.chmod(0o755)
    environment = {**os.environ, "PATH": str(tmp_path) + os.pathsep + os.environ["PATH"]}
    result = subprocess.run(["bash", str(handoff.REPO / "scripts" / "scionbook-chat"), role],
                            env=environment, text=True, capture_output=True, check=True)
    args = result.stdout.splitlines()
    assert args[args.index("--sandbox") + 1] == sandbox
    assert args[args.index("--ask-for-approval") + 1] == approval
    assert skill in args[-1]
    assert not any(value in args for value in ("resume", "fork", "--last"))
    assert "memories.use_memories=false" in args
    assert "agents.enabled=false" in args


def fake_claude(tmp_path):
    executable = tmp_path / "claude"
    executable.write_text("#!/bin/sh\nprintf '%s\\n' \"$PWD\" \"$CLAUDE_CODE_DISABLE_AUTO_MEMORY\" \"$@\"\n")
    executable.chmod(0o755)
    return {**os.environ, "PATH": str(tmp_path) + os.pathsep + os.environ["PATH"],
            "SCIONBOOK_CLIENT": "claude"}


@pytest.mark.skipif(os.name == "nt", reason="Bash adapters are supported on Linux/macOS")
def test_claude_session_launcher_keeps_normal_write_controls(tmp_path):
    result = subprocess.run(["bash", str(handoff.REPO / "scripts" / "scionbook-chat"), "session"],
                            env=fake_claude(tmp_path), text=True, capture_output=True, check=True)
    cwd, memory, *args = result.stdout.splitlines()
    assert cwd == str(handoff.REPO) and memory == "1"
    assert "--permission-mode" not in args
    assert "--dangerously-skip-permissions" not in args
    denied = args[args.index("--disallowedTools") + 1:args.index("--")]
    assert denied == ["Agent"]
    assert "--allowedTools" not in args
    assert "start-session" in args[-1] and "Session Planner" in args[-1]
    assert not any(value in args for value in ("--resume", "--continue", "-c", "-r"))


@pytest.mark.skipif(os.name == "nt", reason="Bash adapters are supported on Linux/macOS")
def test_claude_maintainer_launcher_keeps_write_prompts(tmp_path):
    result = subprocess.run(["bash", str(handoff.REPO / "scripts" / "scionbook-chat"), "maintainer"],
                            env=fake_claude(tmp_path), text=True, capture_output=True, check=True)
    _, memory, *args = result.stdout.splitlines()
    assert memory == "1"
    assert "--permission-mode" not in args
    assert "--dangerously-skip-permissions" not in args
    assert args[args.index("--disallowedTools") + 1] == "Agent"
    assert "start-maintenance" in args[-1]


@pytest.mark.skipif(os.name == "nt", reason="Bash adapters are supported on Linux/macOS")
def test_unknown_client_is_rejected(tmp_path):
    environment = {**os.environ, "SCIONBOOK_CLIENT": "other"}
    result = subprocess.run(["bash", str(handoff.REPO / "scripts" / "scionbook-chat"), "session"],
                            env=environment, text=True, capture_output=True)
    assert result.returncode == 2 and "Unsupported" in result.stderr
    with pytest.raises(ValueError, match="Unsupported"):
        handoff.apply_recap("Approved recap", tmp_path, client="other")


def test_claude_apply_is_ephemeral_file_only_and_checks_structured_receipt(tmp_path, monkeypatch):
    recap = "What's worth saving: $(touch nope)"
    receipt = proposal()
    calls = []
    def run(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(returncode=0, stdout=json.dumps({"structured_output": receipt}))
    monkeypatch.setattr(handoff, "run_proposal", run)
    monkeypatch.setenv("LODESTONE_COOKIE", "test-only-value")
    monkeypatch.setenv("SCIONBOOK_CLIENT", "claude")
    assert handoff.apply_recap(recap, tmp_path)["status"] == "applied"
    command, kwargs = calls[0]
    assert command[0] == "claude" and "-p" in command and "--no-session-persistence" in command
    assert command[command.index("--permission-mode") + 1] == "dontAsk"
    assert command[command.index("--tools") + 1] == ""
    assert "--strict-mcp-config" in command
    assert json.loads(command[command.index("--json-schema") + 1]) == handoff.RESULT_SCHEMA
    assert recap not in " ".join(command)
    assert json.dumps(recap, ensure_ascii=False) in kwargs["input"]
    assert kwargs["cwd"] != str(tmp_path)
    assert "--setting-sources" in command
    assert "LODESTONE_COOKIE" not in kwargs["env"]
    assert kwargs["env"]["CLAUDE_CODE_DISABLE_AUTO_MEMORY"] == "1"


@pytest.mark.parametrize("stdout", ["not JSON", "{}", json.dumps({"structured_output": None})])
def test_claude_apply_without_valid_receipt_is_not_success(tmp_path, monkeypatch, stdout):
    monkeypatch.setattr(handoff, "run_proposal",
                        lambda *a, **k: SimpleNamespace(returncode=0, stdout=stdout))
    with pytest.raises(RuntimeError):
        handoff.apply_recap("Approved recap", tmp_path, client="claude")


def test_start_chat_passes_client_to_launcher(monkeypatch):
    seen = {}
    monkeypatch.setattr(handoff.subprocess, "run",
                        lambda command, **k: seen.update(k) or SimpleNamespace(returncode=0))
    handoff.start_chat("session", None, client="claude")
    assert seen["env"]["SCIONBOOK_CLIENT"] == "claude"


@pytest.mark.parametrize('role,skill', [('session', 'start-session'), ('maintainer', 'start-maintenance'), ('apply', 'apply-recap')])
@pytest.mark.parametrize('dirname', [
    'A repo & # ü',
    pytest.param('A repo & #? ü', marks=pytest.mark.skipif(sys.platform == 'win32', reason='Windows forbids ? in filenames')),
])
def test_app_draft_encodes_exact_workspace_and_skill_without_launch(tmp_path, monkeypatch, role, skill, dirname):
    from urllib.parse import urlsplit, parse_qs
    repo = tmp_path / dirname
    repo.mkdir()
    monkeypatch.setattr(handoff.subprocess, 'run', lambda *a, **k: pytest.fail('launched agent'))
    url = urlsplit(handoff.app_draft_link(role, repo))
    assert url.scheme == 'codex' and url.netloc == 'threads' and url.path == '/new'
    params = parse_qs(url.query)
    assert set(params) == {'path', 'prompt'}
    assert params['path'] == [str(repo.resolve())]
    prompt = params['prompt'][0]
    if role == 'apply':
        assert prompt.startswith('Use $apply-recap from .agents/skills/apply-recap/SKILL.md.')
        assert 'verify the local save' in prompt and '$start-maintenance' not in prompt
        assert 'missing' in prompt and 'fails' in prompt
        assert prompt.endswith('Recap to apply:\n')
    else:
        assert prompt == f'Use ${skill} from .agents/skills/{skill}/SKILL.md.'
    assert not url.fragment


@pytest.mark.parametrize('role', ['session', 'apply', 'maintainer'])
def test_draft_needs_no_confirmation_terminal_or_cli(monkeypatch, capsys, role):
    monkeypatch.setattr(handoff, 'open_terminal', lambda: pytest.fail('terminal opened'))
    monkeypatch.setattr(handoff.shutil, 'which', lambda *a: pytest.fail('CLI probed'))
    monkeypatch.setattr(handoff, 'apply_recap', lambda *a: pytest.fail('saved recap'))
    handoff.main(['draft', '--role', role])
    assert capsys.readouterr().out.startswith('codex://threads/new?')


def test_draft_rejects_non_directory_workspace(tmp_path):
    file = tmp_path / 'file'
    file.write_text('not a workspace')
    with pytest.raises(ValueError, match='directory'):
        handoff.app_draft_link('session', file)


def test_apply_and_followup_drafts_do_not_read_or_transfer_recap(monkeypatch, capsys):
    from urllib.parse import urlsplit, parse_qs
    class NoRead:
        def read(self, *args):
            pytest.fail('Draft generation read a recap')
    monkeypatch.setattr(sys, 'stdin', NoRead())
    monkeypatch.setattr(handoff, 'apply_recap', lambda *a: pytest.fail('Recap was applied'))
    handoff.main(['draft', '--role', 'apply'])
    apply = parse_qs(urlsplit(capsys.readouterr().out.strip()).query)['prompt'][0]
    assert apply.endswith('Recap to apply:\n')
    handoff.main(['draft', '--role', 'maintainer'])
    followup = parse_qs(urlsplit(capsys.readouterr().out.strip()).query)['prompt'][0]
    assert followup == 'Use $start-maintenance from .agents/skills/start-maintenance/SKILL.md.'


@pytest.mark.parametrize("role,skill", [
    ("session", "start-session"), ("maintainer", "start-maintenance"), ("apply", "apply-recap"),
])
def test_portable_prompt_needs_no_client_files_or_recap(monkeypatch, capsys, role, skill):
    def forbidden(*args, **kwargs):
        pytest.fail("Portable prompt attempted a side effect or private input access")
    monkeypatch.setattr(handoff.subprocess, "run", forbidden)
    monkeypatch.setattr(handoff.shutil, "which", forbidden)
    monkeypatch.setattr(handoff, "open_terminal", forbidden)
    monkeypatch.setattr(handoff, "apply_recap", forbidden)
    monkeypatch.setattr(Path, "read_text", forbidden)
    monkeypatch.setattr(Path, "write_text", forbidden)
    monkeypatch.setattr(sys, "stdin", SimpleNamespace(read=forbidden))
    handoff.main(["prompt", "--role", role])
    output = capsys.readouterr().out
    assert f".agents/skills/{skill}/SKILL.md" in output
    assert "codex" not in output.lower()
    if role == "apply":
        assert output.rstrip().endswith("Recap to apply:")


def test_portable_prompt_rejects_unknown_role():
    with pytest.raises(ValueError, match="Unknown prompt role"):
        handoff.portable_prompt("unknown")
