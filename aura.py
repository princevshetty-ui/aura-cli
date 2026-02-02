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


class Colors:
    """ANSI color codes for terminal styling."""
    RESET = '\033[0m'
    BOLD = '\033[1m'
    
    # Colors
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'


def colorize(text, color):
    """Apply color to text if terminal supports it."""
    try:
        return f"{color}{text}{Colors.RESET}"
    except Exception:
        return text


def print_styled_message(emoji, title, message, color):
    """Print a stylized message with emoji, title, and color."""
    styled_title = colorize(title, color + Colors.BOLD)
    styled_message = colorize(message, color)
    print(f"\n{emoji} {styled_title}")
    print(f"   {styled_message}\n")


def print_ai_box(text):
    lines = text.split('\n')
    width = min(max(len(line) for line in lines), 80)  # Limit width to 80 chars
    
    print("\n" + "┌" + "─" * (width + 2) + "┐")
    print("│ " + "AURA AI ADVICE".center(width) + " │")
    print("├" + "─" * (width + 2) + "┤")
    for line in lines:
        # Wrap long lines if necessary or just print them
        print(f"│ {line.ljust(width)} │")
    print("└" + "─" * (width + 2) + "┘\n")


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
    print_styled_message(
        "🛡️ ",
        "Aura Security",
        "Security Scan Started...",
        Colors.RED
    )
    
    secrets_found, env_issues, remediation_prompt = scan_secrets()
    
    if secrets_found:
        print(f"⚠️  {Colors.RED}{Colors.BOLD}Found {len(secrets_found)} potential secret(s):{Colors.RESET}")
        for filepath, secret_type, value in secrets_found:
            masked_value = value[:8] + '...' if len(value) > 8 else value
            print(f"   • {filepath}: {secret_type} ({masked_value})")
        
        # Query GitHub Copilot for guidance
        print(f"\n{Colors.BLUE}Asking GitHub Copilot for remediation guidance...{Colors.RESET}\n")
        try:
            copilot_path = shutil.which('copilot')
            if not copilot_path:
                raise FileNotFoundError("copilot CLI not found")

            short_prompt = "How do I remove a leaked secret from git history safely?"
            ai_response = subprocess.run(
                [copilot_path, 'explain', short_prompt],
                capture_output=True,
                text=True,
                timeout=30
            )

            if ai_response.returncode != 0:
                stderr_hint = (ai_response.stderr or "").lower()
                if "unknown" in stderr_hint or "invalid" in stderr_hint:
                    ai_response = subprocess.run(
                        [copilot_path, '-p', short_prompt],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
            if ai_response.returncode == 0:
                if ai_response.stdout:
                    print_ai_box(ai_response.stdout.strip())
                else:
                    print(f"{Colors.YELLOW}Note: Copilot returned no output.{Colors.RESET}")
            else:
                stderr = (ai_response.stderr or "").strip()
                if stderr:
                    print(f"{Colors.BLUE}{stderr}{Colors.RESET}")
                else:
                    print(f"{Colors.YELLOW}Note: Copilot returned no output.{Colors.RESET}")
        except FileNotFoundError:
            print(f"{Colors.YELLOW}Note: 'copilot' CLI not found. Install the Copilot CLI to get AI-powered remediation guidance.{Colors.RESET}")
        except subprocess.TimeoutExpired:
            print(f"{Colors.YELLOW}[⚠️] AI took too long to respond, please try again.{Colors.RESET}")
        except Exception as e:
            print(f"{Colors.YELLOW}Note: Could not query GitHub Copilot: {e}{Colors.RESET}")
    
    if env_issues:
        print(f"\n⚠️  {Colors.RED}{Colors.BOLD}Found {len(env_issues)} .env file(s) with incorrect permissions:{Colors.RESET}")
        for filepath, mode in env_issues:
            print(f"   • {filepath}: {mode} (should be 0o600)")
    
    if not secrets_found and not env_issues:
        print(f"{Colors.GREEN}{Colors.BOLD}✓ No security issues detected!{Colors.RESET}\n")


def cmd_pulse(args):
    """Code health pulse subcommand."""
    print_styled_message(
        "💓",
        "Aura Pulse",
        "Code Health Analysis Started...",
        Colors.GREEN
    )


def cmd_story(args):
    """Code story/documentation subcommand."""
    print_styled_message(
        "📖",
        "Aura Story",
        "Code Story Generation Started...",
        Colors.BLUE
    )


def cmd_eco(args):
    """Ecosystem analysis subcommand."""
    print_styled_message(
        "🌍",
        "Aura Eco",
        "Dependency Ecosystem Analysis Started...",
        Colors.CYAN
    )


def cmd_fly(args):
    """Performance flight check subcommand."""
    print_styled_message(
        "🚀",
        "Aura Fly",
        "Performance Analysis Started...",
        Colors.MAGENTA
    )


def main():
    """Main CLI entry point with argparse setup."""
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
