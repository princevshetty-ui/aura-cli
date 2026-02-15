#!/usr/bin/env python3
"""
Aura - A modular CLI tool for GitHub Copilot CLI.
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
from rich.markdown import Markdown
import time
from collections import Counter
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn, SpinnerColumn

# Initialize Rich console for modern output with forced color support
console = Console(force_terminal=True, force_interactive=True)

# Timings (tweak these to make animations faster/slower)
HEADER_STEP_WAIT = 0.5  # seconds per header step (faster)
LIVE_PANEL_WAIT_DEFAULT = 0.8  # default wait for live panels

# Module Color Themes - Each module has its own distinct vibrant palette
MODULE_THEMES = {
    'header': {
        'primary': 'bright_white',
        'secondary': 'bright_cyan',
        'border': 'bright_cyan',
        'accent': 'cyan'
    },
    'check': {  # Security - Crimson/Orange (alert, warning)
        'primary': 'bright_red',
        'secondary': 'red',
        'border': 'bright_red',
        'accent': 'yellow',
        'text': 'bright_yellow'
    },
    'pulse': {  # Health - Magenta/Pink (energy, vitality)
        'primary': 'bright_magenta',
        'secondary': 'magenta',
        'border': 'bright_magenta',
        'accent': 'bright_cyan',
        'text': 'bright_cyan'
    },
    'story': {  # Documentation - Blue/Indigo (creativity, wisdom)
        'primary': 'bright_blue',
        'secondary': 'blue',
        'border': 'bright_blue',
        'accent': 'bright_white',
        'text': 'bright_white'
    },
    'eco': {  # Green Computing - Green/Teal (sustainability)
        'primary': 'bright_green',
        'secondary': 'green',
        'border': 'bright_green',
        'accent': 'cyan',
        'text': 'cyan'
    },
    'fly': {  # Onboarding - Yellow/Gold (launch, energy)
        'primary': 'bright_yellow',
        'secondary': 'yellow',
        'border': 'bright_yellow',
        'accent': 'bright_white',
        'text': 'bright_white'
    }
}


def get_theme(module: str) -> dict:
    """Get the color theme for a module."""
    return MODULE_THEMES.get(module, MODULE_THEMES['header'])


def render_title_panel(label: str, module: str = 'header'):
    """Render a centered title panel with module-specific colors."""
    from rich.align import Align
    
    theme = get_theme(module)
    title_text = Text(label, style=f"bold {theme['primary']}")
    
    return Panel(
        Align(title_text, align="center"),
        border_style=theme['border'],
        padding=(1, 2),
        box=box.DOUBLE
    )


def display_header():
    """Display the AURA CLI header with vibrant styling and smooth animation."""
    theme = get_theme('header')
    
    # Quick animated header with initialization
    steps = [
        ("◈", "Initializing Aura"),
        ("◈◈", "Loading modules"),
        ("◈◈◈", "Ready to assist")
    ]

    for dots, step in steps:
        with console.status(f"[bold {theme['secondary']}]{dots} {step}...[/bold {theme['secondary']}]", spinner="dots"):
            time.sleep(HEADER_STEP_WAIT)

    # Main headline with consistent vibrant color
    console.print(render_title_panel("◆ AURA CLI ◆", 'header'))


def render_ai_output(content: str, title: str, module: str):
    """Render AI output consistently across all modules with proper formatting."""
    theme = get_theme(module)
    
    # Check if it's an error/fallback message
    error_keywords = ["timeout", "error", "not found", "unavailable", "not authenticated", "skipped"]
    is_error = any(keyword in content.lower() for keyword in error_keywords)
    
    if is_error:
        console.print(Panel(
            Text(f"{title}\n{content}", style=f"dim {theme['accent']}"),
            border_style=theme['border'],
            padding=(1, 2)
        ))
    else:
        # Render as Markdown WITHOUT style override - let Rich format headers, bold, code naturally
        md = Markdown(content)
        console.print(Panel(
            md,
            title=title,
            border_style=theme['border'],
            box=box.ROUNDED,
            padding=(1, 2),
            width=min(100, console.width - 2)
        ))


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
    # Smart exclusion: ignore system/cache directories
    exclude_dirs = {'.git', 'node_modules', '.venv', '__pycache__', '.pytest_cache', 
                    'site-packages', '.mypy_cache', '.tox', 'dist', 'build', 'eggs', '.eggs'}
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


def get_previous_carbon_grade() -> tuple[str | None, str | None]:
    """Read the previous carbon grade from GREEN_AUDIT.md for progress tracking.
    
    Returns:
        (previous_grade, previous_timestamp) or (None, None) if not found
    """
    try:
        if not os.path.exists('GREEN_AUDIT.md'):
            return None, None
        
        with open('GREEN_AUDIT.md', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find the most recent audit entry
        import re
        # Look for pattern: ### Audit - YYYY-MM-DD HH:MM:SS followed by Carbon Grade: X
        audit_pattern = r'### Audit - (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*?Carbon Grade: ([A-F])'
        matches = re.findall(audit_pattern, content, re.DOTALL)
        
        if matches:
            # Return the most recent (last) entry
            return matches[-1][1], matches[-1][0]
        
        # Fallback: look for old format
        grade_match = re.search(r'Carbon Grade: ([A-F])', content)
        if grade_match:
            return grade_match.group(1), None
            
    except Exception:
        pass
    
    return None, None


def get_zerve_recommendations(complexity_feedback: str) -> list[str]:
    """Analyze complexity feedback for high-frequency patterns and suggest optimizations.
    
    Returns list of 'Zerve' recommendations for batch processing or serverless patterns.
    """
    recommendations = []
    feedback_lower = (complexity_feedback or "").lower()
    
    # Detect high-frequency logic patterns
    high_freq_indicators = [
        'loop', 'iteration', 'for each', 'repeated', 'multiple calls',
        'subprocess', 'api call', 'http request', 'database query',
        'event', 'trigger', 'webhook', 'polling', 'interval'
    ]
    
    has_high_freq = any(indicator in feedback_lower for indicator in high_freq_indicators)
    
    if has_high_freq:
        if 'subprocess' in feedback_lower or 'api' in feedback_lower or 'http' in feedback_lower:
            recommendations.append(
                "**Batch Processing**: Group multiple API/subprocess calls into batches to reduce idle energy waste."
            )
        
        if 'loop' in feedback_lower or 'iteration' in feedback_lower or 'repeated' in feedback_lower:
            recommendations.append(
                "**Serverless Pattern**: Consider event-driven serverless functions for high-frequency logic to minimize idle compute."
            )
        
        if 'polling' in feedback_lower or 'interval' in feedback_lower:
            recommendations.append(
                "**Event-Driven Architecture**: Replace polling with webhooks/events to eliminate unnecessary CPU cycles."
            )
    
    # Detect I/O patterns
    if 'file' in feedback_lower and ('read' in feedback_lower or 'write' in feedback_lower):
        recommendations.append(
            "**Lazy I/O**: Use streaming/generators instead of loading entire files to reduce memory and energy footprint."
        )
    
    return recommendations


def analyze_complexity_with_copilot(main_script: str = "aura.py", snippet_lines: int = 20) -> str:
    """Send a short main-script snippet to GitHub Copilot CLI for complexity analysis."""
    try:
        if not os.path.exists(main_script):
            return "Main script not found. Skipping complexity analysis."

        with open(main_script, 'r', encoding='utf-8') as f:
            lines = f.read().splitlines()

        # Use a shorter snippet for faster response (20 lines by default)
        snippet = "\n".join(lines[:snippet_lines])
        if not snippet.strip():
            return "Main script is empty. Skipping complexity analysis."

        # Check for copilot CLI (GitHub Copilot CLI)
        copilot_bin = shutil.which('copilot')
        if not copilot_bin:
            return "GitHub Copilot CLI not found. Install with: npm install -g @github/copilot"

        # Build a concise prompt for complexity analysis - ask for structured output
        prompt = (
            f"Analyze this code for algorithmic complexity (Big O). Identify nested loops or redundant I/O "
            f"that cause high CPU spikes. Suggest one Carbon-Neutral refactor to reduce energy consumption. "
            f"Give a brief, structured response with: 1) Complexity rating, 2) Issues found, 3) One refactor suggestion.\n\n{snippet}"
        )

        # Use copilot CLI via stdin with /quit to exit after response
        input_text = f"{prompt}\n/quit\n"
        
        result = subprocess.run(
            [copilot_bin],
            input=input_text,
            capture_output=True,
            text=True,
            timeout=90
        )

        output = (result.stdout or "").strip()
        error = (result.stderr or "").strip()

        if output:
            # Clean up the output - extract only the actual analysis, skip tool logs
            clean_lines = []
            in_analysis = False
            skip_patterns = [
                '● Read', '● Check', '● Grep', '● Explore', '● Create',
                '└ ', '$ ', 'lines read', 'lines found', 'lines...',
                'Total usage est:', 'API time spent:', 'Total session time:',
                'Total code changes:', 'Breakdown by AI model:', 'claude-',
                'I\'ll analyze', 'Let me analyze', 'Would you like me to'
            ]
            
            for line in output.split('\n'):
                stripped = line.strip()
                
                # Skip empty lines
                if not stripped:
                    if in_analysis:
                        clean_lines.append('')  # Keep paragraph breaks in analysis
                    continue
                
                # Skip copilot tool logs and stats
                if any(pattern in line for pattern in skip_patterns):
                    continue
                
                # Skip copilot prompts
                if stripped.startswith('>') or stripped.startswith('copilot>'):
                    continue
                
                # Start capturing when we see analysis headers or bullet points
                if stripped.startswith('##') or stripped.startswith('**') or stripped.startswith('###'):
                    in_analysis = True
                
                # Also capture numbered lists, bullet points, and code blocks
                if stripped.startswith('-') or stripped.startswith('1.') or stripped.startswith('2.') or stripped.startswith('3.'):
                    in_analysis = True
                
                if stripped.startswith('```'):
                    in_analysis = True
                
                if in_analysis or stripped.startswith('##') or stripped.startswith('**'):
                    clean_lines.append(line)
            
            # Remove trailing empty lines
            while clean_lines and not clean_lines[-1].strip():
                clean_lines.pop()
            
            result_text = '\n'.join(clean_lines).strip()
            return result_text if result_text else "Copilot analysis completed. Code appears efficient."
        elif error:
            if "auth" in error.lower() or "login" in error.lower():
                return "GitHub Copilot not authenticated. Run: copilot login"
            return f"Copilot: {error[:100]}"

        return "Copilot analysis completed. Using local O(n) assessment."
    except subprocess.TimeoutExpired:
        return "Analysis timeout. Using local O(n) assessment for filesystem operations."
    except Exception as e:
        return f"Analysis error: {str(e)[:80]}. Using local O(n) assessment."


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
    theme = get_theme('check')
    console.print(render_title_panel("◆ AURA — SECURITY ◆", 'check'))
    
    # Pre-flight check: Verify Copilot CLI authentication
    if not check_copilot_auth():
        console.print(f"[bold {theme['primary']}]⚠ Aura needs your help![/bold {theme['primary']}]")
        console.print(f"Please run [bold {theme['accent']}]copilot login[/bold {theme['accent']}] to authenticate.\n")
        return

    # Make scan feel more alive
    _print_live_panel("Scanning", "Analyzing files for exposed secrets...", style=theme['secondary'], wait=0.8)
    secrets_found, env_issues, remediation_prompt = scan_secrets()
    console.print()
    
    if secrets_found:
        # Create a Rich Table for secrets findings
        table = Table(
            title=f"[bold {theme['primary']}]Security Findings[/bold {theme['primary']}]",
            border_style=theme['border'],
            box=box.ROUNDED
        )
        table.add_column("File", style=theme['text'])
        table.add_column("Type", style=theme['accent'])
        table.add_column("Status", style=theme['primary'])
        
        for filepath, secret_type, value in secrets_found:
            table.add_row(filepath, secret_type, "⚠ Review Required")
        
        console.print(table)
        console.print()
        
        # Query Copilot for remediation guidance
        loading_spinner = Spinner("dots", text=f"[{theme['secondary']}]Consulting AI for remediation...[/{theme['secondary']}]")
        with Live(loading_spinner, console=console, refresh_per_second=8, transient=True):
            copilot_path = shutil.which('copilot')
        
        if not copilot_path:
            console.print("[bold yellow]Note:[/bold yellow] 'copilot' CLI not found. Install the Copilot CLI to get AI-powered remediation guidance.")
        else:
            try:
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

                input_text = f"{prompt}\n/quit\n"
                
                result = subprocess.run(
                    [copilot_path],
                    input=input_text,
                    capture_output=True,
                    text=True,
                    timeout=90
                )

                copilot_out = (result.stdout or '').strip()
                
                # Clean the output
                if copilot_out:
                    clean_lines = []
                    for line in copilot_out.split('\n'):
                        line_stripped = line.strip()
                        if any(skip in line_stripped for skip in ['Total usage:', 'API time:', 'session time:', '●', '└', '├']):
                            continue
                        clean_lines.append(line)
                    copilot_out = '\n'.join(clean_lines)

                if copilot_out:
                    render_ai_output(copilot_out, "🛡️ Remediation Steps", 'check')
                else:
                    console.print("[bold yellow]Note:[/bold yellow] Copilot returned no output.")

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
    """Code health pulse subcommand - Wellness dashboard with activity metrics."""
    from rich.align import Align
    from rich.columns import Columns
    from rich.rule import Rule

    theme = get_theme('pulse')

    if not getattr(args, 'compact', False):
        console.print(render_title_panel("◆ AURA — PULSE ◆", 'pulse'))

    _print_live_panel("Analyzing", "Compiling activity signals...", style=theme['secondary'], wait=(0.6 if not getattr(args, 'compact', False) else 0))

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
    left = Panel(Group(stats_table, Text("\nActivity (last 6h)", style="bold underline"), *hist_lines), title="📊 Overview", border_style=theme['secondary'])
    right_items = [focus_text]
    if git_info:
        right_items.append(Text(git_info, style="dim"))
    right_items.append(Text("\nSuggested micro-actions:", style="bold underline"))
    # Suggest micro actions (non-destructive)
    micro = ["Run tests (small target)", "Add 1 TODO", "Refactor 1 small func", "Update a short doc line"]
    for i, m in enumerate(micro, start=1):
        right_items.append(Text(f"{i}. {m}", style="white"))

    right = Panel(Group(*right_items), title="🎯 Focus & Suggestions", border_style=theme['primary'])

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
    console.print(Panel(status_text, border_style=theme['primary'] if minutes_since < 30 else "yellow"))

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
            console.print(Panel(Text(stretch_text, style="white"), title="🧘 Zen Break", border_style=theme['accent']))
            console.print(Panel(Text("🎧 Vibe Check: Open [link=https://lofi.co]Lofi.co[/link] for focus beats.", style="white"), border_style=theme['secondary']))


def cmd_story(args):
    """Code story/documentation subcommand - Founder's Journal."""
    theme = get_theme('story')
    
    console.print(render_title_panel("◆ AURA — STORY ◆", 'story'))

    _print_live_panel("Analyzing changes", "Gathering recent code updates...", style=theme['secondary'], wait=0.8)
    git_diff = get_git_diff(lines=40)

    if not git_diff:
        console.print(Panel(
            "[bold cyan]ℹ️  No code changes detected.[/bold cyan]\n\n"
            "Tip: Make a change and commit to generate your Founder's Journal entry.",
            border_style=theme['secondary'],
            padding=(1, 2)
        ))
        return

    loading_spinner = Spinner("dots", text=f"[{theme['primary']}]✨ Composing your Founder's Journal...[/{theme['primary']}]")
    journal_entry = None
    with Live(loading_spinner, console=console, refresh_per_second=8, transient=True):
        try:
            copilot_bin = shutil.which('copilot')
            if copilot_bin:
                prompt = (
                    "Based on these recent code changes, write a short, inspiring 'Founder's Journal' entry "
                    "that celebrates the progress. Use 3-4 sentences with a confident, proud tone. "
                    "Start with something like 'Today marks...' or 'Another milestone...' - make the developer feel accomplished.\n\n"
                    f"Code changes:\n{git_diff}"
                )
                input_text = f"{prompt}\n/quit\n"
                cp = subprocess.run([copilot_bin], input=input_text, capture_output=True, text=True, timeout=60)
                raw_output = (cp.stdout or cp.stderr or "").strip()
                # Clean the output
                clean_lines = []
                for line in raw_output.split('\n'):
                    line_stripped = line.strip()
                    if not line_stripped:
                        continue
                    if any(skip in line_stripped for skip in ['Total usage:', 'API time:', 'session time:', '●', '└', '├']):
                        continue
                    clean_lines.append(line)
                journal_entry = '\n'.join(clean_lines)
            if not journal_entry:
                journal_entry = (
                    "Today marks meaningful progress on the codebase. The changes demonstrate thoughtful engineering "
                    "and move the project closer to its goals. Every commit is a step forward."
                )
        except subprocess.TimeoutExpired:
            journal_entry = (
                "Progress continues steadily. The team delivered valuable updates, keeping momentum strong and the vision clear."
            )
        except Exception:
            journal_entry = (
                "This session added thoughtful refinements that strengthen the foundation and propel the project forward."
            )

    # Clean the journal entry
    final_entry = journal_entry.replace('**', '').strip()

    console.print(Rule(style="dim"))
    
    # Render AI output using the helper for consistency
    render_ai_output(final_entry, "📖 Today's Story", 'story')
    
    # Append to STORY_JOURNAL.md
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    journal_md_entry = f"""
### {timestamp}

{final_entry}

---
"""
    
    try:
        journal_header = f"""# 📖 Founder's Journal - {os.path.basename(os.getcwd())}

*Your development story, one commit at a time.*

---
"""
        if os.path.exists('STORY_JOURNAL.md'):
            with open('STORY_JOURNAL.md', 'a', encoding='utf-8') as f:
                f.write(journal_md_entry)
        else:
            with open('STORY_JOURNAL.md', 'w', encoding='utf-8') as f:
                f.write(journal_header + journal_md_entry)
        
        console.print(Panel(
            Text("✓ Entry added to STORY_JOURNAL.md", style=theme['accent']),
            border_style=theme['border'],
            padding=(0, 2)
        ))
    except Exception as e:
        console.print(f"[yellow]⚠️  Could not save STORY_JOURNAL.md: {str(e)[:50]}[/yellow]")
    
    # Proud closing message
    console.print(Panel(
        Text("🎉 You're building something great. Keep shipping!", style=f"bold {theme['primary']}"),
        border_style=theme['primary'],
        padding=(0, 2)
    ))


def cmd_eco(args):
    """Ecosystem analysis subcommand - Carbon audit."""
    theme = get_theme('eco')
    
    if not getattr(args, 'compact', False):
        console.print(render_title_panel("◆ AURA — ECO ◆", 'eco'))

    # Scan for bloat with loading indicator
    if getattr(args, 'compact', False):
        largest_files, total_bloat = scan_bloat()
    else:
        loading_spinner = Spinner("dots", text=f"[{theme['primary']}]🌿 Scanning filesystem for bloat...[/{theme['primary']}]")
        with Live(loading_spinner, console=console, refresh_per_second=8, transient=True):
            largest_files, total_bloat = scan_bloat()

    # Analyze complexity with Copilot (skip if --no-ai flag)
    if getattr(args, 'no_ai', False):
        complexity_feedback = "AI complexity audit skipped (--no-ai flag used). Local assumption: O(n) patterns."
    else:
        if getattr(args, 'compact', False):
            complexity_feedback = analyze_complexity_with_copilot()
        else:
            loading_spinner = Spinner("dots", text=f"[{theme['primary']}]🌿 Analyzing code complexity with AI...[/{theme['primary']}]")
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
            border_style=theme['primary'],
            box=box.ROUNDED,
            padding=(1, 2)
        ))

        if complexity_feedback:
            render_ai_output(complexity_feedback, "🌿 AI Insights", 'eco')
        
        # Display Zerve recommendations if high-frequency patterns detected
        zerve_recs = get_zerve_recommendations(complexity_feedback)
        if zerve_recs:
            zerve_content = "\n".join(f"• {rec}" for rec in zerve_recs)
            console.print(Panel(
                Markdown(zerve_content),
                title="⚡ Zerve Optimizations",
                border_style=theme['border'],
                box=box.ROUNDED,
                padding=(1, 2)
            ))

    # Generate GREEN_AUDIT.md documentation (Persistent Green Journal)
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    
    # Get previous grade for progress tracking
    prev_grade, prev_timestamp = get_previous_carbon_grade()
    
    # Calculate progress
    grade_order = {'A': 1, 'B': 2, 'C': 3, 'D': 4, 'E': 5, 'F': 6}
    if prev_grade and prev_grade in grade_order and carbon_score in grade_order:
        prev_rank = grade_order[prev_grade]
        curr_rank = grade_order[carbon_score]
        if curr_rank < prev_rank:
            progress_text = f"🌱 Getting Greener! Improved from {prev_grade} → {carbon_score}"
            progress_emoji = "📈"
        elif curr_rank > prev_rank:
            progress_text = f"⚠️ More Bloated - Regressed from {prev_grade} → {carbon_score}"
            progress_emoji = "📉"
        else:
            progress_text = f"➡️ Stable - Maintained grade {carbon_score}"
            progress_emoji = "📊"
    else:
        progress_text = "🆕 First Audit - Baseline established"
        progress_emoji = "🎯"
    
    # Get Zerve recommendations for high-frequency patterns
    zerve_recs = get_zerve_recommendations(complexity_feedback)
    zerve_section = ""
    if zerve_recs:
        zerve_section = "\n**Zerve Optimizations (Energy-Efficient Patterns):**\n" + "\n".join(f"- {rec}" for rec in zerve_recs)
    
    heavy_file_lines = "\n".join(
        [f"- {fpath} ({size_mb:.2f} MB) — {impact}" for fpath, size_mb, impact in largest_files if size_mb > 50]
    )
    if not heavy_file_lines:
        heavy_file_lines = "✓ No energy-heavy files detected"

    table_lines = "\n".join(
        [f"| {fpath} | {size_mb:.2f} MB | {impact} |" for fpath, size_mb, impact in largest_files]
    ) or "| No files found | - | - |"

    # New audit entry (appended to journal)
    audit_entry = f"""
### Audit - {timestamp}

**Carbon Grade: {carbon_score}** {progress_emoji}

#### Progress
{progress_text}

#### Static Bloat Scan (Top 5 Largest Files)

| File | Size | Energy Impact |
| --- | --- | --- |
{table_lines}

**Energy Heavy (>50MB):**
{heavy_file_lines}

**Total Size (Top {len(largest_files)} files):** {total_bloat_text}

#### AI Complexity Audit

{complexity_feedback}

#### Recommendations

1. **Prune or ignore heavy assets**: Move large artifacts to archives or add them to `.gitignore`.
2. **Refactor hotspots**: Apply the AI-suggested refactor to reduce CPU spikes.
3. **Monitor sustainability**: Run `aura eco` regularly and track grade trends.
{zerve_section}

---
"""

    try:
        # Persistent Green Journal: Append instead of overwrite
        journal_header = f"""# 🌿 Green Journal - {os.path.basename(os.getcwd())}

*Sustainability tracking for your codebase. Each audit is appended below.*

"""
        if os.path.exists('GREEN_AUDIT.md'):
            # Append new entry to existing journal
            with open('GREEN_AUDIT.md', 'a', encoding='utf-8') as f:
                f.write(audit_entry)
        else:
            # Create new journal with header
            with open('GREEN_AUDIT.md', 'w', encoding='utf-8') as f:
                f.write(journal_header + audit_entry)
        
        if not getattr(args, 'compact', False):
            # Show progress panel
            console.print(Panel(
                Text(f"{progress_emoji} {progress_text}", style="bright_green"),
                title="🌿 Sustainability Progress",
                border_style="green",
                padding=(0, 2)
            ))
            console.print(Panel(
                Text("✓ Audit appended to GREEN_AUDIT.md", style="bright_green"),
                border_style="green",
                padding=(0, 2)
            ))
    except Exception as e:
        console.print(f"[yellow]⚠️  Could not save GREEN_AUDIT.md: {str(e)[:50]}[/yellow]")


def cmd_fly(args):
    """Agentic Onboarding - Automate the 'blank page' phase of development."""
    theme = get_theme('fly')
    
    console.print(render_title_panel("◆ AURA — FLY ◆", 'fly'))
    
    project_type = getattr(args, 'project_type', None)
    
    # If no project type provided, show help
    if not project_type:
        console.print(Panel(
            Text(
                "✈️ Agentic Onboarding\n\n"
                "Aura Fly automates project setup. Provide a project type:\n\n"
                "  aura fly \"Next.js with Tailwind\"\n"
                "  aura fly \"Python FastAPI\"\n"
                "  aura fly \"React TypeScript\"\n"
                "  aura fly \"Python Data Science API\"\n\n"
                "Aura will generate and execute the setup commands for you.",
                style=theme['text']
            ),
            title="🛫 Flight Plan Required",
            border_style=theme['primary'],
            padding=(1, 2)
        ))
        return
    
    console.print(Panel(
        Text(f"Project Type: {project_type}", style=f"bold {theme['primary']}"),
        title="✈️ Flight Plan",
        border_style=theme['border'],
        padding=(0, 2)
    ))
    
    # AI Planning: Generate setup commands using Copilot CLI
    loading_spinner = Spinner("dots", text=f"[{theme['primary']}]🚀 Consulting Copilot for setup commands...[/{theme['primary']}]")
    commands = []
    
    with Live(loading_spinner, console=console, refresh_per_second=8, transient=True):
        copilot_bin = shutil.which('copilot')
        if not copilot_bin:
            console.print(Panel(
                Text("GitHub Copilot CLI not found. Install with: npm install -g @github/copilot", style="red"),
                border_style="red",
                padding=(1, 2)
            ))
            return
        
        prompt = (
            f"The user wants to start a {project_type}. Generate a list of the 5 essential bash commands needed to "
            f"initialize this project, install core dependencies, and create a README. "
            f"Output ONLY the commands as a newline-separated list, no explanations or numbering."
        )
        
        input_text = f"{prompt}\n/quit\n"
        
        try:
            result = subprocess.run(
                [copilot_bin],
                input=input_text,
                capture_output=True,
                text=True,
                timeout=90
            )
            
            output = (result.stdout or "").strip()
            
            if output:
                # Parse commands from output - filter out non-command lines
                for line in output.split('\n'):
                    line = line.strip()
                    # Skip empty lines, comments, headers, and copilot metadata
                    if not line:
                        continue
                    if line.startswith('#') or line.startswith('●') or line.startswith('└'):
                        continue
                    if 'Total usage' in line or 'API time' in line or 'session time' in line:
                        continue
                    if line.startswith('$'):
                        line = line[1:].strip()  # Remove leading $
                    # Check if it looks like a command
                    if any(cmd in line.lower() for cmd in ['npm', 'npx', 'pip', 'python', 'mkdir', 'cd', 'git', 'touch', 'echo', 'cat', 'curl', 'wget', 'yarn', 'pnpm', 'cargo', 'go ', 'brew', 'apt']):
                        commands.append(line)
                    elif line.startswith('mkdir') or line.startswith('cd ') or line.startswith('echo '):
                        commands.append(line)
        except subprocess.TimeoutExpired:
            console.print(Panel(
                Text("Copilot timeout. Please try again.", style=theme['secondary']),
                border_style=theme['secondary'],
                padding=(1, 2)
            ))
            return
        except Exception as e:
            console.print(f"[{theme['secondary']}]⚠️  Copilot error: {str(e)[:50]}[/{theme['secondary']}]")
            return
    
    # Limit to 5 commands
    commands = commands[:5]
    
    if not commands:
        console.print(Panel(
            Text("Could not generate setup commands. Try a more specific project type.", style=theme['secondary']),
            border_style=theme['secondary'],
            padding=(1, 2)
        ))
        return
    
    # Safety & Confirmation: Display the plan
    command_list = "\n".join(f"  {i+1}. {cmd}" for i, cmd in enumerate(commands))
    console.print(Panel(
        Text(f"Generated Flight Plan ({len(commands)} steps):\n\n{command_list}", style="cyan"),
        title="🛫 Pre-Flight Checklist",
        border_style=theme['border'],
        box=box.ROUNDED,
        padding=(1, 2)
    ))
    
    console.print()
    console.print(f"[bold {theme['primary']}]🚀 Aura is ready for takeoff.[/bold {theme['primary']}]")
    
    # Ask for explicit confirmation
    try:
        response = input("   Execute these commands? (y/n): ").strip().lower()
    except (KeyboardInterrupt, EOFError):
        console.print("\n[yellow]Flight cancelled.[/yellow]")
        return
    
    if response != 'y':
        console.print(Panel(
            Text("✈️ Flight aborted. No changes made.", style=theme['text']),
            border_style=theme['secondary'],
            padding=(0, 2)
        ))
        return
    
    console.print()
    console.print(Rule(style="dim"))
    console.print(f"[bold {theme['primary']}]🛫 Initiating launch sequence...[/bold {theme['primary']}]\n")
    
    # Execution with Feedback - Interactive mode (output flows to terminal)
    completed = 0
    failed_steps = []
    
    for i, cmd in enumerate(commands):
        step_num = i + 1
        console.print(f"[bold cyan]Step {step_num}/{len(commands)}:[/bold cyan] {cmd}")
        console.print()
        
        success = False
        while not success:
            try:
                # Run command interactively - output flows directly to terminal
                # Do not use capture_output so user can interact with prompts
                exit_code = subprocess.call(cmd, shell=True, cwd=os.getcwd())
                
                if exit_code == 0:
                    console.print(f"\n[green]✓ Step {step_num} completed[/green]\n")
                    completed += 1
                    success = True
                else:
                    console.print(f"\n[yellow]⚠️ Step {step_num} returned exit code {exit_code}[/yellow]")
                    try:
                        retry = input("   (R)etry, (S)kip, or (A)bort? ").strip().lower()
                    except (KeyboardInterrupt, EOFError):
                        console.print("\n[yellow]Flight aborted.[/yellow]")
                        return
                    
                    if retry == 'r':
                        console.print("[yellow]Retrying...[/yellow]\n")
                        continue
                    elif retry == 'a':
                        console.print("[yellow]Flight aborted.[/yellow]")
                        return
                    else:  # Skip
                        console.print(f"[yellow]Skipping step {step_num}[/yellow]\n")
                        failed_steps.append((step_num, cmd))
                        success = True  # Move to next
                        
            except Exception as e:
                console.print(f"\n[red]✗ Error in step {step_num}: {str(e)[:50]}[/red]")
                try:
                    retry = input("   (R)etry, (S)kip, or (A)bort? ").strip().lower()
                except (KeyboardInterrupt, EOFError):
                    console.print("\n[yellow]Flight aborted.[/yellow]")
                    return
                
                if retry == 'r':
                    console.print("[yellow]Retrying...[/yellow]\n")
                    continue
                elif retry == 'a':
                    console.print("[yellow]Flight aborted.[/yellow]")
                    return
                else:  # Skip
                    console.print(f"[yellow]Skipping step {step_num}[/yellow]\n")
                    failed_steps.append((step_num, cmd))
                    success = True
    
    console.print(Rule(style="dim"))
    
    # Final status
    if failed_steps:
        skip_list = "\n".join(f"  • Step {s}: {c}" for s, c in failed_steps)
        console.print(Panel(
            Text(f"✈️ Flight completed with {len(failed_steps)} skipped step(s):\n\n{skip_list}", style=theme['secondary']),
            title="🛬 Landing Report",
            border_style=theme['secondary'],
            padding=(1, 2)
        ))
    else:
        console.print(Panel(
            Text(f"✈️ All {completed} steps completed successfully!\n\nYour {project_type} project is ready.", style=theme['accent']),
            title="🛬 Perfect Landing",
            border_style=theme['accent'],
            padding=(1, 2)
        ))
    
    # Final Handover: Run aura story to document the project birth
    console.print()
    console.print("[bold blue]📖 Documenting project birth...[/bold blue]\n")
    
    try:
        # Create a simple args object for cmd_story
        class StoryArgs:
            pass
        story_args = StoryArgs()
        cmd_story(story_args)
    except Exception as e:
        console.print(f"[yellow]⚠️ Could not generate story: {str(e)[:50]}[/yellow]")








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
    fly_parser = subparsers.add_parser(
        'fly',
        help='Agentic Onboarding - Automate project setup',
        aliases=['perf', 'init']
    )
    fly_parser.add_argument('project_type', nargs='?', default=None, help='Project type (e.g., "Next.js with Tailwind", "Python FastAPI")')
    fly_parser.set_defaults(func=cmd_fly)
    
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
