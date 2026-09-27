# Reporting security issues

Do not post credentials, authenticated HTML, player files, or a working exploit containing private data
in public issues. Use the repository host's private vulnerability-reporting feature if the maintainers
have enabled it. If no private channel is listed, ask the maintainer to provide one without disclosing
the sensitive details publicly. Never send a Lodestone session cookie as a reproduction aid.

Reports should identify the affected revision, component, impact, and a minimal synthetic reproduction.
This project does not promise a fixed response time or support window.

Lodestone credentials belong in local process environment variables or hidden terminal input, never
chat messages, tracked files, command arguments, or logs. Follow README.md for authentication and local
storage. Ignore rules prevent future accidental additions; they do not remove data from Git history.
