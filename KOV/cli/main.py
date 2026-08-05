"""KOV operator CLI for chat, autonomous coding, and protected controls."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from KOV.control.agent_loop import run_agent
from KOV.control.stop import StopController
from KOV.diagnostics.doctor import CheckStatus, run_doctor
from KOV.models.chat_gateway import ADKChatGateway
from KOV.runtime.privacy import apply_local_privacy_defaults

apply_local_privacy_defaults()

app = typer.Typer(name="kov", help="Deterministic local continual-improvement agent")
console = Console()


def state_root() -> Path:
    return Path(__file__).resolve().parents[2] / ".kov-state"


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", "-v", help="Show version"),
) -> None:
    """Start private stateless chat when no command is supplied."""

    if version:
        from KOV import __version__

        console.print(f"KOV {__version__}")
    elif ctx.invoked_subcommand is None:
        chat()


@app.command()
def chat() -> None:
    """General local chat; prompts are not written to KOV's ledger."""

    console.print(
        Panel.fit(
            "[bold green]KOV private chat[/bold green]\nFresh bounded context · /quit to exit",
            border_style="green",
        )
    )
    gateway = ADKChatGateway()
    while True:
        try:
            prompt = Prompt.ask("[bold cyan]❯[/bold cyan]").strip()
        except (KeyboardInterrupt, EOFError):
            break
        if prompt.lower() in {"/quit", "/exit"}:
            break
        if not prompt:
            continue
        with console.status("[green]Thinking…[/green]"):
            reply = asyncio.run(gateway.answer(prompt))
        console.print(Panel(reply.answer, border_style="green"))
        if reply.uncertainties:
            console.print("[yellow]Uncertainty:[/yellow] " + "; ".join(reply.uncertainties))


@app.command()
def improve(
    task: Annotated[str, typer.Argument(help="One focused repository improvement")],
    repo: Annotated[Path, typer.Option("--repo", help="Target Git repository")] = Path(
        "/home/digichameleon/adk/research-agent"
    ),
) -> None:
    """Run one isolated deterministic coding candidate."""

    with console.status("[green]KOV is executing a bounded candidate…[/green]"):
        result = run_agent(task, str(repo))
    console.print_json(
        json.dumps(
            {
                "run_id": result.run_id,
                "candidate_id": result.candidate_id,
                "status": result.status,
                "iterations": result.iterations,
                "branch": result.branch,
                "worktree": str(result.worktree),
                "changed_files": result.changed_files,
                "summary": result.final_summary,
            }
        )
    )
    if result.status != "passed":
        raise typer.Exit(1)


@app.command("doctor")
def doctor_command(json_output: bool = typer.Option(False, "--json")) -> None:
    """Run read-only machine and dependency readiness checks."""

    report = run_doctor()
    if json_output:
        console.print_json(report.model_dump_json())
    else:
        for check in report.checks:
            color = {
                CheckStatus.PASS: "green",
                CheckStatus.WARN: "yellow",
                CheckStatus.FAIL: "red",
            }[check.status]
            console.print(f"[{color}]{check.status.value.upper():>4}[/{color}] {check.summary}")
    if not report.ready:
        raise typer.Exit(1)


@app.command()
def status() -> None:
    """Show durable Pause and Emergency Stop state."""

    current = StopController(state_root() / "control").status()
    console.print_json(
        json.dumps(
            {
                "paused": current.paused,
                "emergency_stopped": current.emergency_stopped,
            }
        )
    )


@app.command()
def pause(reason: str = typer.Argument(...)) -> None:
    """Pause autonomous work at the next atomic boundary."""

    StopController(state_root() / "control").pause(reason)
    console.print("[yellow]KOV paused.[/yellow]")


@app.command("emergency-stop")
def emergency_stop(reason: str = typer.Argument(...)) -> None:
    """Persistently stop all future KOV action loops."""

    StopController(state_root() / "control").emergency_stop(reason)
    console.print("[red]Emergency Stop is active.[/red]")


@app.command()
def resume() -> None:
    """Clear Pause locally. Emergency Stop requires its explicit command."""

    StopController(state_root() / "control").resume(locally_authorized=True)
    console.print("[green]Pause cleared.[/green]")


@app.command("clear-emergency-stop")
def clear_emergency_stop() -> None:
    """Clear Emergency Stop from the local operator terminal."""

    StopController(state_root() / "control").clear_emergency_stop(locally_authorized=True)
    console.print("[green]Emergency Stop cleared.[/green]")


if __name__ == "__main__":
    app()
