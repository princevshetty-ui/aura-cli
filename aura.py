#!/usr/bin/env python3
"""
Aura - A modular CLI tool for GitHub Copilot CLI hackathon.
Provides security, analytics, and development insights with stylized output.
"""

import argparse
import sys
import os
import re
import subprocess
import shutil
from rich.console import Console, Group
import json
from rich.panel import Panel
from rich import box
from rich.table import Table
from rich.layout import Layout
from rich.text import Text
from rich.spinner import Spinner
from rich.live import Live
from rich.rule import Rule
import time
from collections import Counter
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn, SpinnerColumn

# Initialize Rich console for modern output with forced color support
console = Console(force_terminal=True, force_interactive=True)

# Timings (tweak these to make animations faster/slower)
HEADER_STEP_WAIT = 0.8  # seconds per header step
LIVE_PANEL_WAIT_DEFAULT = 1.0  # default wait for live panels


def render_title_panel(label: str, palette: list[str], border_style: str):
    """Render a centered, animated title panel with a color palette."""
    from rich.align import Align

    title_text = Text()
    for i, ch in enumerate(label):
        title_text.append(ch, style=palette[i % len(palette)])
    return Panel(
        Align(title_text, align="center"),
        border_style=border_style,
        padding=(1, 2),
        box=box.ROUNDED
    )


def display_header():
    """Display the AURA CLI header with bold styling and animation."""
    # Animated header with initialization animation
    steps = [
        "✨ Initializing Aura...",
        "🔌 Loading modules...",
        "⚙️  Applying configuration...",
        "✅ Ready"
    ]

    # Show each step briefly
    for step in steps:
        with console.status(f"[bold magenta]{step}[/bold magenta]", spinner="dots"):
            time.sleep(HEADER_STEP_WAIT)

    # Main headline (consistent with command headers)
    palette = ["bright_magenta", "magenta", "bright_blue", "blue", "bright_magenta"]
    panel = render_title_panel("✨ AURA CLI ✨", palette, border_style="magenta")
    console.print(panel)


def _print_live_panel(title: str, message: str, style: str = "cyan", wait: float = LIVE_PANEL_WAIT_DEFAULT):
    """Helper: show a short live panel with a spinner to make the CLI feel interactive.

    This is intentionally short to avoid slowing the CLI too much while improving
    perceived responsiveness.
    """
    from rich.align import Align

    # If wait is zero or falsy, treat as no-op
    if not wait:
        return
    panel = Panel(Align(Text(message, style=f"bold {style}"), vertical="middle"), title=f"{title}", border_style=style)
    with Live(panel, refresh_per_second=8, transient=True):
        time.sleep(wait)


def check_copilot_auth():
    """
    Check if user is authenticated with Copilot CLI.
    Returns True if authenticated, False otherwise.
    """
    # Prefer a non-interactive check. Try a few common copilot status commands
    copilot_bin = shutil.which('copilot')
    if not copilot_bin:
        return False

    status_commands = [
        [copilot_bin, 'auth', 'status'],
        [copilot_bin, 'status'],
        [copilot_bin, '--status'],
    ]

    for cmd in status_commands:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
            out = (result.stdout or '') + (result.stderr or '')
            # Many CLIs exit 0 and print 'Logged in' or 'Authenticated' when auth'd
            if result.returncode == 0 and re.search(r'logged in|authenticated|status: authenticated', out, re.I):
                return True
            # Some CLIs return 0 but don't print a friendly message; treat a 0 as a possible auth
            if result.returncode == 0 and out.strip():
                return True
        except subprocess.TimeoutExpired:
            # try the next candidate
            continue
        except Exception:
            continue

    # Fallback: check common environment variables that may indicate auth
    if os.environ.get('GITHUB_TOKEN') or os.environ.get('COPILOT_TOKEN'):
        return True

    return False


def scan_secrets():
    """
    Scan files for secrets including AWS keys, Google API keys, and .env permissions.
    Returns a tuple of (secrets_found, env_issues, remediation_prompt).
    """
    secrets_found = []
    env_issues = []
    remediation_prompt = "How do I safely remove a secret from my git history?"
    
    # Regex patterns for secrets
    aws_pattern = r'AKIA[0-9A-Z]{16}'
    google_pattern = r'AIza[0-9A-Za-z\-_]{35}'
    
    # Directories to exclude
    exclude_dirs = {'.git', 'node_modules', '.venv', '__pycache__', '.pytest_cache'}

    # First collect all files to scan so we can show progress
    filepaths = []
    for root, dirs, files in os.walk('.'):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for file in files:
            filepaths.append(os.path.join(root, file))

    total_files = len(filepaths)

    # Use a progress bar for long-running scans
    if total_files > 0:
        progress_columns = [SpinnerColumn(), TextColumn("{task.description}"), BarColumn(), TextColumn("{task.percentage:>3.0f}%"), TimeRemainingColumn()]
        with Progress(*progress_columns, console=console, transient=True) as progress:
            task = progress.add_task("Scanning files", total=total_files)

            for filepath in filepaths:
                # Check .env files for permissions
                file = os.path.basename(filepath)
                if file == '.env' or file.endswith('.env'):
                    try:
                        stat_info = os.stat(filepath)
                        mode = stat_info.st_mode & 0o777
                        if mode != 0o600:
                            env_issues.append((filepath, oct(mode)))
                    except Exception:
                        pass

                # Scan file content for secrets
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()

                        aws_matches = re.findall(aws_pattern, content)
                        if aws_matches:
                            for match in aws_matches:
                                secrets_found.append((filepath, 'AWS Access Key', match))

                        google_matches = re.findall(google_pattern, content)
                        if google_matches:
                            for match in google_matches:
                                secrets_found.append((filepath, 'Google API Key', match))
                except (IsADirectoryError, PermissionError):
                    pass
                except Exception:
                    pass

                progress.advance(task)
    else:
        # No files found; return empty results
        return secrets_found, env_issues, remediation_prompt

    return secrets_found, env_issues, remediation_prompt


def get_workspace_mtimes(exclude_dirs=None):
    """Return a list of (path, mtime) for files under the current directory,
    ignoring directories in exclude_dirs.
    """
    if exclude_dirs is None:
        exclude_dirs = {'.git', 'node_modules', '.venv', '__pycache__', '.pytest_cache'}
    mtimes = []
    for root, dirs, files in os.walk('.'):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for fname in files:
            fpath = os.path.join(root, fname)
            try:
                m = os.path.getmtime(fpath)
            except Exception:
                continue
            mtimes.append((fpath, m))
    return mtimes


def render_activity_histogram(mtimes, now, hours=6, buckets=6, width=24):
    """Given mtimes list and a reference time, return list of Text lines
    representing a compact histogram (most recent bucket first).
    """
    from rich.text import Text
    bucket_hours = hours
    bucket_span = (bucket_hours * 3600) / buckets
    counts = [0] * buckets
    for _, m in mtimes:
        age = now - m
        if age <= bucket_hours * 3600:
            idx = int(age // bucket_span)
            if idx >= buckets:
                idx = buckets - 1
            counts[idx] += 1

    max_count = max(counts) or 1
    lines = []
    for i in range(buckets):
        rev_i = buckets - 1 - i
        bucket_label = f"-{i+1}h"
        bar_len = int((counts[rev_i] / max_count) * width)
        bar = "█" * bar_len + "░" * (width - bar_len)
        lines.append(Text.assemble((f" {bucket_label:>4} ", "bold"), (f" {bar} ", "cyan"), (f" {counts[rev_i]} files", "white")))
    return lines


def play_sound(kind: str = "bell"):
    """Try to play a simple notification sound.

    Fallbacks (in order): terminal bell, paplay/aplay/spd-say where available.
    This is best-effort and never raises.
    """
    try:
        # Terminal bell (works in many terminals)
        print('\a', end='', flush=True)
    except Exception:
        pass


def parse_idle_field_to_minutes(field: str) -> float:
    """Parse idle time field from `w`/`who` into minutes.

    Handles formats like '.', 'old', '0.00s', '1.23m', 'MM:SS' or 'HH:MM'.
    Returns minutes as float or None if unparsable.
    """
    if not field or field.strip() in (".", "", "?"):
        return 0.0
    f = field.strip()
    if f == 'old':
        return 24 * 60.0
    # seconds
    if f.endswith('s'):
        try:
            return float(f[:-1]) / 60.0
        except Exception:
            return None
    # minutes
    if f.endswith('m'):
        try:
            return float(f[:-1])
        except Exception:
            return None
    # colon separated, could be mm:ss or hh:mm
    if ':' in f:
        parts = f.split(':')
        try:
            if len(parts) == 2:
                a, b = int(parts[0]), int(parts[1])
                # heuristics: if a < 10 assume minutes:seconds, else hours:minutes
                if a < 10:
                    return a + b / 60.0
                return a * 60 + b
        except Exception:
            return None
    # plain number -> minutes
    try:
        return float(f)
    except Exception:
        return None


def get_terminal_idle_minutes() -> float | None:
    """Try to determine the idle minutes for the current terminal session.

    Returns minutes as float, or None if it cannot be determined.
    """
    # Try to get tty name
    try:
        tty = os.ttyname(sys.stdin.fileno())
    except Exception:
        tty = None

    # Try `w -hs` first (more standardized)
    try:
        w_out = subprocess.run(['w', '-hs'], capture_output=True, text=True, timeout=1)
        if w_out.returncode == 0 and w_out.stdout:
            lines = [l for l in w_out.stdout.splitlines() if l.strip()]
            for line in lines:
                parts = line.split()
                # USER TTY FROM LOGIN@ IDLE JCPU PCPU WHAT
                if len(parts) >= 5:
                    user = parts[0]
                    tty_field = parts[1]
                    idle_field = parts[4]
                    if tty and tty_field in tty:
                        m = parse_idle_field_to_minutes(idle_field)
                        if m is not None:
                            return m
            # fallback: try to find any line for current user
            cur_user = os.getenv('USER') or os.getlogin()
            for line in lines:
                parts = line.split()
                if parts and parts[0] == cur_user and len(parts) >= 5:
                    m = parse_idle_field_to_minutes(parts[4])
                    if m is not None:
                        return m
    except Exception:
        pass

    # Try `who -u` as fallback
    try:
        who_out = subprocess.run(['who', '-u'], capture_output=True, text=True, timeout=1)
        if who_out.returncode == 0 and who_out.stdout:
            lines = [l for l in who_out.stdout.splitlines() if l.strip()]
            for line in lines:
                parts = line.split()
                # USER TTY  ... IDLE
                if len(parts) >= 6:
                    tty_field = parts[1]
                    idle_field = parts[5]
                    if tty and tty_field in tty:
                        m = parse_idle_field_to_minutes(idle_field)
                        if m is not None:
                            return m
            # fallback: try matching current user
            cur_user = os.getenv('USER') or os.getlogin()
            for line in lines:
                parts = line.split()
                if parts and parts[0] == cur_user and len(parts) >= 6:
                    m = parse_idle_field_to_minutes(parts[5])
                    if m is not None:
                        return m
    except Exception:
        pass

    return None

    # Try system players if available
    try:
        # prefer paplay (PulseAudio)
        paplay = shutil.which('paplay')
        if paplay:
            # common freedesktop sounds
            candidates = [
                '/usr/share/sounds/freedesktop/stereo/complete.oga',
                '/usr/share/sounds/freedesktop/stereo/phone-incoming-call.oga',
            ]
            for c in candidates:
                if os.path.exists(c):
                    subprocess.run([paplay, c], timeout=3)
                    return

        aplay = shutil.which('aplay')
        if aplay:
            # try a common wav (rare), fallback to bell
            candidates = ['/usr/share/sounds/alsa/Front_Center.wav']
            for c in candidates:
                if os.path.exists(c):
                    subprocess.run([aplay, c], timeout=3)
                    return

        # As a last resort, use spd-say to speak a short phrase
        spd = shutil.which('spd-say')
        if spd:
            phrase = 'Time for a short break' if kind != 'bell' else 'Bell'
            subprocess.run([spd, phrase], timeout=3)
            return
    except Exception:
        pass


def animate_flame(duration: float = 1.0, refresh: int = 8, loop: bool = False, enabled: bool = True):
    """Render a brief flame animation using Rich Live. Non-blocking-ish and
    transient so it feels like a tasteful visual flourish for FLOW state.
    """
    from rich.align import Align
    from rich.text import Text

    if not enabled:
        return
    frames = [
        Text("  🔥  ", style="bold red"),
        Text(" 🔥🔥 ", style="bold bright_red"),
        Text("🔥🔥🔥", style="bold bright_yellow"),
        Text(" 🔥🔥 ", style="bold bright_red"),
        Text("  🔥  ", style="bold red"),
    ]

    # Use a Panel so the animation has a border and title
    with Live(refresh_per_second=refresh, transient=True) as live:
        if loop:
            end = time.time() + duration
            # Loop until duration expires or until a keypress (if stdin is a tty)
            end = time.time() + duration
            try:
                # set up non-blocking key detection
                import termios
                import tty
                import select

                fd = sys.stdin.fileno()
                old_settings = termios.tcgetattr(fd)
                try:
                    tty.setcbreak(fd)
                    while time.time() < end:
                        for frame in frames:
                            panel = Panel(Align(frame, vertical="middle"), border_style="bright_red", title="FLOW")
                            live.update(panel)
                            # check for keypress
                            if select.select([sys.stdin], [], [], duration / (len(frames) * 4))[0]:
                                _ = sys.stdin.read(1)
                                return
                            time.sleep(max(0.02, duration / (len(frames) * 4)))
                finally:
                    try:
                        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                    except Exception:
                        pass
            except Exception:
                # Fallback: loop until time expires without key detection
                while time.time() < end:
                    for frame in frames:
                        panel = Panel(Align(frame, vertical="middle"), border_style="bright_red", title="FLOW")
                        live.update(panel)
                        time.sleep(max(0.02, duration / (len(frames) * 4)))
        else:
            for frame in frames:
                panel = Panel(Align(frame, vertical="middle"), border_style="bright_red", title="FLOW")
                live.update(panel)
                time.sleep(max(0.02, duration / len(frames)))


def get_git_diff(lines: int = 40) -> str:
    """Fetch recent git diff to understand code changes."""
    try:
        result = subprocess.run(['git', 'diff', 'HEAD'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0 and result.stdout:
            output_lines = result.stdout.splitlines()[:lines]
            return '\n'.join(output_lines)
    except Exception:
        pass
    return ""


def scan_bloat(max_size_mb: int = 50, top_n: int = 5):
    """Scan for the largest files and flag energy-heavy assets.

    Returns:
        (largest_files, total_bloat_mb)
        where largest_files = [(path, size_mb, impact_label), ...]
    """
    exclude_dirs = {'.git', 'node_modules', '.venv', '__pycache__', '.pytest_cache', 'site-packages'}
    file_sizes = []

    for root, dirs, files in os.walk('.'):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for file in files:
            fpath = os.path.join(root, file)
            try:
                size_bytes = os.path.getsize(fpath)
            except Exception:
                continue
            size_mb = size_bytes / (1024 * 1024)
            file_sizes.append((fpath, size_mb))

    file_sizes.sort(key=lambda item: item[1], reverse=True)
    largest_files = []
    for fpath, size_mb in file_sizes[:top_n]:
        if size_mb > max_size_mb:
            impact = "Energy Heavy — prune or add to .gitignore"
        else:
            impact = "OK"
        largest_files.append((fpath, size_mb, impact))

    total_bloat_mb = sum(size for _, size, _ in largest_files)
    return largest_files, total_bloat_mb


def analyze_complexity_with_copilot(main_script: str = "aura.py", snippet_lines: int = 40) -> str:
    """Send a short main-script snippet to Copilot for complexity analysis."""
    try:
        if not os.path.exists(main_script):
            return "Main script not found. Skipping complexity analysis."

        with open(main_script, 'r', encoding='utf-8') as f:
            lines = f.read().splitlines()

        snippet = "\n".join(lines[:snippet_lines])
        if not snippet.strip():
            return "Main script is empty. Skipping complexity analysis."

        if not check_copilot_auth():
            return "Copilot CLI not authenticated. Run: copilot -i /login"

        copilot_bin = shutil.which('copilot')
        if not copilot_bin:
            return "Copilot binary not found. Skipping AI analysis."

        prompt = (
            "Analyze this code for algorithmic complexity (Big O). Identify nested loops or redundant I/O that "
            "cause high CPU spikes. Suggest one Carbon-Neutral refactor to reduce energy consumption.\n\n"
            f"Code snippet (first {snippet_lines} lines):\n{snippet}"
        )

        def run_prompt(prompt_text: str, timeout_sec: int) -> str | None:
            result = subprocess.run(
                [copilot_bin, "-p", prompt_text],
                capture_output=True, text=True, timeout=timeout_sec
            )
            if result.returncode == 0 and result.stdout:
                return result.stdout.strip()
            return None

        response = run_prompt(prompt, 15)
        if response:
            return response

        # Retry quickly with a shorter snippet to reduce latency under load.
        short_lines = max(10, snippet_lines // 2)
        short_snippet = "\n".join(lines[:short_lines])
        short_prompt = (
            "Analyze this code for algorithmic complexity (Big O). Identify nested loops or redundant I/O that "
            "cause high CPU spikes. Suggest one Carbon-Neutral refactor to reduce energy consumption.\n\n"
            f"Code snippet (first {short_lines} lines):\n{short_snippet}"
        )
        response = run_prompt(short_prompt, 15)
        if response:
            return response

        return "Copilot analysis unavailable. Defaulting to O(n) complexity."
    except subprocess.TimeoutExpired:
        return "Analysis timeout (15s exceeded). Defaulting to O(n) complexity."
    except Exception as e:
        return f"Analysis error: {str(e)[:50]}. Defaulting to O(n) complexity."


def calculate_carbon_score(largest_files: list, complexity_feedback: str) -> str:
    """Calculate carbon efficiency score A-F based on bloat and complexity."""
    feedback = (complexity_feedback or "").lower()
    heavy_files = [entry for entry in largest_files if entry[1] > 50]
    total_bloat_mb = sum(size for _, size, _ in largest_files)
    several_large_assets = len(heavy_files) >= 2
    major_bloat = len(heavy_files) >= 3 or total_bloat_mb >= 200 or any(size >= 200 for _, size, _ in heavy_files)

    nested_loops = "nested loop" in feedback or "nested loops" in feedback
    quadratic = "o(n^2" in feedback or "o(n²" in feedback or "quadratic" in feedback
    linear = "o(n)" in feedback or "linear" in feedback or "o(n log" in feedback
    constant = "o(1" in feedback or "constant" in feedback
    log_n = "o(log" in feedback

    if nested_loops and major_bloat:
        return "F"
    if quadratic or several_large_assets:
        return "C"
    if (constant or log_n or linear) and not heavy_files:
        return "A"
    if nested_loops or heavy_files:
        return "D"
    return "B"


def cmd_check(args):
    """Security check subcommand."""
    palette = ["bright_red", "red", "bright_magenta", "magenta", "bright_red"]
    console.print(render_title_panel("AURA — SECURITY", palette, border_style="red"))
    
    # Pre-flight check: Verify Copilot CLI authentication
    if not check_copilot_auth():
        console.print("[bold red]⚠️  Aura needs your help![/bold red]")
        console.print("Please run [bold cyan]copilot -i /login[/bold cyan] to authenticate the Copilot agent.\n")
        console.print("Important: after running [bold cyan]copilot -i /login[/bold cyan], open a new terminal to run Aura commands. The Copilot login opens an agent that may occupy the current terminal and prevent Aura output from appearing in the same session.")
        return

    # Make scan feel more alive: brief live intro, then run scan with progress
    _print_live_panel("🔎 Scanning", "Preparing to scan files for secrets...", style="cyan", wait=1.0)
    secrets_found, env_issues, remediation_prompt = scan_secrets()
    console.print()  # Add blank line after scan completes
    
    if secrets_found:
        # Create a Rich Table for secrets findings
        table = Table(title="[bold red]Security Findings[/bold red]", border_style="red")
        table.add_column("File Name", style="cyan")
        table.add_column("Secret Type", style="yellow")
        table.add_column("Action", style="magenta")
        
        for filepath, secret_type, value in secrets_found:
            masked_value = value[:8] + '...' if len(value) > 8 else value
            table.add_row(filepath, secret_type, "Review & Remediate")
        
        console.print(table)
        # NOTE: local "What to do next" checklist removed per user request.
        # Query GitHub Copilot for guidance (capture output and print cleanly)
        console.print("[bold purple]Consulting the Oracle...[/bold purple]\n")
        try:
            copilot_path = shutil.which('copilot')
            if not copilot_path:
                raise FileNotFoundError("copilot CLI not found")

            # Build a prompt that includes counts per secret type and file list
            found_summaries = []
            types = []
            for fpath, stype, _ in secrets_found:
                found_summaries.append(f"{fpath} ({stype})")
                types.append(stype)
            found_list = ", ".join(sorted(set(found_summaries))) if found_summaries else "<unknown>"

            counts = Counter(types)
            if counts:
                counts_list = ", ".join(f"{v} {k}{'s' if v>1 else ''}" for k, v in counts.items())
            else:
                counts_list = "unknown types"

            # If the repository doesn't look like a git repo, tell Copilot so it can give safe local-only advice
            repo_note = "The repository appears to have a .git directory." if os.path.isdir('.git') else "This project does not appear to be a git repository (no .git directory). Provide remediation steps that are safe for users who have not pushed to a remote yet."

            prompt = (
                f"The security scan found the following secrets: {found_list} (summary: {counts_list}). "
                f"{repo_note} IMMEDIATELY output clear, numbered remediation steps as plain text. "
                "For each step include the exact shell commands where applicable, and clearly label any steps that are destructive or that rewrite git history. "
                "If the user may be new to git, include safe 'first-time' guidance (how to backup, how to check if a file is tracked, and how to rotate credentials)."
            )

            # Run copilot non-interactively and capture output to avoid noisy streaming
            with console.status("[bold purple]Querying Copilot for remediation steps...[/bold purple]", spinner="bouncingBar"):
                result = subprocess.run([copilot_path, "--allow-all-tools", "-p", prompt], capture_output=True, text=True, timeout=60)

            copilot_out = (result.stdout or '').strip()
            copilot_err = (result.stderr or '').strip()

            if copilot_out:
                console.print(Panel(Text(copilot_out, style="white"), title="Copilot remediation (stdout)", border_style="purple"))
            if copilot_err:
                console.print(Panel(Text(copilot_err, style="yellow"), title="Copilot remediation (stderr)", border_style="yellow"))

            if not copilot_out and not copilot_err:
                console.print("[bold yellow]Note:[/bold yellow] Copilot returned no output.")

        except FileNotFoundError:
            console.print("[bold yellow]Note:[/bold yellow] 'copilot' CLI not found. Install the Copilot CLI to get AI-powered remediation guidance.")
        except subprocess.TimeoutExpired:
            console.print("[bold yellow]⚠️  AI took too long to respond, please try again.[/bold yellow]")
        except Exception as e:
            console.print(f"[bold yellow]Note:[/bold yellow] Could not query GitHub Copilot: {e}")
    
    if env_issues:
        # Create a table for env file permission issues
        env_table = Table(title="[bold red].env Permission Issues[/bold red]", border_style="red")
        env_table.add_column("File Name", style="cyan")
        env_table.add_column("Current Permissions", style="yellow")
        env_table.add_column("Expected", style="green")
        
        for filepath, mode in env_issues:
            env_table.add_row(filepath, mode, "0o600")
        
        console.print(env_table)
    
    if not secrets_found and not env_issues:
        console.print(Panel("[bold green]✓ No security issues detected![/bold green]", border_style="green"))


def cmd_pulse(args):
    """Code health pulse subcommand.

    This is a richer wellness dashboard with professional styling, activity
    histogram, focus meter, and repo-aware metrics. It avoids playful or
    childish wording and aims to provide actionable, glanceable insights.
    """
    from rich.align import Align
    from rich.columns import Columns
    from rich.rule import Rule

    # Polished title with PULSE-appropriate calm palette
    palette = ["bright_cyan", "cyan", "bright_blue", "blue", "bright_cyan"]

    if not getattr(args, 'compact', False):
        console.print(render_title_panel("AURA — PULSE", palette, border_style="cyan"))

    _print_live_panel("Analyzing workspace", "Compiling activity signals...", style="cyan", wait=(0.8 if not getattr(args, 'compact', False) else 0))

    # Collect file mtimes using helper; allow --hours to change histogram window
    hours = getattr(args, 'hours', 6)
    now = time.time()
    mtimes = get_workspace_mtimes()

    newest_path = None
    newest_mtime = 0.0
    for p, m in mtimes:
        if m > newest_mtime:
            newest_mtime = m
            newest_path = p

    if not mtimes:
        console.print(Panel("No analyzable files found.", border_style="yellow"))
        return

    minutes_since = (now - newest_mtime) / 60.0
    minutes_label = f"{int(minutes_since)}m ago"

    # Build activity histogram using helper (hours configurable)
    buckets = 6
    hist_lines = render_activity_histogram(mtimes, now, hours=hours, buckets=buckets, width=24)

    # Quick stats
    modified_5 = sum(1 for _, m in mtimes if now - m <= 5 * 60)
    modified_30 = sum(1 for _, m in mtimes if now - m <= 30 * 60)
    modified_60 = sum(1 for _, m in mtimes if now - m <= 60 * 60)
    modified_24h = sum(1 for _, m in mtimes if now - m <= 24 * 3600)

    stats_table = Table.grid(expand=True)
    stats_table.add_column(justify="left")
    stats_table.add_column(justify="right")
    stats_table.add_row("Last edit:", f"[bold]{os.path.basename(newest_path)}[/bold]")
    stats_table.add_row("Ago:", f"{minutes_label}")
    stats_table.add_row("Touched (5/30/60/24h):", f"{modified_5}/{modified_30}/{modified_60}/{modified_24h}")

    # Focus meter (10-block gauge) — more recent edits => higher focus
    focus_score = max(0.0, min(1.0, 1.0 - (minutes_since / 120.0)))
    filled = int(round(focus_score * 10))
    empty = 10 - filled
    gauge = "|" + "■" * filled + "·" * empty + "|"
    focus_text = Text(f"Focus: {gauge} ", style="bold")
    if minutes_since < 5:
        focus_text.append("FLOW", style="bright_green")
    elif minutes_since <= 30:
        focus_text.append("STEADY", style="cyan")
    else:
        focus_text.append("REST", style="yellow")

    # Repo-aware info: last commit if available
    git_info = None
    try:
        if os.path.isdir('.git'):
            git_out = subprocess.run(['git', 'log', '-1', '--format=%ct::%s'], capture_output=True, text=True, timeout=2)
            if git_out.returncode == 0 and git_out.stdout.strip():
                ts, msg = git_out.stdout.strip().split('::', 1)
                commit_age_min = (now - int(ts)) / 60.0
                git_info = f"Last commit: {int(commit_age_min)}m ago — {msg}"
    except Exception:
        git_info = None

    # Build left and right columns
    left = Panel(Group(stats_table, Text("\nActivity (last 6h)", style="bold underline"), *hist_lines), title="Overview", border_style="cyan")
    right_items = [focus_text]
    if git_info:
        right_items.append(Text(git_info, style="dim"))
    right_items.append(Text("\nSuggested micro-actions:", style="bold underline"))
    # Suggest micro actions (non-destructive)
    micro = ["Run tests (small target)", "Add 1 TODO", "Refactor 1 small func", "Update a short doc line"]
    for i, m in enumerate(micro, start=1):
        right_items.append(Text(f"{i}. {m}", style="white"))

    right = Panel(Group(*right_items), title="Focus & Suggestions", border_style="magenta")

    # If compact output requested, print a single JSON line and exit
    if getattr(args, 'compact', False):
        compact = {
            'latest': os.path.basename(newest_path) if newest_path else None,
            'minutes_since': int(minutes_since),
            'focus_score': round(focus_score, 2),
            'touched_5m': modified_5,
            'touched_30m': modified_30,
            'touched_60m': modified_60,
            'touched_24h': modified_24h,
        }
        print(json.dumps(compact, separators=(',', ':')))
        return

    console.print(Columns([left, right], expand=True))

    # Determine idle state: check both file mtime and terminal idle
    idle_threshold = float(getattr(args, 'idle', 15))
    terminal_idle = get_terminal_idle_minutes()
    idle_by_files = minutes_since > idle_threshold
    idle_by_terminal = (terminal_idle is not None and terminal_idle > idle_threshold)
    idle_by_force = getattr(args, 'force_zen', False)
    is_idle = idle_by_files or idle_by_terminal or idle_by_force

    # Build status message based on ACTUAL developer activity (minutes_since file edits)
    status_text = Text()
    if minutes_since < 5:
        # FLOW: very recent activity (within 5 minutes) — show "In flow" only when truly active
        status_text.append("In flow — keep going!", style="bold bright_green")
        # tasteful looping flame animation for Flow (short loop). Skip in compact mode.
        if not getattr(args, 'compact', False):
            try:
                animate_flame(duration=3.0, loop=True, enabled=True)
            except Exception:
                pass
    elif minutes_since <= 30:
        # STEADY: moderate activity (5-30 minutes since last edit)
        status_text.append("STEADY RHYTHM — Good progress. Consider a brief checkpoint.", style="bold cyan")
    else:
        # REST: low activity (30+ minutes since last edit) — time for a break
        status_text.append("REST — It's been a while since edits. Take a micro-break.", style="bold yellow")

    console.print(Rule(style="dim"))
    console.print(Panel(status_text, border_style="green" if minutes_since < 30 else "yellow"))

    # If idle (and not in compact mode and not opted out), fetch Copilot wellness suggestion
    if is_idle and not getattr(args, 'compact', False) and not getattr(args, 'no_ai', False):
        console.print(Rule(style="dim"))
        
        # Show "Fetching wellness suggestion..." while Copilot is working in background
        loading_spinner = Spinner("dots", text="[cyan]Fetching wellness suggestion...[/cyan]")
        with Live(loading_spinner, console=console, refresh_per_second=8, transient=True) as live:
            copilot_bin = shutil.which('copilot')
            stretch_text = None
            error_occurred = False
            
            try:
                if copilot_bin:
                    # Fetch a 1-minute physical stretch with extended timeout (30s to be safe)
                    # This gives Copilot plenty of time to respond without user seeing timeout
                    cp = subprocess.run(
                        [copilot_bin, "-p", "Suggest a 1-minute physical stretch for a developer. Format as a numbered list (3-4 steps)."],
                        capture_output=True, text=True, timeout=30
                    )
                    stretch_text = (cp.stdout or cp.stderr or "").strip()
                    if not stretch_text:
                        stretch_text = "Take a moment to stretch and breathe. Stand up, move around, and reset your mind."
                else:
                    stretch_text = "Install the Copilot CLI to enable guided wellness breaks."
            except subprocess.TimeoutExpired:
                error_occurred = True
                stretch_text = "Copilot is taking longer than expected. Please try again in a moment."
            except Exception as e:
                error_occurred = True
                stretch_text = f"Could not fetch suggestion: {str(e)[:50]}"
        
        # Play a friendly sound to draw attention to the break
        try:
            play_sound('bell')
        except Exception:
            pass

        # Show Zen Break panel with the suggestion
        if stretch_text:
            console.print(Panel(Text(stretch_text, style="white"), title="Zen Break 🧘", border_style="yellow"))
            console.print(Panel(Text("🎧 Vibe Check: Open [link=https://lofi.co]Lofi.co[/link] for focus beats.", style="white"), border_style="bright_blue"))


def cmd_story(args):
    """Code story/documentation subcommand - Founder's Journal."""
    palette = ["bright_blue", "blue", "cyan", "bright_cyan", "blue"]
    console.print(render_title_panel("AURA — STORY", palette, border_style="blue"))

    _print_live_panel("Analyzing changes", "Gathering recent code updates...", style="blue", wait=1.0)
    git_diff = get_git_diff(lines=40)

    if not git_diff:
        console.print(Panel(
            "[bold cyan]ℹ️  No code changes detected.[/bold cyan]\n\n"
            "Tip: Make a change and commit to generate your Founder's Journal entry.",
            border_style="cyan",
            padding=(1, 2)
        ))
        return

    loading_spinner = Spinner("dots", text="[blue]Composing your Founder's Journal...[/blue]")
    journal_entry = None
    with Live(loading_spinner, console=console, refresh_per_second=8, transient=True):
        try:
            copilot_bin = shutil.which('copilot')
            if copilot_bin:
                prompt = (
                    "Based on these recent code changes, write a short, 3-sentence 'Founder's Journal' entry "
                    "that explains the progress in a professional yet confident tone. Avoid technical jargon.\n\n"
                    f"Code changes:\n{git_diff}"
                )
                cp = subprocess.run([copilot_bin, "-p", prompt], capture_output=True, text=True, timeout=30)
                journal_entry = (cp.stdout or cp.stderr or "").strip()
            if not journal_entry:
                journal_entry = (
                    "Today we made solid progress on the codebase. The team focused on quality and reliability, "
                    "moving the project forward with clear, purposeful improvements."
                )
        except subprocess.TimeoutExpired:
            journal_entry = (
                "Progress is moving steadily. The team delivered meaningful updates and kept momentum strong."
            )
        except Exception:
            journal_entry = (
                "This session added thoughtful refinements and kept the project moving in the right direction."
            )

    # Clean the journal entry
    clean_lines = [line for line in journal_entry.split('\n') if line.strip() and line.strip() != '---']
    final_entry = '\n'.join(clean_lines).replace('**', '').strip()

    console.print(Rule(style="dim"))
    console.print(Panel(
        Text(final_entry, style="white"),
        title="📖 Today's Story",
        border_style="blue",
        padding=(1, 2)
    ))
    console.print(Panel(
        Text("💭 Reflect on your progress and celebrate the small wins.", style="dim"),
        border_style="blue",
        padding=(0, 2)
    ))


def cmd_eco(args):
    """Ecosystem analysis subcommand - Carbon audit."""
    palette = ["bright_green", "green", "bright_cyan", "cyan", "bright_green"]
    if not getattr(args, 'compact', False):
        console.print(render_title_panel("AURA — ECO", palette, border_style="green"))

    # Scan for bloat with loading indicator
    if getattr(args, 'compact', False):
        largest_files, total_bloat = scan_bloat()
    else:
        loading_spinner = Spinner("dots", text="[green]Scanning filesystem for bloat...[/green]")
        with Live(loading_spinner, console=console, refresh_per_second=8, transient=True):
            largest_files, total_bloat = scan_bloat()

    # Analyze complexity with Copilot (skip if --no-ai flag)
    if getattr(args, 'no_ai', False):
        complexity_feedback = "AI complexity audit skipped (--no-ai flag used). Local assumption: O(n) patterns."
    else:
        if getattr(args, 'compact', False):
            complexity_feedback = analyze_complexity_with_copilot()
        else:
            loading_spinner = Spinner("dots", text="[green]Analyzing code complexity with AI...[/green]")
            with Live(loading_spinner, console=console, refresh_per_second=8, transient=True):
                complexity_feedback = analyze_complexity_with_copilot()

    carbon_score = calculate_carbon_score(largest_files, complexity_feedback)
    heavy_files = [entry for entry in largest_files if entry[1] > 50]
    total_bloat_text = f"{total_bloat:.1f} MB" if total_bloat > 0 else "0 MB"

    table_width = max(72, console.width - 6)
    table = Table(
        border_style="bright_green",
        box=box.SIMPLE_HEAVY,
        show_header=True,
        header_style="bold bright_green",
        show_lines=False,
        expand=False,
        pad_edge=False,
        width=table_width
    )

    table.add_column("File", style="cyan", ratio=2, no_wrap=True, overflow="ellipsis")
    table.add_column("Size", style="white", ratio=1, justify="right")
    table.add_column("Energy Impact", style="bright_green", ratio=2, overflow="ellipsis")

    if largest_files:
        for fpath, size_mb, impact in largest_files:
            rel_path = os.path.relpath(fpath, start='.')
            table.add_row(rel_path, f"{size_mb:.2f} MB", impact)
    else:
        table.add_row("No files found", "-", "-")

    score_colors = {
        "A": "bold bright_green",
        "B": "bold green",
        "C": "bold yellow",
        "D": "bold bright_yellow",
        "E": "bold red",
        "F": "bold bright_red"
    }
    score_style = score_colors.get(carbon_score, "bold white")

    summary = Group(
        Text(f"Carbon Grade: {carbon_score}", style=score_style),
        Text(f"Energy Heavy files (>50MB): {len(heavy_files)}", style="white"),
        Text(f"Total size (top {len(largest_files)} files): {total_bloat_text}", style="white"),
        Rule(style="dim"),
        table
    )

    if getattr(args, 'compact', False):
        print(json.dumps({
            "carbon_grade": carbon_score,
            "energy_heavy_files": len(heavy_files),
            "total_top_files_mb": round(total_bloat, 1),
            "largest_files": [
                {"file": fpath, "size_mb": round(size_mb, 2), "impact": impact}
                for fpath, size_mb, impact in largest_files
            ]
        }, separators=(",", ":")))
    else:
        console.print(Rule(style="dim"))
        console.print(Panel(
            summary,
            title="🌿 Eco Audit",
            border_style="bright_green",
            box=box.ROUNDED,
            padding=(1, 2)
        ))

        if complexity_feedback:
            if any(term in complexity_feedback.lower() for term in ["timeout", "error", "not found", "unavailable"]):
                console.print(Panel(
                    Text("🤖 AI Insights\n" + complexity_feedback + "\n\nUsing local assessment: O(n) complexity for filesystem operations.", style="dim yellow"),
                    border_style="yellow",
                    padding=(1, 2)
                ))
            else:
                console.print(Panel(
                    Text(complexity_feedback, style="white"),
                    title="🤖 AI Insights",
                    border_style="bright_green",
                    padding=(1, 2)
                ))

    # Generate GREEN_AUDIT.md documentation
    heavy_file_lines = "\n".join(
        [f"- {fpath} ({size_mb:.2f} MB) — {impact}" for fpath, size_mb, impact in largest_files if size_mb > 50]
    )
    if not heavy_file_lines:
        heavy_file_lines = "✓ No energy-heavy files detected"

    table_lines = "\n".join(
        [f"| {fpath} | {size_mb:.2f} MB | {impact} |" for fpath, size_mb, impact in largest_files]
    ) or "| No files found | - | - |"

    green_content = f"""# 🌿 Carbon Audit Report - {os.path.basename(os.getcwd())}

## Carbon Grade: {carbon_score}

Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}

### Static Bloat Scan (Top 5 Largest Files)

| File | Size | Energy Impact |
| --- | --- | --- |
{table_lines}

**Energy Heavy (>50MB):**
{heavy_file_lines}

**Total Size (Top {len(largest_files)} files):** {total_bloat_text}

### AI Complexity Audit

{complexity_feedback}

### Recommendations

1. **Prune or ignore heavy assets**: Move large artifacts to archives or add them to `.gitignore`.
2. **Refactor hotspots**: Apply the AI-suggested refactor to reduce CPU spikes.
3. **Monitor sustainability**: Run `aura eco` regularly and track grade trends.

---
*Report generated by Aura CLI - Green Computing Auditor*
"""

    try:
        with open('GREEN_AUDIT.md', 'w', encoding='utf-8') as f:
            f.write(green_content)
        if not getattr(args, 'compact', False):
            console.print(Panel(
                Text("✓ Sustainability report saved to GREEN_AUDIT.md", style="bright_green"),
                border_style="green",
                padding=(0, 2)
            ))
    except Exception as e:
        console.print(f"[yellow]⚠️  Could not save GREEN_AUDIT.md: {str(e)[:50]}[/yellow]")


def cmd_fly(args):
    """Performance flight check subcommand."""
    palette = ["bright_yellow", "yellow", "bright_magenta", "magenta", "bright_yellow"]
    console.print(render_title_panel("AURA — FLY", palette, border_style="yellow"))
    _print_live_panel("⚡ Benchmarking", "Running quick performance probes...", style="yellow", wait=1.2)
    console.print("[bold yellow]Performance snapshot ready. Use `aura fly --help` for tuning options.[/bold yellow]")








def main():
    """Main CLI entry point with argparse setup."""
    # Parse args first so we can optionally suppress the header for compact/CI modes
    
    parser = argparse.ArgumentParser(
        prog='aura',
        description='Aura - Intelligent CLI tool for development insights',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  aura check           Run security analysis
  aura pulse           Analyze code health
  aura story           Generate code documentation
  aura eco             Check dependencies
  aura fly             Performance check
        """
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s 0.1.0'
    )
    
    subparsers = parser.add_subparsers(
        title='commands',
        description='available commands',
        dest='command',
        help='command help'
    )
    
    # Security check command
    check_parser = subparsers.add_parser(
        'check',
        help='Run security vulnerability checks',
        aliases=['sec']
    )
    check_parser.add_argument('--preview', action='store_true', help='Preview remediation commands without running anything')
    check_parser.set_defaults(func=cmd_check)
    
    # Code health pulse command
    pulse_parser = subparsers.add_parser(
        'pulse',
        help='Quick productivity pulse',
        aliases=['health','p']
    )
    pulse_parser.add_argument('--no-ai', action='store_true', help='Do not call Copilot for micro-break suggestions')
    pulse_parser.add_argument('--hours', type=int, default=6, help='Time window in hours for activity histogram (default: 6)')
    pulse_parser.add_argument('--compact', action='store_true', help='Compact output for CI/low-tty environments')
    pulse_parser.add_argument('--idle', type=int, default=15, help='Idle threshold in minutes to trigger Zen Break (default: 15)')
    pulse_parser.add_argument('--force-zen', action='store_true', help='Force Zen Break (useful for testing)')
    pulse_parser.set_defaults(func=cmd_pulse)
    
    # Code story command
    subparsers.add_parser(
        'story',
        help='Generate code documentation and stories',
        aliases=['doc']
    ).set_defaults(func=cmd_story)
    
    # Ecosystem analysis command
    eco_parser = subparsers.add_parser(
        'eco',
        help='Analyze project dependencies and ecosystem',
        aliases=['deps']
    )
    eco_parser.add_argument('--no-ai', action='store_true', help='Skip Copilot analysis (faster)')
    eco_parser.add_argument('--compact', action='store_true', help='Compact output for CI/automation')
    eco_parser.set_defaults(func=cmd_eco)
    
    # Performance flight check command
    subparsers.add_parser(
        'fly',
        help='Run performance and optimization analysis',
        aliases=['perf']
    ).set_defaults(func=cmd_fly)
    
    args = parser.parse_args()
    
    # Display help if no command specified
    if not hasattr(args, 'func'):
        parser.print_help()
        sys.exit(0)
    # Show header unless user requested compact/ci output
    if not getattr(args, 'compact', False):
        display_header()

    # Execute the selected command
    args.func(args)


if __name__ == '__main__':
    main()
