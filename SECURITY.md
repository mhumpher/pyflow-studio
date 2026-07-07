# Security policy

Pyflow is a **local-first, single-user** tool by default. The server binds to `127.0.0.1` and there is
no authentication layer yet — do not expose it to a network you don't fully trust.

## Important security properties to understand

- **The Python tool runs arbitrary code.** The `dev.python` tool executes the code stored in the
  workflow, in-process, with full Python privileges. This is intended for running *your own* code on
  *your own* machine. **A `.pyflow` file can therefore contain executable code — treat shared workflow
  files exactly as you would any script, and do not run untrusted ones.** Subprocess/sandbox isolation
  is a prerequisite for running user-code tools in any shared/hosted context (see
  [docs/09-non-functional.md](docs/09-non-functional.md)).

- **Database credentials.** The Database Input/Output tools currently store their connection settings in
  the workflow file. Use `${ENV_VAR}` references (supported in any connection field, including the
  password) so secrets live in environment variables, not in the `.pyflow` file. A managed secret store
  and connection manager are on the roadmap.

- **File access.** Input/Output tools read and write local paths. Only open workflows whose paths you
  trust.

## Reporting a vulnerability

Please **do not** open a public issue for security problems. Instead, use GitHub's private vulnerability
reporting (the repository's **Security → Report a vulnerability** tab) so the issue can be triaged before
disclosure. Include a description, reproduction steps, and the affected version/commit.

We aim to acknowledge reports promptly and will coordinate a fix and disclosure timeline with you.
