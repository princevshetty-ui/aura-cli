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
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.layout import Layout
from rich.text import Text
from rich.spinner import Spinner
from rich.live import Live
import time

# Initialize Rich console for modern output with forced color support
console = Console(force_terminal=True, force_interactive=True)


def display_header():
    """Display the AURA CLI header with bold purple styling and animation."""
    # Animated header with initialization animation
    with console.status("[bold magenta]✨ Initializing Aura...[/bold magenta]", spinner="dots"):
        time.sleep(0.5)
    header_text = Text("✨ AURA CLI ✨", style="bold magenta", justify="center")
    panel = Panel(header_text, border_style="magenta", padding=(0, 2), expand=False)
    console.print(panel)


def check_copilot_auth():
    """
    Check if user is authenticated with Copilot CLI.
    Returns True if authenticated, False otherwise.
    """
    try:
        result = subprocess.run(
            ["copilot", "-i", "/login"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
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
    
    # Scan all files
    for root, dirs, files in os.walk('.'):
        # Remove excluded directories
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        for file in files:
            filepath = os.path.join(root, file)
            
            # Check .env files for permissions
            if file == '.env' or file.endswith('.env'):
                try:
                    stat_info = os.stat(filepath)
                    mode = stat_info.st_mode & 0o777
                    if mode != 0o600:
                        env_issues.append((filepath, oct(mode)))
                except Exception as e:
                    pass
            
            # Scan file content for secrets
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                    # Check for AWS keys
                    aws_matches = re.findall(aws_pattern, content)
                    if aws_matches:
                        for match in aws_matches:
                            secrets_found.append((filepath, 'AWS Access Key', match))
                    
                    # Check for Google API keys
                    google_matches = re.findall(google_pattern, content)
                    if google_matches:
                        for match in google_matches:
                            secrets_found.append((filepath, 'Google API Key', match))
            except (IsADirectoryError, PermissionError):
                pass
            except Exception:
                pass
    
    return secrets_found, env_issues, remediation_prompt


def cmd_check(args):
    """Security check subcommand."""
    console.print(Panel("[bold magenta]🛡️  Aura Security[/bold magenta]", border_style="magenta", padding=(0, 2)))
    
    # Pre-flight check: Verify Copilot CLI authentication
    if not check_copilot_auth():
        console.print("[bold red]⚠️  Aura needs your help![/bold red]")
        console.print("Please run [bold cyan]copilot /login[/bold cyan] to activate my AI core.\n")
        return
    
    # Animated scanning
    with console.status("[bold cyan]Scanning for security threats...[/bold cyan]", spinner="dots"):
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
        
        # Query GitHub Copilot for guidance
        console.print("[bold purple]Consulting the Oracle...[/bold purple]\n")
        try:
            copilot_path = shutil.which('copilot')
            if not copilot_path:
                raise FileNotFoundError("copilot CLI not found")

            # The --allow-all-tools flag is key for 2026 agentic workflows
            subprocess.run(["copilot", "--allow-all-tools", "-p", f"The security scan found a secret in {filepath}. IMMEDIATELY output the remediation steps as plain text and exit."])
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
    """Code health pulse subcommand."""
    console.print(Panel("[bold green]💓 Aura Pulse[/bold green]", border_style="green"))
    console.print("[bold green]Code Health Analysis Started...[/bold green]")


def cmd_story(args):
    """Code story/documentation subcommand."""
    console.print(Panel("[bold blue]📖 Aura Story[/bold blue]", border_style="blue"))
    console.print("[bold blue]Code Story Generation Started...[/bold blue]")


def cmd_eco(args):
    """Ecosystem analysis subcommand."""
    console.print(Panel("[bold cyan]🌍 Aura Eco[/bold cyan]", border_style="cyan"))
    console.print("[bold cyan]Dependency Ecosystem Analysis Started...[/bold cyan]")


def cmd_fly(args):
    """Performance flight check subcommand."""
    console.print(Panel("[bold magenta]🚀 Aura Fly[/bold magenta]", border_style="magenta"))
    console.print("[bold magenta]Performance Analysis Started...[/bold magenta]")


def main():
    """Main CLI entry point with argparse setup."""
    # Display header
    display_header()
    
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
    subparsers.add_parser(
        'check',
        help='Run security vulnerability checks',
        aliases=['sec']
    ).set_defaults(func=cmd_check)
    
    # Code health pulse command
    subparsers.add_parser(
        'pulse',
        help='Analyze code health and quality metrics',
        aliases=['health']
    ).set_defaults(func=cmd_pulse)
    
    # Code story command
    subparsers.add_parser(
        'story',
        help='Generate code documentation and stories',
        aliases=['doc']
    ).set_defaults(func=cmd_story)
    
    # Ecosystem analysis command
    subparsers.add_parser(
        'eco',
        help='Analyze project dependencies and ecosystem',
        aliases=['deps']
    ).set_defaults(func=cmd_eco)
    
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
    
    # Execute the selected command
    args.func(args)


if __name__ == '__main__':
    main()
