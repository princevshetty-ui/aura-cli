# 🚀 Aura CLI - Complete User Guide

## Overview

**Aura** is a comprehensive CLI tool for developers that provides intelligent insights across five key domains:

- **Check** (🛡️) - Security vulnerability and secret scanning
- **Pulse** (💓) - Productivity analysis and wellness suggestions  
- **Story** (📖) - Code documentation generation
- **Eco** (🌍) - Green computing and sustainability audit
- **Fly** (🚀) - Performance optimization checks

---

## Installation & Setup

### Prerequisites
- Python 3.7+
- Rich library (`pip install rich`)
- Optional: GitHub Copilot CLI (for AI-powered suggestions)

### Quick Start
```bash
python3 aura.py --help              # Show all commands
python3 aura.py pulse               # Run productivity analysis
python3 aura.py check               # Run security scan
```

---

## Command Reference

### 1. **Aura Pulse** - Productivity & Wellness

**Purpose**: Monitor your coding activity, detect when you're idle, and offer personalized wellness suggestions.

#### Basic Usage
```bash
python3 aura.py pulse               # Standard run (full UI)
python3 aura.py p                   # Short alias
python3 aura.py health              # Long alias
```

#### Flags
| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--no-ai` | boolean | false | Skip Copilot suggestions (faster) |
| `--hours` | int | 6 | Activity histogram window (1-24 hours) |
| `--compact` | boolean | false | JSON output only (for CI/automation) |
| `--idle` | int | 15 | Idle threshold in minutes for Zen Break |
| `--force-zen` | boolean | false | Force Zen Break without waiting |

#### Examples

```bash
# Standard wellness check with full UI
python3 aura.py pulse

# Check with 12-hour activity window
python3 aura.py pulse --hours 12

# Low idle threshold (trigger break faster)
python3 aura.py pulse --idle 5

# Without Copilot (no network call, faster)
python3 aura.py pulse --no-ai

# JSON output for scripts/CI
python3 aura.py pulse --compact

# Force Zen Break for testing
python3 aura.py pulse --force-zen

# Combine flags
python3 aura.py pulse --idle 10 --hours 12 --no-ai
```

#### Output Explained

**FLOW State** (< 5 minutes since last edit)
- You're actively coding
- Shows flame animation
- No break suggestion

**STEADY RHYTHM** (5-30 minutes since last edit)  
- Good progress, consistent activity
- Checkpoint recommendation
- No break suggestion yet

**REST State** (30+ minutes since last edit)
- Time for a break
- Zen Break with wellness suggestion
- Bell notification (optional)

#### Focus Score
- 10/10 = Just edited (< 1 min)
- 5/10 = Some idle time (30-60 min)
- 0/10 = Significant idle (2+ hours)

#### Compact JSON Output
```json
{
  "latest": "aura.py",
  "minutes_since": 3,
  "focus_score": 0.97,
  "touched_5m": 1,
  "touched_30m": 1,
  "touched_60m": 4,
  "touched_24h": 5
}
```

---

### 2. **Aura Check** - Security Scanning

**Purpose**: Scan your codebase for security vulnerabilities, secrets, and common risks.

#### Basic Usage
```bash
python3 aura.py check               # Run security check
python3 aura.py sec                 # Alias
```

#### Flags
| Flag | Type | Description |
|------|------|-------------|
| `--preview` | boolean | Show suggestions without running fixes |

#### Examples
```bash
# Full security check
python3 aura.py check

# Preview mode (show issues without fixing)
python3 aura.py check --preview
```

#### Checks Performed
- ✓ Secret detection (API keys, tokens, credentials)
- ✓ `.env` file permissions (should be 0600)
- ✓ Common vulnerabilities
- ✓ AI-powered remediation suggestions (if Copilot available)

---

### 3. **Aura Story** - Documentation

**Purpose**: Auto-generate code documentation and docstrings.

#### Usage
```bash
python3 aura.py story               # Generate documentation
python3 aura.py doc                 # Alias
```

---

### 4. **Aura Eco** - Green Computing Audit

**Purpose**: Scan for filesystem bloat, assess algorithmic complexity, and generate a sustainability report.

#### Usage
```bash
python3 aura.py eco                 # Run green computing audit
python3 aura.py deps                # Alias

# Generates GREEN_AUDIT.md with the findings
```

---

### 5. **Aura Fly** - Performance

**Purpose**: Analyze performance optimization opportunities.

#### Usage
```bash
python3 aura.py fly                 # Run performance check
python3 aura.py perf                # Alias
```

---

## Use Cases & Examples

### Use Case 1: Daily Productivity Check
```bash
# In the morning, check your activity
python3 aura.py pulse

# This shows:
# - Your coding activity over the last 6 hours
# - Focus score (how active you've been)
# - Suggested micro-actions
# - Wellness recommendations if idle
```

### Use Case 2: CI/CD Integration
```bash
# In GitHub Actions or CI pipeline
python3 aura.py pulse --compact --no-ai

# Output: Single JSON line, no animations or API calls
# Perfect for metrics collection
```

### Use Case 3: Standing Desk Reminder
```bash
# Run periodically to get wellness breaks
python3 aura.py pulse --idle 30

# When idle > 30 minutes, get a stretch suggestion
# Useful with cron: */30 * * * * python3 aura.py pulse --idle 30 --no-ai
```

### Use Case 4: Security Audit
```bash
# Check for secrets in your repo
python3 aura.py check

# Get AI-powered remediation suggestions
# (requires Copilot CLI installed and authenticated)
```

### Use Case 5: Quick Metrics
```bash
# Get JSON metrics for dashboard
python3 aura.py pulse --compact

# Parse and visualize metrics in your monitoring tool
```

---

## Input Validation & Error Handling

All inputs are validated for safety:

| Invalid Input | Behavior |
|---------------|----------|
| `--hours 100` | Clamped to 24 (max) with warning |
| `--hours 0` | Clamped to 1 (min) with warning |
| `--idle -5` | Clamped to 0 (min) with warning |
| `--idle abc` | Error: must be integer |
| Invalid command | Shows help and usage |

---

## Copilot Integration

### Requirements
- GitHub Copilot CLI installed: `brew install GitHub/gh-oss/copilot` (macOS) or equivalent
- Authenticated: Run `copilot -i /login` in your terminal

### How It Works
- When you're idle for 15+ minutes, Aura fetches a wellness suggestion from Copilot
- Non-intrusive: Uses 30-second timeout, graceful fallback if unavailable
- Can be disabled with `--no-ai` flag

### Troubleshooting
If Copilot suggestions don't appear:
1. Check Copilot is installed: `which copilot`
2. Authenticate: `copilot -i /login`
3. Try again in a new terminal
4. Or use `--no-ai` flag to skip

---

## Performance & Timing

| Operation | Duration | Notes |
|-----------|----------|-------|
| Pulse (compact) | < 1s | JSON only, no UI |
| Pulse (full UI) | 2-3s | Includes animations |
| Pulse + Copilot | 5-10s | Waiting for wellness suggestion |
| Check (basic) | 1-2s | Secret scanning |
| Check + Copilot | 10-15s | With remediation suggestions |

---

## Tips & Tricks

### 1. Set Up Auto-Run with Cron
```bash
# Check productivity every 2 hours
0 */2 * * * /usr/bin/python3 ~/aura/aura.py pulse --idle 30 --no-ai

# Morning security check
0 8 * * * /usr/bin/python3 ~/aura/aura.py check --preview
```

### 2. Parse JSON in Scripts
```bash
# Get focus score
python3 aura.py pulse --compact | jq '.focus_score'

# Count files edited in last 5 minutes
python3 aura.py pulse --compact | jq '.touched_5m'
```

### 3. Suppress Animations (Headless)
```bash
# Use --compact for CI/headless environments
python3 aura.py pulse --compact
```

### 4. Force Tests Without Waiting
```bash
# Test Zen Break without being actually idle
python3 aura.py pulse --force-zen --no-ai
```

---

## Troubleshooting

### Issue: Command times out
**Solution**: Use `--compact` and `--no-ai` flags
```bash
python3 aura.py pulse --compact --no-ai
```

### Issue: "No analyzable files found"
**Solution**: Make sure you have files in your workspace
- Aura scans `.py`, `.js`, `.ts`, `.rs`, `.go`, `.java`, etc.
- Must be within current directory and subdirectories

### Issue: Copilot suggestions not appearing
**Solution**: 
1. Run: `which copilot` (must exist)
2. Run: `copilot -i /login` (re-authenticate)
3. Try: `python3 aura.py pulse --force-zen`

### Issue: JSON output malformed
**Solution**: Use `--compact` flag, don't pipe through other commands
```bash
python3 aura.py pulse --compact  # ✓ correct
python3 aura.py pulse | grep json  # ✗ wrong
```

---

## Security & Privacy

- ✓ All code runs locally
- ✓ Workspace files never uploaded (only timestamps used)
- ✓ Optional Copilot integration (can be disabled)
- ✓ No telemetry or tracking
- ✓ Safe for production use

---

## Contributing

Found a bug? Have a feature request?

1. Test the issue: `python3 aura.py pulse --no-ai`
2. Report details: command used, error message, environment
3. Submit issue on GitHub

---

## Version

Current version: **0.1.0**

```bash
python3 aura.py --version
```

---

## Quick Reference Card

```
PULSE (Productivity)
  aura pulse              Full UI with analysis
  aura p                  Short alias
  aura pulse --compact    JSON output
  aura pulse --no-ai      No Copilot call
  aura pulse --idle 10    Custom idle threshold

CHECK (Security)
  aura check              Full security scan
  aura sec                Alias
  aura check --preview    Show without fixing

OTHER
  aura story / doc        Generate documentation
  aura eco / deps         Dependency analysis
  aura fly / perf         Performance analysis
  aura --help             Show full help
  aura --version          Show version
```

---

**Happy coding! 🚀**

