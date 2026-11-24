# Figma access (Cursor + Claude Code)

Same pattern as Jira: **template in git, real token only on your laptop**. After one
copy-and-paste, both Cursor and Claude Code start the `figma-qa` MCP server from
`secrets/figma.env`.

You need **Node.js 18+** (`npx`) on the PATH. Pytest itself does not need Node.

## One-time: create the token (QA Figma account)

Use a **shared QA / bot Figma user** that can open the QA files — not a personal
account you will rotate out.

1. Open [Figma → Settings → Security → Personal access tokens](https://help.figma.com/hc/en-us/articles/8085703771159-Manage-personal-access-tokens) (or **Generate new token**).
2. **Token name:** `playwright-e2e-qa` (or any name the team will recognize).
3. **Expiration:** 90 days (do not leave 1 day).
4. Tick **read** scopes only:

   - `current_user:read`
   - `file_content:read`
   - `file_metadata:read`
   - `library_assets:read` / `library_content:read` / `team_library_content:read` if you use libraries

   Leave write / webhooks **unchecked**.
5. Generate, copy `figd_…` **once**. Do not paste it into Slack, git, or chat.

## Every laptop: paste the token (once)

From the repo root:

```bash
cp secrets/figma.example.env secrets/figma.env
```

Open `secrets/figma.env` and replace `your-figma-personal-access-token-here` with the
token. Save.

Confirm git will not commit it:

```bash
git check-ignore -v secrets/figma.env
test -f secrets/figma.env && echo "local figma env: present"
```

`git status` must **not** list `secrets/figma.env`. The `no-real-secrets` pre-commit
hook also blocks it.

## Restart the AI client

- **Cursor:** reload the window (or quit and reopen). MCP config is `.cursor/mcp.json`
  (`figma-qa` → `scripts/figma_mcp.sh`).
- **Claude Code:** restart `claude`, then `/mcp` and confirm `figma-qa` is connected.

First start downloads `figma-developer-mcp` via `npx` (needs network).

## Use it

Copy a **frame** link from Figma (Share → copy link, with `node-id=`) and paste it in
chat: *read this screen* / *write locators from this frame*.

## GitLab CI (optional)

Add a **protected** variable `FIGMA_ACCESS_TOKEN` on the project if a CI job must call
the Figma REST API. Do not put the value in `environment-stage.yaml` or in git.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| MCP exits: missing `secrets/figma.env` | Run the copy step above |
| Placeholder token error | The example string is still in the file — paste `figd_…` |
| `npx: command not found` | Install Node 18+ |
| 403 from Figma | Token account cannot open that file — share the QA file with the bot user |
| Official Figma plugin vs `figma-qa` | Plugin uses OAuth (`mcp.figma.com`). This repo’s shared path is **`figma-qa` + paste token**. They can both be enabled; prefer `figma-qa` for team token access. |
