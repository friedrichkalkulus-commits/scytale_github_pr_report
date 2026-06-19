# AI Prompt: Build a JIRA Integration

This file contains a ready-to-use prompt for an AI coding assistant. Its goal is to reproduce this project's approach (extract, analyse, report) for JIRA instead of GitHub, reusing the project's shared, source-agnostic machinery.

Copy the prompt below (everything inside the prompt block) and give it to an AI coding assistant working inside this repository.

---

## The Prompt

You are a data engineer extending an existing integration project. The project currently connects to GitHub, fetches merged pull requests from a repository, and produces a report on whether each was peer-reviewed and passed its checks before merging, in effect, evidence for a code-review compliance control. Your task is to build an equivalent integration for **JIRA**, following the same structure and reusing the same shared machinery.

### Step 1 - Understand the existing project first

Before writing any code, read these existing files to understand the structure you are mirroring:

- `extract.py` - fetches raw data from GitHub's API (authentication, endpoints, pagination). Note how configuration is passed in as function arguments, not hardcoded.
- `transform.py` - computes the judgements (`CR_Passed`, `CHECKS_PASSED`) from the raw data, with its rules kept next to the functions that use them.
- `main.py` - owns all configuration and file paths, and orchestrates the steps.
- `utils.py` - general, source-agnostic helpers (`save_json`, `load_json`, `write_csv`). **These are not specific to GitHub and must be reused unchanged.**

**Most importantly, read `ai_utils/project_context.md` in full before doing anything else.** It describes the project's purpose, architecture, design decisions, definitions, and known limitations in detail. It is the single best source for understanding not just *what* the project does but *why* it is built the way it is, which is exactly what you need to reproduce its approach faithfully for JIRA.

The guiding principle of this project is a separation between **source-specific** code (fetching and judging, which differ per source) and **general** code (reading, writing, and CSV output, which stay the same). Preserve this principle.

### Step 2 - Research the JIRA API and map the concepts

JIRA's entities are not identical to GitHub's, so do not assume a one-to-one translation. Research the relevant parts of the JIRA REST API and determine the appropriate equivalents. In particular:

- JIRA is organised around **issues** (tickets) within projects, not pull requests. The unit of the report is a JIRA issue.
- Authentication uses an **API key/token** (with the user's email), not a GitHub personal access token. Handle it the same secure way: read it from a `.env` file, never hardcode it, and keep `.env` out of version control.
- GitHub's "approved by a reviewer" and "checks passed" have no exact JIRA equivalents. Research what JIRA *does* offer as evidence that a ticket followed its required process, for example, whether it passed through required workflow states, received necessary approvals, or had required fields completed before being closed/resolved. Choose defensible equivalents and **document your choice and reasoning**, exactly as the GitHub project documents its `CR_Passed` and `CHECKS_PASSED` definitions (see the "Key definitions and decisions" section of `ai_utils/project_context.md` for the model to follow). Where JIRA genuinely has no parallel to a GitHub concept, say so rather than forcing a false mapping.

### Step 3 - Build the integration, mirroring the structure

Create the JIRA equivalents of the source-specific modules, mirroring the existing ones:

- A JIRA extraction step that fetches the raw issue data from the JIRA API and saves it as JSON, taking its configuration (which project, how many issues, output path) as function arguments, just as `extract.py` does.
- A JIRA transformation step that computes the chosen judgements per issue and produces a report with clearly named columns, just as `transform.py` does.
- Orchestration that owns the JIRA configuration and runs the steps in order, just as `main.py` does.

**Reuse `utils.py` unchanged** for all JSON reading/writing and CSV output. Do not duplicate or modify it. If a genuinely general helper is missing, add it to `utils.py` so it remains shared.

### Step 4 - Match the project's quality standards

- Keep configuration in one place (the orchestration layer), passed into the functions as arguments.
- Handle errors and edge cases gracefully (missing fields, empty results, failed fetches), as the GitHub version does.
- Produce the same kinds of outputs: a raw JSON of fetched data, a processed report, and a CSV.
- Document the JIRA-specific definitions, assumptions, and limitations, following the example set in `ai_utils/project_context.md`, particularly its "Assumptions and limitations" section, which shows the expected level of openness about scope and edge cases.
- If you are unsure about any JIRA API behaviour, say so rather than guessing.

### Design note

If this project were to support many integrations at once, an object-oriented design, a shared base class defining the common extract/transform/report flow, with one subclass per source (GitHub, JIRA, ...), would be a natural way to formalise the shared-versus-specific separation. For a single additional integration, mirroring the existing module structure (as described above) is a simpler and sufficient approach.