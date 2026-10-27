# AURA CLI — The Agentic Developer Shield

A Python command-line companion built for the **GitHub Copilot CLI Hackathon** to explore AI-assisted security, developer wellness, journaling, sustainability checks, and project onboarding.

## At a glance

- **1,700+ lines of Python** documented in the project README.
- Five command groups: `check`, `pulse`, `story`, `eco`, and `fly`.
- Uses GitHub Copilot CLI for AI-assisted suggestions and Rich for terminal UI.

## Five modules

- **Check / Shield:** scans for common exposed-key patterns and insecure `.env` permissions; can request AI remediation guidance.
- **Pulse / Wellness:** displays recent edit activity and flow-state indicators, with optional AI-generated break suggestions.
- **Story / Narrator:** turns recent Git changes into development journal entries saved to `STORY_JOURNAL.md`.
- **Eco / Auditor:** checks large files and code patterns for possible complexity/efficiency concerns, with an A–F grade and a persistent audit log.
- **Fly / Takeoff:** proposes a small project setup plan, asks for confirmation, and executes commands interactively with retry/skip options.

## Architecture and stack

Python 3.10+ · argparse · Rich · GitHub Copilot CLI invoked as a subprocess.

## Safety and scope

The command tool relies on local filesystem observations and Copilot-generated advice; it should not be treated as a dedicated security scanner or a verified carbon-measurement tool. Review generated commands before execution and use the project only with appropriate Copilot CLI access.
