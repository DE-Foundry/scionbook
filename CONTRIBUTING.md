# Contributing to Scionbook

Start with README.md and standards.md. Scionbook keeps Python data tools independent of AI providers;
shared Markdown workflows must work through explicit file-based prompts. Put client-specific setup and
launch behavior in optional integrations, with a manual path that remains usable without that client.

## Development

Use Python 3.10 or newer in a virtual environment, then run:

```bash
python3 -m pip install -r requirements-dev.txt
python3 -m pytest tests/ -q
```

The suite uses synthetic fixtures and requires no character account, cookie, or live service. Add tests
for changed parser, authentication, persistence, or launcher behavior. For workflow changes, check the
manual path, unavailable capabilities, role boundaries, and linked references. Describe checks actually
performed and remaining limits in the pull request. Do not claim fixture tests prove live compatibility.

Keep changes focused. Discuss larger features in an issue before implementation. For bugs, include the
command/workflow, Python version, operating system, expected behavior, and a sanitized error. Never attach
player snapshots, real account HTML, cookies, or private inventories. Reproduce parser problems using
minimal synthetic fixtures under tests/fixtures/.

Preserve unknown versus zero, complete-history validation, staged refresh installation, and newer dated
player reports. New unlock annotations need exact English quest names and source links; see
[unlock coverage](docs/unlock-coverage.md). Keep personal preferences and reports in ignored local files.

Contributions are provided under the repository's MIT license. Only contribute code, fixtures, and assets
you have the right to share. Public-release checks are documented in [release preparation](docs/releasing.md).
