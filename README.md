# 🌟 AURA CLI: The Agentic Developer Shield

> **Your AI-powered command-line companion for secure, sustainable, and mindful development.**  
> Aura scans for secrets, tracks your flow state, audits carbon efficiency, and automates project scaffolding—all powered by GitHub Copilot.

---

## 📋 Table of Contents

- [Prerequisites](#-prerequisites)
- [Quick Installation](#-quick-installation)
- [The Five Pillars](#-the-five-pillars)
  - [🛡️ Check (Shield)](#️-check-shield)
  - [🔥 Pulse (Wellness)](#-pulse-wellness)
  - [📖 Story (Narrator)](#-story-narrator)
  - [🌿 Eco (Auditor)](#-eco-auditor)
  - [🚀 Fly (Takeoff)](#-fly-takeoff)
- [Command Reference](#-command-reference)
- [Architecture](#-architecture)
- [Developer's Note](#-developers-note)

---

## ⚠️ Prerequisites

Before using Aura CLI, ensure you have the following installed:

| Requirement | Version | Installation |
|-------------|---------|--------------|
| **Python** | 3.10+ | [python.org](https://python.org) |
| **GitHub Copilot Subscription** | Active | [GitHub Copilot](https://github.com/features/copilot) |
| **Copilot CLI** | Latest | `npm install -g @github/copilot` |

> **🔐 CRITICAL: Authentication Required**
> 
> Before running any Aura command, you **MUST** authenticate with GitHub Copilot:
> ```bash
> copilot /login
or "copilot -i/login
> ```
> Run this in a separate terminal and complete the authentication flow. Aura will not function without valid Copilot credentials.

---

## 🚀 Quick Installation

**Make Aura globally accessible in just two commands:**

```bash
# Make the script executable
chmod +x aura.py

# Create a global symlink (requires sudo)
sudo ln -s $(pwd)/aura.py /usr/local/bin/aura
```

**Install dependencies:**

```bash
pip install -r requirements.txt
```

**Verify installation:**

```bash
aura --help
```

---

## 🏛️ The Five Pillars

Aura is built around five core modules, each designed to enhance a critical aspect of modern development.

---

### 🛡️ Check (Shield)

**Security vulnerability scanning with AI-powered remediation.**

The Shield module performs deep filesystem scans to detect exposed secrets, API keys, and misconfigured environment files. When threats are found, Aura consults GitHub Copilot to generate **step-by-step remediation guidance** tailored to your specific situation.

**Features:**
- 🔍 **AWS Access Key Detection** — Catches exposed `AKIA*` patterns
- 🔍 **Google API Key Detection** — Identifies `AIza*` credentials
- 🔒 **`.env` Permission Auditing** — Flags insecure file permissions
- 🤖 **AI Remediation** — Copilot generates exact `git filter-branch` commands to clean your history

```bash
aura check
# Alias: aura sec
```

---

### 🔥 Pulse (Wellness)

**Flow-state tracking and developer wellness dashboard.**

Pulse monitors your coding activity to determine whether you're in **FLOW**, **STEADY**, or **REST** mode. It displays an activity histogram, focus gauge, and micro-action suggestions. When idle, Aura enters **Zen Mode** and offers AI-generated stretch exercises to keep you healthy.

**Features:**
- 📊 **Activity Histogram** — Visualize your last 6 hours of edits
- 🎯 **Focus Gauge** — Real-time flow state indicator
- 🧘 **Zen Mode** — AI-powered physical stretch suggestions when idle
- 🔥 **Flow Animation** — Celebratory flame animation when you're in the zone

```bash
aura pulse
# Aliases: aura health, aura p
```

| Flag | Description |
|------|-------------|
| `--no-ai` | Skip AI wellness suggestions |
| `--hours N` | Adjust histogram window (default: 6) |
| `--idle N` | Set idle threshold in minutes (default: 15) |

---

### 📖 Story (Narrator)

**Transform Git diffs into professional Founder's Journal entries.**

Story analyzes your recent code changes and uses GitHub Copilot to generate a **confident, inspirational narrative** about your progress. Entries are automatically appended to `STORY_JOURNAL.md`, creating a living record of your development journey.

**Features:**
- 📝 **Automatic Journaling** — Git diff → professional prose
- 🎉 **Proud Messaging** — Celebratory tone to keep you motivated
- 📚 **Persistent History** — All entries saved to `STORY_JOURNAL.md`
- ✨ **AI-Powered** — Copilot crafts inspiring narratives from raw code changes

```bash
aura story
# Alias: aura doc
```

---

### 🌿 Eco (Auditor)

**Carbon efficiency auditing with Big O complexity analysis.**

The Eco module scans your codebase for **energy-heavy files** and uses Copilot to analyze algorithmic complexity. It assigns a **Carbon Grade (A-F)** based on bloat and efficiency, then tracks your progress in a persistent **Green Journal* (`GREEN_AUDIT.md`).

**Features:**
- 📁 **Static Bloat Scan** — Identifies files >50MB that waste storage/bandwidth
- 🧠 **AI Complexity Audit** — Copilot analyzes Big O patterns (nested loops, quadratic operations)
- 🌱 **Carbon Grading** — A-F scale based on code sustainability
- 📈 **Progress Tracking** — "Getting Greener" / "More Bloated" / "Stable" indicators
- ⚡ **Zerve Recommendations** — Suggests batch processing and serverless patterns

```bash
aura eco
# Alias: aura deps
```

| Grade | Meaning |
|-------|---------|
| **A** | Excellent — O(n) or better, minimal bloat |
| **B** | Good — Efficient with minor improvements possible |
| **C** | Fair — Some quadratic patterns or large assets |
| **D** | Poor — Nested loops or heavy files detected |
| **F** | Critical — Major bloat + nested loops |

---

### 🚀 Fly (Takeoff)

**Agentic project onboarding with AI-generated scaffolding.**

Fly automates the "blank page" phase of development. Tell Aura what you want to build, and Copilot generates **5 essential setup commands**. You review the plan, confirm, and Aura executes each step interactively with retry/skip options.

**Features:**
- 🤖 **AI Command Generation** — Copilot plans your project setup
- ✅ **Safety Confirmation** — Review commands before execution
- 🔄 **Interactive Execution** — Retry, skip, or abort each step
- 📖 **Auto-Documentation** — Runs `aura story` after setup to document your new project

```bash
aura fly "Next.js with Tailwind"
aura fly "Python FastAPI"
aura fly "React TypeScript"
# Alias: aura init
```

---

## 📖 Command Reference

| Command | Alias | Description |
|---------|-------|-------------|
| `aura check` | `sec` | Security vulnerability scanning |
| `aura pulse` | `health`, `p` | Developer wellness dashboard |
| `aura story` | `doc` | AI-powered Founder's Journal |
| `aura eco` | `deps` | Carbon efficiency audit |
| `aura fly "<type>"` | `init` | Agentic project scaffolding |

**Global Flags:**

| Flag | Description |
|------|-------------|
| `--help` | Show help message |
| `--version` | Display version information |
| `--no-ai` | Skip AI features (where applicable) |
| `--compact` | JSON output for CI/CD pipelines |

---

## 🏗️ Architecture

Aura CLI is built with **1,700+ lines of robust Python**, designed for reliability and extensibility.

**Core Technologies:**

| Component | Technology |
|-----------|------------|
| **CLI Framework** | Python `argparse` with subcommand pattern |
| **Terminal UI** | [Rich](https://github.com/Textualize/rich) — Panels, Tables, Spinners, Markdown rendering |
| **AI Integration** | GitHub Copilot CLI via subprocess with stdin interaction |
| **Theming** | Module-specific color palettes (Red/Magenta/Blue/Green/Yellow) |

**Design Principles:**

- 🎨 **Distinct Visual Identity** — Each module has its own color theme
- 🔄 **Consistent AI Output** — `render_ai_output()` helper ensures uniform formatting
- 📁 **Persistent Journals** — `GREEN_AUDIT.md` and `STORY_JOURNAL.md` track your progress
- ⚡ **Smart Exclusions** — Ignores `.git`, `node_modules`, `__pycache__`, etc.

---

## 👨‍💻 Developer's Note

> **This project was built as part of a 2nd-year BCA academic initiative to explore the boundaries of AI Agent workflows.**

Aura represents an experiment in **human-AI collaboration**—where the CLI acts not just as a tool, but as an intelligent partner that understands context, suggests improvements, and celebrates your wins.

Built for the **GitHub Copilot CLI Hackathon**, Aura demonstrates how AI can enhance every stage of development: from security scanning to wellness tracking to sustainable coding practices.

---

<p align="center">
  <strong>Built with 💜 using GitHub Copilot</strong><br>
  <em>Secure. Mindful. Sustainable.</em>
</p>
