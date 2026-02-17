#!/usr/bin/env python3
"""
KOV CLI - Main entry point
Rich UI with loading indicators and responsive feedback
"""

import os
import sys
import logging
import typer
from typing import Optional
from rich.console import Console
from rich.prompt import Prompt
from rich.spinner import Spinner
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from rich.markdown import Markdown
import threading
import time
from KOV.core.advanced_agent import AdvancedKOVAgent

app = typer.Typer(
    name="kov",
    help="KOV - Local AI Developer Agent",
    add_completion=False
)

console = Console()

def setup_logging(debug: bool = False):
    """Configure logging for KOV operations."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('kov.log'),
            logging.StreamHandler() if debug else logging.NullHandler()
        ]
    )

def print_banner(model: str):
    """Print KOV welcome banner with rich formatting."""
    banner = Panel.fit(
        "[bold blue]🤖 KOV - Local AI Developer Agent[/bold blue]\n"
        f"[dim]Powered by {model} via Ollama[/dim]\n"
        "[dim]Local + Internet Access Available[/dim]\n\n"
        "[yellow]Commands:[/yellow] /quit, /help, /clear, /debug",
        border_style="blue"
    )
    console.print(banner)
    console.print()

def print_help():
    """Print available commands with rich formatting."""
    help_text = """
[bold yellow]Available Commands:[/bold yellow]
• [cyan]/quit, /exit[/cyan]  - Exit KOV
• [cyan]/help[/cyan]         - Show this help
• [cyan]/clear[/cyan]        - Clear conversation history
• [cyan]/debug[/cyan]        - Toggle debug mode

[bold yellow]Example Usage:[/bold yellow]
• "What files are in this directory?"
• "Show me the README file"
• "Check what's on google.com"
• "Create a Python script"
• "Download a file from URL"
    """
    console.print(Panel(help_text, border_style="yellow", title="Help"))

def show_thinking_indicator(stop_event):
    """Show a thinking indicator while processing."""
    spinner = Spinner("dots", text="[dim]KOV is thinking...[/dim]")
    with Live(spinner, console=console, refresh_per_second=10):
        while not stop_event.is_set():
            time.sleep(0.1)

@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    debug: bool = typer.Option(False, "--debug", "-d", help="Enable debug mode"),
    model: str = typer.Option("llama3:latest", "--model", "-m", help="Ollama model to use"),
    version: bool = typer.Option(False, "--version", "-v", help="Show version")
):
    """KOV - Local AI Developer Agent. Start interactive chat by default."""
    if version:
        show_version()
        return
    
    if ctx.invoked_subcommand is None:
        # Default behavior - start chat
        start_chat(debug, model)

def start_chat(debug: bool = False, model: str = "llama3:latest"):
    """Start interactive chat session with KOV agent."""
    setup_logging(debug)
    print_banner(model)
    
    try:
        with console.status("[bold green]Initializing Advanced KOV...", spinner="dots"):
            agent = AdvancedKOVAgent(debug=debug, model=model)
        
        console.print("[green]✓[/green] KOV initialized successfully!\n")
        debug_mode = debug
        
        while True:
            try:
                # Rich prompt with custom styling
                user_input = Prompt.ask(
                    "[bold cyan]❯[/bold cyan]",
                    console=console
                ).strip()
                
                # Handle special commands
                if user_input.lower() in ['/quit', '/exit']:
                    console.print("[yellow]Goodbye! 👋[/yellow]")
                    break
                elif user_input.lower() == '/help':
                    print_help()
                    continue
                elif user_input.lower() == '/clear':
                    with console.status("[yellow]Clearing conversation history...", spinner="dots"):
                        agent = AdvancedKOVAgent(debug=debug_mode, model=model)
                    console.print("[green]✓[/green] Conversation history cleared.\n")
                    continue
                elif user_input.lower() == '/debug':
                    debug_mode = not debug_mode
                    with console.status("[yellow]Toggling debug mode...", spinner="dots"):
                        agent = AdvancedKOVAgent(debug=debug_mode, model=model)
                    status = "enabled" if debug_mode else "disabled"
                    console.print(f"[green]✓[/green] Debug mode {status}.\n")
                    continue
                    
                if not user_input:
                    continue
                
                # Show thinking indicator in separate thread
                stop_event = threading.Event()
                thinking_thread = threading.Thread(target=show_thinking_indicator, args=(stop_event,))
                thinking_thread.start()
                
                try:
                    # Process with agent
                    response = agent.run(user_input)
                    
                    # Stop thinking indicator
                    stop_event.set()
                    thinking_thread.join()
                    
                    # Display response with rich formatting
                    response_panel = Panel(
                        Markdown(response),
                        border_style="green",
                        title="[bold green]KOV Response[/bold green]",
                        title_align="left"
                    )
                    console.print(response_panel)
                    console.print()
                    
                except Exception as e:
                    stop_event.set()
                    thinking_thread.join()
                    console.print(f"[red]Error:[/red] {str(e)}")
                    if debug_mode:
                        console.print_exception()
                
            except KeyboardInterrupt:
                console.print("\n[yellow]Goodbye! 👋[/yellow]")
                break
            except EOFError:
                console.print("\n[yellow]Input stream closed. Exiting.[/yellow]")
                break
            except Exception as e:
                console.print(f"[red]Error:[/red] {str(e)}")
                if debug_mode:
                    console.print_exception()
                    
    except Exception as e:
        console.print(f"[red]Failed to initialize KOV:[/red] {str(e)}")
        if debug:
            console.print_exception()
        sys.exit(1)

@app.command()
def chat(
    debug: bool = typer.Option(False, "--debug", "-d", help="Enable debug mode"),
    model: str = typer.Option("llama3:latest", "--model", "-m", help="Ollama model to use")
):
    """Start interactive chat session with KOV agent (same as default behavior)."""
    start_chat(debug, model)

@app.command()
def version():
    """Show KOV version information."""
    show_version()

def show_version():
    """Display version information."""
    from KOV import __version__
    version_panel = Panel(
        f"[bold blue]KOV version {__version__}[/bold blue]\n"
        "[dim]Local AI Developer Agent[/dim]",
        border_style="blue"
    )
    console.print(version_panel)

if __name__ == "__main__":
    app()
