# VINW Workflow — Kimi Plugin

VINW (Vibe Is Not Wish) spiral-ascend software engineering process control skill for Kimi.

## What it does

This skill teaches Kimi to follow a strict 7-layer spiral workflow when building software projects:

1. **L1 Requirements** — Decompose user intent into atomic, verifiable requirements
2. **L2 Evidence** — Research existing solutions, literature, and alternatives
3. **L3 Design** — Refine architecture and API design based on evidence
4. **L4 Implementation** — Code strictly against the design documents
5. **L5 Testing** — Validate implementation and catch design-level defects
6. **L6 Cleanup** — Remove debug code, unify style, sync docs
7. **L7 Final Verification** — Archive project with a completion report

## Key features

- **Baseline freeze/rollback** — Each layer can be frozen as a read-only snapshot
- **Spiral ascend** — Roll back to any upper-layer baseline when design defects are found
- **Confirmation gates** — Blocking human-in-the-loop checkpoints at critical transitions
- **Atomic change log** — Every modification is logged with before/after states
- **Consistency checks** — Verify code matches design documents

## How to use

1. Install this plugin in Kimi
2. Say: "用 VINW 工作流帮我实现一个 Python CLI 工具"
3. Kimi will initialize the project structure and guide you through each layer

## Relationship with VINW MCP Server

This skill provides the **methodology layer**. If you also run the VINW MCP Server locally (`vinw server --http`), the skill will use MCP tools for state machine operations. Without the server, the skill guides Kimi to manage the Markdown project structure using native file tools.
