# Copilot Instructions for Aura CLI

## Project Overview
**Aura** is a modular Python CLI tool designed for the GitHub Copilot CLI hackathon. It provides intelligent insights across five key development domains: security, code health, documentation, dependencies, and performance.

## Architecture & Key Components

### Command Structure
Aura uses Python's `argparse` library with a subcommand pattern. Five main commands with aliases:
- **check** (alias: sec) - Security vulnerability scanning
- **pulse** (alias: health) - Code quality and health metrics  
- **story** (alias: doc) - Code documentation generation
- **eco** (alias: deps) - Dependency and ecosystem analysis
- **fly** (alias: perf) - Performance optimization checks

Each command has a dedicated handler function (`cmd_*`) that executes the analysis.

### Styling & Output
The `Colors` class provides ANSI color codes for terminal styling. All output uses `print_styled_message()` which:
1. Combines emoji + title + descriptive message
2. Applies color and bold formatting 
3. Gracefully falls back to plain text if unsupported

Messages follow the format: `emoji Title\n   message`

## Development Patterns

### Adding New Commands
1. Create handler function: `def cmd_<name>(args):`
2. Call `print_styled_message(emoji, title, message, color)` with appropriate emoji and color
3. Add subparser in `main()`: `subparsers.add_parser('name', help='...', aliases=['short']).set_defaults(func=cmd_<name>)`

### Color Convention
- **RED** (🛡️ check) - Security/warnings
- **GREEN** (💓 pulse) - Health/positive
- **BLUE** (📖 story) - Documentation/information
- **CYAN** (🌍 eco) - System/ecosystem
- **MAGENTA** (🚀 fly) - Performance/speed

## Getting Started

### Running the CLI
```bash
python3 aura.py --help          # Show help
python3 aura.py check           # Run security check
python3 aura.py pulse           # Run code health analysis
python3 aura.py check --help    # Show command-specific help
```

### Key Files
- `aura.py` - Complete CLI implementation (~150 lines)
  - `Colors` class: Terminal styling
  - Command handlers: `cmd_check()`, `cmd_pulse()`, `cmd_story()`, `cmd_eco()`, `cmd_fly()`
  - `main()`: argparse setup and entry point

## Next Steps for Feature Implementation
1. Replace placeholder messages with actual analysis logic
2. Add command-specific arguments for configurable scans
3. Implement actual analysis modules (security, metrics, docs, deps, perf)
4. Add configuration file support (`.aurarc`)
5. Implement verbose/quiet output modes
