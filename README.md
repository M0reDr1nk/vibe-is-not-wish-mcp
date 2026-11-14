# VINW — Vibe Is Not Wish MCP

> **Vibe ≠ Wish.** A Markdown-first, spiral-ascend workflow engine for strict software engineering process control.

VINW is an MCP server that gives an agent a process it cannot skip: seven layers, explicit baselines, recorded ascents, blocking review gates, and an audit trail a human can read at any time. It also ships a read-only TUI so you can watch the work without reading the chat log.

## Contents

- [Design Purpose & Philosophy](#design-purpose--philosophy)
- [Self-hosting Record](#self-hosting-record)
- [How It Works](#how-it-works)
- [Install & Configure](#install--configure)
- [Watching Progress](#watching-progress)
- [MCP Tools](#mcp-tools)
- [Citation & Reference Format](#citation--reference-format)
- [License](#license)

## Design Purpose & Philosophy

### The problem

Vibe coding is fast because the conversation is the only state. The conversation also forgets: why a decision was made, which version was approved, what was tried and reverted, and which assumption turned out to be wrong. When a test fails three hours later, the cheapest action is to patch the symptom in the file the agent happens to be looking at — not to ask which layer owns the root cause.

VINW starts from one premise:

> **When a wrong turn is expensive, the process must be an artifact, not a vibe.**

So the process is a directory tree, state transitions are tool calls, the changelog is append-only, and the human is a gate rather than a spectator.

### What VINW is

- **A process control plane.** Seven layers from requirements to final acceptance, with explicit baselines, recorded ascents, and descent rounds.
- **A Markdown data plane.** Requirements, evidence, design, implementation notes, test results, and the final report are plain files you can read, diff, and commit.
- **A tool surface over the same state.** 38 MCP tools, a CLI, and a read-only TUI, all looking at the same `.vinw/manifest.md`.
- **A methodology, not just a server.** An optional skill tells the agent which tool to call at each boundary.
- **A gate against self-certification.** Independent audit reports, classification of every finding, and blocking checks at the points where a project would otherwise advance.

### Principles

1. **The process is the artifact.**
   Every layer produces a document. A baseline freezes the layer's README (its stage contract and summary) into `.baseline/vNNN.md`; the manifest is the single state machine and the README is its human-facing mirror. A rollback restores the baseline body but keeps the live todo list, so reverting a design never rewinds work progress.

2. **Spiral, not linear.**
   Software engineering needs backtracking. When a test reveals a design flaw, VINW ascends to the layer that owns the root cause, restores its baseline, marks every layer below as `superseded` — not deleted — and starts a new descent round. The history of *why* the project went back is first-class data.

3. **Record before you roll back.**
   Every ascent records `from_layer`, `to_layer`, `to_baseline`, `reason`, and the before/after descent numbers. Every change records intent before the modification. Nothing important is silently overwritten; even `force=true` leaves a `[force]` trace in the baseline reason.

4. **Gates over goodwill.**
   "Please remember to check" is not a control. `se_can_descend` refuses while a blocking confirmation is open; design-review gates default to blocking; L4 cannot be baselined or descended from without a passing consistency state; unresolved audit escalations block the gate. The TUI and `se_get_next_steps` surface the block instead of letting it disappear into a chat message. (The supported path is to check `se_can_descend` before descending; like any advisory API, it cannot stop a caller that ignores it.)

5. **Evidence before design.**
   L2 is not a literature-review decoration. It forces references, an evidence matrix, and a synthesis whose conclusions become constraints on L3. "I like this stack" is not an argument; "this stack wins on these weighted criteria, and here is the measurement" is.

6. **An audit proves the absence of drift, not the presence of correctness.**
   The text check is a necessary condition: it verifies that required design symbols exist in code. The LLM audit looks for semantic gaps and demands `file:line` evidence. Tests are the constructive proof within their coverage. VINW keeps all three and never treats a green text check as proof that the code is right.

7. **Automate the mechanical; escalate the judgment.**
   Triage classifies each finding as `impl_bug`, `design_bug`, `design_gap`, or `ambiguous`, with a confidence. Only `impl_bug + high confidence` may be fixed automatically. Design problems and ambiguity go to a human with four fields: difference, analysis, recommendation, and impact.

8. **Different planes need different storage.**
   Project documents are Markdown: human-readable, git-friendly, reviewable. The global project registry is SQLite at `$VINW_HOME/registry.db`: machine state, concurrent writers, WAL, transactions. Forcing one medium to serve both jobs would weaken both.

9. **Self-hosting is the acceptance test.**
   VINW is built with VINW. [`vinw-design/`](vinw-design/) is its own process record: 16 descents, 15 ascents, and 88 audit findings, each triaged through the same reports and gates the tool enforces on its users.

### Non-goals

- **Not a code generator.** VINW constrains a capable agent; it does not replace one.
- **Not a correctness guarantee.** It makes process failures visible and recoverable, not impossible.
- **Not a linter, formatter, or test runner.** It gates on their results rather than reimplementing them.
- **Not a cloud service.** No account, no telemetry, no network dependency; the data is local files.
- **Not a straightjacket.** `force` exists for real emergencies, but it is recorded as an exception, not hidden.

## Self-hosting Record

**Statistics snapshot: commit `2a90ed5`** (2026-11-14 15:20 +08:00). At this commit the test suite reports `303 passed` across 16 files, and the MCP surface exposes `38` tools.

VINW's own implementation is its longest-running test case. As of this commit, **88 design/code deviations had been intercepted and recorded**:

| Type | Count | Description | Representative example |
|------|------:|-------------|------------------------|
| `impl_bug` | 42 | Code contradicts or omits something the approved design already specifies. | `ensure()` re-anchored the audited fingerprint even when the text re-check failed, so a rejected transition could be retried successfully. |
| `design_gap` | 18 | Code implements real behavior that the design never specified; the design has to catch up. | Drift detection and `heal_drift` were implemented and sitting in the gate path before L3 had any contract for them. |
| `design_bug` | 19 | The design itself is wrong, internally inconsistent, or contradicts behavior the implementation needs. | The design described two mutually exclusive triage routes: append a triage section to PROMPT v3, or expose a separate `se_triage_prompt` tool. |
| `ambiguous` | 2 | The design is silent and either reading is defensible; a human must choose the intended behavior. | The execution position of `heal_drift` (before or after the guards) was undefined; both readings were defensible. |
| unclassified | 7 | Reported before the audit contract required a classification field. | Early reviews that predate the triage workflow. |
| **Total** | **88** | — | — |

**Counting basis.** All 88 findings are machine-counted from the eight distinct LLM audit reports stored in `L4-编码实现/consistency-reports/` (identical re-stores of the same content are de-duplicated by content hash). Classification comes from the stored triage verdicts where present, otherwise from the report's own field. Seven early findings predate the classification contract and are counted as `unclassified` rather than guessed. Rounds are counted separately, so a conceptual issue re-found by a later reviewer can appear twice; this is an audit-record count, not a deduplicated defect count. Process-only violations and development-time self-checks are excluded.

The full evidence lives in [`vinw-design/L4-编码实现/consistency-reports/`](vinw-design/L4-编码实现/consistency-reports/) and the append-only [changelog](vinw-design/.vinw/changelog.md).

**Two defects that the audit loop itself had to catch, not the gates:** a stale MCP server process (killed and restarted; see the R30 record) and a test-only edit at L6 that the design-lag gate refused. Both are kept in the record rather than smoothed over.

## How It Works

### The seven layers

| Layer | Question it answers | Primary artifacts |
|-------|---------------------|-------------------|
| **L1 需求拆解** | What exactly are we building, and how will we know it is done? | `proposals.md`, todo list |
| **L2 参考文献与方案搜证汇总** | What already exists, and why is our choice better for this case? | `references.md`, `evidence-matrix.md`, `synthesis.md` |
| **L3 方案细化** | What is the architecture and the exact interface? | `design-doc.md`, `api-design.md` |
| **L4 编码实现** | Does the code match the approved design? | implementation notes, consistency reports |
| **L5 测试验证** | Does it work, and do failures point back to design? | `test-plan.md`, `test-results.md`, debug sessions |
| **L6 检视清理** | Is the debug scaffolding gone and the docs synced? | cleanup log |
| **L7 终验** | Is this deliverable, and what are the known limits? | `final-report.md` |

### The spiral

```
descent-1: L1 → L2 → L3 → L4 → L5
                          ↓ tests reveal a design flaw
    se_ascend(L5, L3, "v001", "API contract mismatch")
                          ↓
descent-2:           L3 (rollback to v001) → L4 → L5
                                  ↓ another issue found
    se_ascend(L5, L2, "v001", "Evidence matrix incomplete")
                          ↓
descent-3:      L2 → L3 → L4 → L5 → L6 → L7
```

An ascent is not a reset. It records the reason, restores the target layer's baseline, marks the layers below as `superseded`, and increments the descent counter. The project can therefore show both what was decided and why it was reopened.

### Project layout

```
my-app/
├── .vinw/
│   ├── manifest.md          # Single state machine
│   ├── changelog.md         # Append-only change log
│   ├── ascensions.md        # Ascent history
│   └── decisions.md         # Cross-layer decisions
├── L1-需求拆解/
│   ├── README.md
│   └── proposals.md
├── L2-参考文献与方案搜证汇总/
│   ├── README.md
│   ├── references.md
│   ├── evidence-matrix.md
│   └── synthesis.md
├── L3-方案细化/
│   ├── README.md
│   ├── design-doc.md
│   └── api-design.md
├── L4-编码实现/
│   ├── README.md
│   ├── implementation.md
│   ├── consistency-reports/
│   └── .baseline/
│       └── v001.md
├── L5-测试验证/
│   ├── README.md
│   ├── test-plan.md
│   ├── test-results.md
│   └── debug-sessions/
├── L6-检视清理/
└── L7-终验/
```

## Install & Configure

### Requirements

- Python **3.10+**
- A harness that can launch an MCP server over stdio or Streamable HTTP
- Linux, macOS, or Windows

### Fast path: let your agent install it

Copy the block below into your coding agent (Claude Code, Cursor, Windsurf, DSH, or any agent that can edit its own MCP configuration). Replace the four input values and the `<one sentence>` description, then send it. The prompt is written so the agent verifies each step and stops on failure instead of claiming success.

```text
Install and configure VINW MCP for this workspace. Work autonomously, verify
every step, and stop with a short report if anything fails.

Inputs — replace these first:
  VINW_REPO = <absolute path to the vibe-is-not-wish-mcp checkout>
  WORK_ROOT = <absolute directory that will hold the project>
  PROJECT   = <project name, use lowercase-kebab-case>
  HARNESS   = <claude-code | claude-desktop | cursor | windsurf | vscode | dsh | other>

Steps:
1. Check prerequisites.
     python3 --version          # must be >= 3.10
     test -d "$VINW_REPO"
   If the checkout is missing, clone the repository there first. Do not guess
   a different path.

2. Install VINW in editable mode, so later git pulls take effect without a
   reinstall.
     cd "$VINW_REPO"
     python3 -m venv .venv
     .venv/bin/python -m pip install -U pip
     .venv/bin/python -m pip install -e .
     .venv/bin/python -c "import vinw; print(vinw.__file__)"
   PASS only if the printed path is inside $VINW_REPO/vinw. If it points at
   site-packages/vinw, the install is a stale copy: rerun the editable install
   and verify again.

3. Create the project. Skip this step if
   "$WORK_ROOT/$PROJECT/.vinw/manifest.md" already exists.
     .venv/bin/vinw init "$WORK_ROOT/$PROJECT" --name "$PROJECT" --desc "<one sentence>"

3.5 **Restart the MCP server after every install.** The DSH-spawned
   `vinw server` is a long-running process: `pip install` only changes
   files on disk, never the modules already loaded in memory. After any
   code change, kill the server process (DSH respawns it on the next tool
   call) or reinstall the plugin bundle. A stale server silently runs old
   gates — see the R30 incident record in vinw-design.

4. Verify registration. `vinw init` registers the project automatically in
   current revisions (pass `--no-register` to opt out). Check:
     .venv/bin/vinw project list
   If the project is missing (older version, `--no-register`, or a registry
   failure), register it manually:
     .venv/bin/vinw project add "$WORK_ROOT/$PROJECT" --name "$PROJECT"

5. Connect the MCP server. Prefer stdio unless the harness cannot launch a
   subprocess.
   stdio endpoint:
     command = $VINW_REPO/.venv/bin/vinw
     args    = ["server"]
     cwd     = $WORK_ROOT/$PROJECT
   Harness-specific wiring:
     - claude-code: from "$WORK_ROOT/$PROJECT", run
         claude mcp add vinw -- "$VINW_REPO/.venv/bin/vinw" server
     - claude-desktop: merge the JSON below into
         "~/Library/Application Support/Claude/claude_desktop_config.json"
         (Windows: %APPDATA%\Claude\claude_desktop_config.json)
     - cursor: merge the JSON below into ~/.cursor/mcp.json
     - windsurf: merge the JSON below into ~/.codeium/windsurf/mcp_config.json
     - vscode: put the same object under the "servers" key in .vscode/mcp.json
     - dsh: create a configuration-only bundle with package.json (dsh.bundle.patch)
         and cordis.patch.yml inserting @deepseek-ai/dsh-mcp-client with
         serverName=vinw, transport=stdio, command, args, cwd; install it with
         plugin_manager. A working example is in .dsh-bundles/vinw-mcp/.
   JSON shape for clients that use mcpServers:
     {
       "mcpServers": {
         "vinw": {
           "command": "$VINW_REPO/.venv/bin/vinw",
           "args": ["server"],
           "cwd": "$WORK_ROOT/$PROJECT"
         }
       }
     }
   If the client ignores "cwd", start it from the project directory, or call
   se_use_project("$PROJECT") once, or pass the "project" argument to tools.

   HTTP alternative, for clients that only accept a URL:
     start "$VINW_REPO/.venv/bin/vinw server --http --port 3000" as a managed
     background process, keep it running, and use
     http://127.0.0.1:3000/mcp. Do not start a second copy on the same port.

6. Verify end to end.
     .venv/bin/vinw status "$WORK_ROOT/$PROJECT"
   Restart or reload the harness if it caches MCP connections, then call:
     se_get_project       -> must return name, current_layer, current_descent
     se_get_next_steps    -> must list the L1 work
   If the tools are missing, inspect the harness MCP log. Do not claim success
   without the two tool results.

7. Report back:
   - repository, venv, and project paths
   - transport used, and the exact config file or command changed
   - output of `vinw project list` and `se_get_project`
   - watch command: $VINW_REPO/.venv/bin/vinw tui "$WORK_ROOT/$PROJECT"
   - the next action the user must take (normally: approve the L1 gate)
```

### Manual install

```bash
cd vibe-is-not-wish-mcp

# 1. Editable install in a local venv
python3 -m venv .venv
.venv/bin/python -m pip install -U pip
.venv/bin/python -m pip install -e .        # add ".[dev]" for pytest/ruff

# 2. Create a project — current revisions register it automatically
.venv/bin/vinw init ./projects/my-app --name my-app --desc "My application"
.venv/bin/vinw project list   # verify the project is visible

# 3. Watch it (read-only)
.venv/bin/vinw tui my-app

# 4. Serve it
.venv/bin/vinw server                     # stdio
.venv/bin/vinw server --http --port 3000  # http://127.0.0.1:3000/mcp
```

Why `-e` matters: it makes the `vinw` console script and the `vinw` Python package come from this checkout. A non-editable copy in `site-packages` will keep running old code after you pull, which produces the classic "the fix is in the source but the TUI still shows the bug" illusion.

`vinw init` registers the project automatically in current revisions. On an older revision, or when you pass `--no-register`, register it explicitly:

```bash
.venv/bin/vinw project add ./projects/my-app --name my-app
```

### Register with your harness

**stdio** is the simplest and works everywhere that can launch a subprocess:

```json
{
  "mcpServers": {
    "vinw": {
      "command": "/absolute/path/to/vibe-is-not-wish-mcp/.venv/bin/vinw",
      "args": ["server"],
      "cwd": "/absolute/path/to/project/my-app"
    }
  }
}
```

| Harness | Where the config goes | Notes |
|---------|----------------------|-------|
| **Claude Code** | `claude mcp add vinw -- /abs/.venv/bin/vinw server` | Run from the project directory |
| **Claude Desktop** | Settings → Connectors → Add custom connector, or `claude_desktop_config.json` | JSON shape above |
| **Cursor** | `~/.cursor/mcp.json` | JSON shape above |
| **Windsurf** | `~/.codeium/windsurf/mcp_config.json` | JSON shape above |
| **VS Code Copilot** | `.vscode/mcp.json` | Put the object under `"servers"` |
| **DeepSeek Harness** | configuration-only bundle installed through `plugin_manager` | See below |
| **Kimi** | No native MCP client | Use the Kimi plugin, or a local bridge |

**Streamable HTTP** is convenient when several clients should share one server:

```bash
.venv/bin/vinw server --http --port 3000
# Connect at http://127.0.0.1:3000/mcp
```

For a **DeepSeek Harness** bundle, the repository contains a working example in [`.dsh-bundles/vinw-mcp/`](.dsh-bundles/vinw-mcp/). Update the absolute paths and install it as a local bundle:

```json
{
  "name": "@local/vinw-mcp",
  "version": "1.0.0",
  "private": true,
  "type": "module",
  "files": ["cordis.patch.yml"],
  "dsh": { "bundle": { "patch": "./cordis.patch.yml" } }
}
```

```yaml
- insert:
    - id: vinw-mcp
      name: '@deepseek-ai/dsh-mcp-client'
      config:
        serverName: vinw
        transport: stdio
        command: /absolute/path/to/.venv/bin/vinw
        args: ["server"]
        cwd: /absolute/path/to/project/my-app
        failOnStartupError: false
```

**Kimi** has no native MCP client today. The two practical options are the VINW Kimi plugin in [`vinw-plugin/`](vinw-plugin/) (methodology only) or a small local bridge that exposes the HTTP endpoint in a format Kimi can consume.

### Verify

```bash
.venv/bin/vinw project list
.venv/bin/vinw status ./projects/my-app
```

`vinw status` prints the project name, current descent and layer, pending confirmations, and ascent count. Then ask the agent to call `se_get_project`; it must return the same project.

### Troubleshooting

| Symptom | Cause and fix |
|---------|---------------|
| `vinw: command not found` | Use `.venv/bin/vinw`, or activate the venv, or install globally with `pipx install .` |
| Import points at `site-packages/vinw` | Stale non-editable install; reinstall with `pip install -e .` |
| New project missing from the TUI selector | Run `vinw project list`. If absent, register it: `vinw project add <path> --name <name>`. In current revisions, `vinw init` and `se_init_project` register automatically; `--no-register` / `register=false` opts out, and a registry failure is reported as a warning |
| `sqlite3.OperationalError: unable to open database file` | `$VINW_HOME` (default `~/.vinw`) is not writable, often because the agent runs in a sandbox. Set `VINW_HOME` to a writable directory |
| MCP tools do not appear after configuration | Restart or reload the harness; check its MCP log; ensure the `command` path is absolute and executable |
| `No active project` from a tool | `se_use_project("<name>")`, or pass `project="<path-or-name>"` to the tool |
| HTTP server exits immediately | Port already in use; choose another `--port` |
| TUI says no project | Press `p` to open the selector, or start with `vinw tui <path\|name>` |

## Watching Progress

The same state is visible from three surfaces: the TUI for humans, MCP tools for agents, and the CLI for scripts.

### For humans: the TUI

```bash
.venv/bin/vinw tui                    # project selector
.venv/bin/vinw tui my-app             # by registered name
.venv/bin/vinw tui ./projects/my-app  # by path
```

The TUI does not modify project documents or workflow state. It polls the project files every **2 seconds**, so it can stay open in a second terminal while an agent works. It never blocks the agent; the only write it makes is the registry's last-accessed timestamp when you switch projects. If a file is caught mid-write, it keeps the last good render and shows the error instead of crashing.

**Keys**

| Key | Action |
|-----|--------|
| `p` | Open the project selector |
| `↑` / `↓` + `Enter` | Choose a project (in the selector) |
| `Esc` | Cancel the selector |
| `r` | Force an immediate refresh |
| `q` | Quit |

**The three panels**

1. **Top — layer graph.** Current descent and layer, each layer's state and latest baseline, ascent arrows with their reasons, L4 consistency and drift badges, and a drift warning panel when code and design disagree.
2. **Middle — todos and gates.** Open todo items across layers, split into `🔒 blocking` (blocks the supported advance path) and `🔓 review-only` (does not block it), with counts.
3. **Bottom — state and recent changes.** Whether the project can descend, the recommended next call, contextual hints, and the last three changelog entries.

**Layer legend**

| Mark | Meaning |
|------|---------|
| `◆` | Current layer, when it is already baselined (bold cyan) |
| `▶` | In progress (bold yellow when it is the current layer) |
| `✅` | Baselined |
| `↻` | Superseded — needs redo in this descent |
| `🏁` | Completed (L7 only) |
| `○` | Pending / never started |
| dim green | A passed baseline or completed layer that is not current |

**L4 audit badges**

| Badge | Meaning |
|-------|---------|
| `chk✓` | Text consistency passed |
| `chk!` | Text consistency found inconsistencies |
| `chk⚙` | Consistency check could not run (configuration error) |
| `⚠冲突` | Text and LLM verdicts conflict; likely an extractor defect |
| `·待审` | An LLM verdict is required but missing |
| `/llm✓` | LLM verdict passed |

**Drift badges**

| Badge | Meaning |
|-------|---------|
| `⚠漂移` | Code changed after the approved design |
| `🚫设计滞后` | Code moved ahead of the design; update L3 first |
| `⚠需重审` | Design changed; the previous audit no longer applies |
| `⚠漂移未知` | The fingerprint is unavailable; do not treat as clean |

**What to watch while an agent works**

- **Current layer / descent changed?** That is a baseline, descend, or ascend event. Check the bottom panel for the reason.
- **A `🔒` gate appeared?** `se_can_descend` will refuse until a human decides. The TUI cannot approve it; tell the agent your decision so it can call `se_resolve_confirmation`.
- **`🚫设计滞后` or `chk!`?** Do not let the agent push on. It must fix the implementation or ascend to L3.
- **Todos moving?** The middle panel is the cheapest progress indicator.
- **Changelog tail?** The bottom panel shows the last three entries; the full append-only log is in `.vinw/changelog.md`.

### For agents: MCP tools and CLI

Agents should treat the MCP tools as the API and the TUI as a read-only monitor. The source of truth is `<project>/.vinw/manifest.md`.

| Question | Call |
|----------|------|
| What is the full state? | `se_get_project` — layer graph, ascents, blocking gates, review items, consistency, drift |
| What should I do next? | `se_get_next_steps` — work list, gate, next transition, special instruction |
| What is left? | `se_get_todos` — todos across non-superseded layers |
| What changed recently? | `se_get_changelog(limit=...)` |
| Can I descend? | `se_can_descend` |
| What baselines exist? | `se_list_baselines(layer=...)` |
| What documents exist? | `se_list_documents(layer=...)` |
| Does a human need to decide? | `se_get_escalations`, `se_triage_prompt` |
| Which projects are known? | `se_list_projects`, `se_use_project`, or the `project=` argument |

**Startup resolution.** `vinw server` auto-loads a project from `cwd/vinw-design/.vinw/manifest.md` or `cwd/.vinw/manifest.md`. If neither exists, call `se_use_project("<name-or-path>")` once or pass `project="<name-or-path>"` to individual tools.

**A practical polling discipline**

```
Start of a session or after a layer switch:
  se_get_project

Before choosing an action:
  se_get_next_steps

While working:
  se_get_todos
  se_get_changelog(limit=5)

Before baseline or descend:
  se_can_descend
  se_get_project          # read consistency and drift

When audit findings appear:
  se_get_escalations
  se_triage_prompt

After a change:
  se_get_changelog        # confirm the write was recorded

At the end of a layer:
  se_get_project          # verify status and baseline
```

Do not poll in a tight loop. Call these at state boundaries; the TUI already provides continuous observation for the human.

**Shell-level checks** work too, and are useful in CI or when the agent cannot reach MCP tools:

```bash
.venv/bin/vinw status ./projects/my-app
.venv/bin/vinw project list
.venv/bin/vinw project history my-app
```

**Ask your agent for a progress report.** A reliable prompt is:

```text
Report VINW progress for this project. Use se_get_project and
se_get_next_steps. Give me: current layer and descent, all blocking gates,
open todos, consistency and drift status, and the single next action. If a
human decision is pending, quote the gate id and the exact decision you need.
```

### Watching together

The TUI and MCP tools are designed to run at the same time:

- The TUI **reads project state**; MCP tools **write it**. The TUI cannot corrupt the workflow.
- The TUI refreshes every 2 seconds, so it usually shows a new state before the agent's summary arrives.
- The agent sees the same facts through `se_get_project`, so the human and the agent cannot tell two different stories about the same layer.
- If the TUI and the agent disagree, `manifest.md` wins. Ask the agent to read it directly.

## MCP Tools

38 tools, grouped by job. Every project-scoped tool accepts an optional `project` argument (path or registered name); when omitted, the active project is used. Registry tools operate on the registry itself.

| Area | Tools |
|------|-------|
| **Project lifecycle** | `se_init_project`, `se_get_project`, `se_complete_project` |
| **Registry** | `se_register_project`, `se_list_projects`, `se_use_project`, `se_remove_project`, `se_set_project_state`, `se_project_history`, `se_export_projects`, `se_prune_projects` |
| **Documents & baselines** | `se_store_document`, `se_read_document`, `se_list_documents`, `se_list_baselines` |
| **Workflow** | `se_baseline`, `se_ascend`, `se_descend`, `se_can_descend` |
| **Gates** | `se_require_confirmation`, `se_resolve_confirmation`, `se_purge_confirmations` |
| **Change log** | `se_log_change`, `se_get_changelog` |
| **Todos & guidance** | `se_get_todos`, `se_update_todo`, `se_get_next_steps` |
| **Audit & triage** | `se_check_consistency`, `se_store_consistency_report`, `se_triage_prompt`, `se_store_triage`, `se_get_escalations`, `se_record_triage_decision` |
| **Repair** | `se_repair_state`, `se_sync_layer_readmes` |
| **Search** | `se_search_proposals` |

The authoritative tool contracts live in [`vinw-design/L3-方案细化/api-design.md`](vinw-design/L3-方案细化/api-design.md). The design catalog is generated from `vinw/server.py` and checked by a test, so the published list and the implementation cannot silently diverge.

## Citation & Reference Format

### Citing VINW

If you use VINW in academic work, a report, or another project, cite the software and, when the claim depends on a specific state, pin the commit.

**Plain text**

```text
M0reDr1nk. VINW: Vibe Is Not Wish MCP (Version 0.2.0) [Computer software].
2026. https://github.com/M0reDr1nk/vibe-is-not-wish-mcp
```

**BibTeX**

```bibtex
@software{vinw2026,
  author       = {M0reDr1nk},
  title        = {{VINW}: Vibe Is Not Wish MCP},
  year         = {2026},
  version      = {0.2.0},
  url          = {https://github.com/M0reDr1nk/vibe-is-not-wish-mcp},
  note         = {Markdown-first, spiral-ascend workflow engine for strict
                  software engineering process control}
}
```

**Pinning a commit.** For reproducible claims, cite a commit-pinned URL instead of `main`:

```text
https://github.com/M0reDr1nk/vibe-is-not-wish-mcp/tree/<commit-sha>
```

For example, the self-hosting statistics in this README were compiled at `830a5c2`; cite that commit if you are reproducing the table. State the commit you actually inspected, not the newest one by default.

### Referencing the audit trail

VINW's records use stable, short identifiers. They are designed to be quoted in issues, reviews, and papers without ambiguity.

| Kind | Format | Scope | Example |
|------|--------|-------|---------|
| Commit | 7-character short SHA | Repository | `830a5c2` |
| Baseline | `vNNN` | Layer | `L4-编码实现/v013` |
| Ascent | `asc-NNN` | Project | `asc-013` |
| Change | `chg-YYYYMMDD-HHMMSS-NNN` | Project | `chg-20261114-030842-147` |
| Confirmation | `cfm-YYYYMMDD-HHMMSS-NNN` | Project | `cfm-20261113-153121-001` |
| Consistency report | `report-<id>[-NN].md` | Project | `report-954217cd` |
| Finding | `INC-NNN` / `GAP-NNN` | **Report-local** | `report-954217cd/INC-001` |
| Design or code location | `file:line` or `file:start-end` | Repository | `api-design.md:610-612` |
| Layer document | `<layer>/<filename>` | Project | `L3-方案细化/api-design.md` |

Two rules matter when citing findings:

1. **Finding IDs are report-local.** `INC-001` exists in several reports with different meanings; for example, `report-7474b697/INC-001` and `report-954217cd/INC-001` are different defects. Always qualify it with the report: `report-954217cd/INC-001`, not `INC-001`.
2. **Report IDs are usually content-derived.** Most are hashes of the report content; a `-NN` suffix marks a re-check or a second part. Some early reports use a descriptive ID such as `report-L4-r1-text.md`. Cite the filename as stored under `L4-编码实现/consistency-reports/`.

For a review comment, the full form is:

```text
report-954217cd/INC-001 (impl_bug, confidence=high)
```

### Referencing literature in L2

L2 uses three prefixes so that a claim can be traced to its kind of source:

| Prefix | Use for | Example |
|--------|---------|---------|
| `ref-NNN` | Academic papers, standards, official documentation | `ref-001` |
| `oss-NNN` | Open-source projects, products, existing implementations | `oss-001` |
| `internal-NNN` | Internal or historical projects used as evidence (same pattern as `ref-`/`oss-`) | `internal-001` |

Each entry lives in [`L2-参考文献与方案搜证汇总/references.md`](vinw-design/L2-参考文献与方案搜证汇总/references.md) with its title, source/link, key conclusion, and relevance. The evidence matrix and synthesis should cite the ID (`ref-001`), not repeat a bare URL; this keeps the evidence chain stable when a link moves.

### Repo-internal links

- Use relative paths for files in this repository.
- Use commit permalinks for evidence that must remain stable: `https://github.com/M0reDr1nk/vibe-is-not-wish-mcp/blob/<commit-sha>/<path>#Lx-Ly`.
- Do not cite a moving branch when the claim depends on a specific line; pin the commit and the line range.

## License

MIT
