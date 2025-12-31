"""CLI interface for voice trainer."""

import time
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table
from rich.text import Text
from rich import box

from .analyzer import VoiceAnalyzer, VoiceAnalysis
from .database import VoiceDatabase
from .passages import get_random_passage, list_all_passages, get_passage_by_id
from .recorder import Recorder

app = typer.Typer(
    name="voice",
    help="Voice Training CLI - Track and improve your speaking voice",
    no_args_is_help=True,
)
console = Console()


def get_default_paths():
    """Get default paths for recordings and database."""
    base = Path.cwd()
    return {
        "recordings": base / "recordings",
        "database": base / "voice_trainer.db",
    }


@app.command()
def record(
    duration: int = typer.Option(10, "--duration", "-d", help="Recording duration in seconds"),
    passage: bool = typer.Option(False, "--passage", "-p", help="Show a passage to read"),
    passage_id: Optional[str] = typer.Option(None, "--passage-id", help="Specific passage ID to use"),
    analyze_after: bool = typer.Option(True, "--analyze/--no-analyze", help="Analyze recording after capture"),
    save: bool = typer.Option(True, "--save/--no-save", help="Save analysis to database"),
):
    """Record a new voice sample from the microphone."""
    paths = get_default_paths()

    # Show passage if requested
    selected_passage = None
    if passage or passage_id:
        if passage_id:
            selected_passage = get_passage_by_id(passage_id)
            if not selected_passage:
                console.print(f"[red]Passage '{passage_id}' not found.[/red]")
                raise typer.Exit(1)
        else:
            selected_passage = get_random_passage()

        console.print()
        console.print(Panel(
            f"[bold cyan]{selected_passage.title}[/bold cyan]\n\n"
            f"[white]{selected_passage.text}[/white]\n\n"
            f"[dim]Focus: {selected_passage.focus.replace('_', ' ').title()}[/dim]",
            title="Read This Passage",
            border_style="cyan",
        ))
        console.print()

        # Adjust duration based on passage
        if duration == 10:  # Default duration
            duration = max(duration, selected_passage.estimated_duration + 3)

    # Initialize recorder
    recorder = Recorder(recordings_dir=str(paths["recordings"]))

    # Countdown before recording
    console.print("[yellow]Get ready to record...[/yellow]")
    for i in range(3, 0, -1):
        console.print(f"[bold yellow]{i}...[/bold yellow]")
        time.sleep(1)

    console.print()
    console.print("[bold green]Recording now! Speak clearly.[/bold green]")
    console.print()

    # Show progress during recording
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}s"),
        console=console,
    ) as progress:
        task = progress.add_task("[red]Recording...", total=duration)

        # Start recording in background
        import threading
        import sounddevice as sd
        import numpy as np

        audio_data = []
        sample_rate = 44100

        def audio_callback(indata, frames, time_info, status):
            audio_data.append(indata.copy())

        stream = sd.InputStream(
            samplerate=sample_rate,
            channels=1,
            dtype=np.float32,
            callback=audio_callback,
        )

        with stream:
            for _ in range(duration):
                time.sleep(1)
                progress.update(task, advance=1)

    # Save recording
    import soundfile as sf
    from datetime import datetime

    audio_array = np.concatenate(audio_data, axis=0)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"recording_{timestamp}.wav"
    filepath = paths["recordings"] / filename
    paths["recordings"].mkdir(exist_ok=True)
    sf.write(filepath, audio_array, sample_rate)

    console.print()
    console.print(f"[green]Recording saved:[/green] {filepath}")

    # Analyze if requested
    if analyze_after:
        console.print()
        console.print("[cyan]Analyzing recording...[/cyan]")

        analyzer = VoiceAnalyzer()
        analysis = analyzer.analyze(filepath)

        _display_analysis(analysis)

        # Save to database if requested
        if save:
            db = VoiceDatabase(str(paths["database"]))
            passage_id_to_save = selected_passage.id if selected_passage else None
            db.save_analysis(analysis, passage_id=passage_id_to_save)
            console.print()
            console.print("[dim]Analysis saved to database.[/dim]")


@app.command()
def analyze(
    filename: str = typer.Argument(..., help="Path to audio file to analyze"),
    save: bool = typer.Option(False, "--save", "-s", help="Save analysis to database"),
):
    """Analyze a specific audio recording."""
    filepath = Path(filename)

    if not filepath.exists():
        # Try looking in recordings folder
        paths = get_default_paths()
        filepath = paths["recordings"] / filename
        if not filepath.exists():
            console.print(f"[red]File not found: {filename}[/red]")
            raise typer.Exit(1)

    console.print(f"[cyan]Analyzing: {filepath}[/cyan]")
    console.print()

    analyzer = VoiceAnalyzer()
    analysis = analyzer.analyze(filepath)

    _display_analysis(analysis)

    if save:
        paths = get_default_paths()
        db = VoiceDatabase(str(paths["database"]))
        db.save_analysis(analysis)
        console.print()
        console.print("[dim]Analysis saved to database.[/dim]")


@app.command()
def history(
    limit: int = typer.Option(10, "--limit", "-n", help="Number of sessions to show"),
):
    """Show history of recorded sessions and trends."""
    paths = get_default_paths()
    db = VoiceDatabase(str(paths["database"]))

    # Get statistics
    stats = db.get_statistics()

    if "error" in stats:
        console.print(f"[yellow]{stats['error']}[/yellow]")
        console.print("Record some sessions first with: voice record")
        raise typer.Exit(0)

    # Display overall stats
    console.print()
    console.print("[bold cyan]Overall Statistics[/bold cyan]")
    console.print()

    stats_table = Table(box=box.ROUNDED)
    stats_table.add_column("Metric", style="cyan")
    stats_table.add_column("Value", style="white")

    stats_table.add_row("Total Sessions", str(stats["total_sessions"]))
    stats_table.add_row("Practice Time", f"{stats['total_practice_minutes']:.1f} minutes")
    stats_table.add_row("Avg Pitch", f"{stats['avg_pitch_mean']:.1f} Hz")
    stats_table.add_row("Pitch Range (all-time)", f"{stats['lowest_pitch_ever']:.1f} - {stats['highest_pitch_ever']:.1f} Hz")
    stats_table.add_row("Avg Expressiveness", f"{stats['avg_expressiveness']:.1f}/100")

    console.print(stats_table)

    # Get trends
    console.print()
    console.print("[bold cyan]Trends (Last 14 Days)[/bold cyan]")
    console.print()

    trends = db.get_trends(days=14)

    if "error" in trends:
        console.print(f"[dim]{trends['error']} - need at least 2 sessions.[/dim]")
    else:
        trends_table = Table(box=box.ROUNDED)
        trends_table.add_column("Metric", style="cyan")
        trends_table.add_column("Earlier", style="dim")
        trends_table.add_column("Recent", style="white")
        trends_table.add_column("Change", style="white")

        metric_names = {
            "pitch_range": "Pitch Range",
            "pitch_variability_percent": "Pitch Variability",
            "expressiveness_score": "Expressiveness",
            "speaking_rate_estimate": "Speaking Rate",
        }

        for key, name in metric_names.items():
            if key in trends:
                data = trends[key]
                change = data["percent_change"]
                if change > 0:
                    change_str = f"[green]+{change:.1f}%[/green]"
                elif change < 0:
                    change_str = f"[red]{change:.1f}%[/red]"
                else:
                    change_str = "0%"

                trends_table.add_row(
                    name,
                    f"{data['earlier_avg']:.1f}",
                    f"{data['recent_avg']:.1f}",
                    change_str,
                )

        console.print(trends_table)

    # Recent sessions
    console.print()
    console.print("[bold cyan]Recent Sessions[/bold cyan]")
    console.print()

    analyses = db.get_all_analyses(limit=limit)

    if not analyses:
        console.print("[dim]No sessions recorded yet.[/dim]")
        return

    session_table = Table(box=box.ROUNDED)
    session_table.add_column("Date", style="dim")
    session_table.add_column("File", style="cyan")
    session_table.add_column("Duration", style="white")
    session_table.add_column("Pitch Range", style="white")
    session_table.add_column("Expressiveness", style="white")

    for a in analyses:
        session_table.add_row(
            a["recorded_at"][:16],
            a["filename"][:25],
            f"{a['duration_seconds']:.1f}s",
            f"{a['pitch_range']:.1f} Hz",
            f"{a['expressiveness_score']:.1f}",
        )

    console.print(session_table)


@app.command()
def compare(
    file1: str = typer.Argument(..., help="First audio file (baseline)"),
    file2: str = typer.Argument(..., help="Second audio file (comparison)"),
):
    """Compare two recordings side by side."""
    paths = get_default_paths()

    # Resolve file paths
    path1 = Path(file1)
    path2 = Path(file2)

    if not path1.exists():
        path1 = paths["recordings"] / file1
    if not path2.exists():
        path2 = paths["recordings"] / file2

    for p, name in [(path1, file1), (path2, file2)]:
        if not p.exists():
            console.print(f"[red]File not found: {name}[/red]")
            raise typer.Exit(1)

    console.print("[cyan]Analyzing both recordings...[/cyan]")
    console.print()

    analyzer = VoiceAnalyzer()
    analysis1 = analyzer.analyze(path1)
    analysis2 = analyzer.analyze(path2)

    comparison = analyzer.compare(analysis1, analysis2)

    # Display comparison table
    table = Table(
        title="Recording Comparison",
        box=box.ROUNDED,
    )
    table.add_column("Metric", style="cyan")
    table.add_column(f"Baseline\n{path1.name[:20]}", style="dim")
    table.add_column(f"Current\n{path2.name[:20]}", style="white")
    table.add_column("Change", style="white")

    display_metrics = [
        ("pitch_mean", "Pitch Mean (Hz)"),
        ("pitch_range", "Pitch Range (Hz)"),
        ("pitch_variability_percent", "Pitch Variability (%)"),
        ("chest_voice_percent", "Chest Voice (%)"),
        ("head_voice_percent", "Head Voice (%)"),
        ("intensity_mean", "Intensity Mean (dB)"),
        ("expressiveness_score", "Expressiveness"),
    ]

    for key, name in display_metrics:
        data = comparison[key]
        change = data["percent_change"]

        if change > 5:
            change_str = f"[green]+{change:.1f}%[/green]"
        elif change < -5:
            change_str = f"[red]{change:.1f}%[/red]"
        else:
            change_str = f"{change:+.1f}%"

        table.add_row(
            name,
            f"{data['baseline']:.1f}",
            f"{data['current']:.1f}",
            change_str,
        )

    console.print(table)


@app.command()
def passages(
    focus: Optional[str] = typer.Option(None, "--focus", "-f", help="Filter by focus area"),
):
    """List available practice passages."""
    all_passages = list_all_passages()

    if focus:
        all_passages = [p for p in all_passages if focus.lower() in p.focus.lower()]

    if not all_passages:
        console.print("[yellow]No passages found matching that filter.[/yellow]")
        raise typer.Exit(0)

    console.print()
    console.print("[bold cyan]Available Practice Passages[/bold cyan]")
    console.print()

    for p in all_passages:
        console.print(Panel(
            f"[white]{p.text}[/white]\n\n"
            f"[dim]Focus: {p.focus.replace('_', ' ').title()} | "
            f"~{p.estimated_duration}s[/dim]",
            title=f"[cyan]{p.title}[/cyan] [dim]({p.id})[/dim]",
            border_style="dim",
        ))
        console.print()


@app.command()
def devices():
    """List available audio input devices."""
    from .recorder import Recorder

    devices = Recorder.list_devices()

    if not devices:
        console.print("[red]No audio input devices found.[/red]")
        raise typer.Exit(1)

    console.print()
    console.print("[bold cyan]Available Audio Input Devices[/bold cyan]")
    console.print()

    table = Table(box=box.ROUNDED)
    table.add_column("ID", style="dim")
    table.add_column("Name", style="cyan")
    table.add_column("Channels", style="white")
    table.add_column("Sample Rate", style="white")

    for d in devices:
        table.add_row(
            str(d["id"]),
            d["name"],
            str(d["channels"]),
            f"{d['sample_rate']:.0f} Hz",
        )

    console.print(table)

    # Show default device
    try:
        default = Recorder.get_default_device()
        console.print()
        console.print(f"[dim]Default input device: {default['name']}[/dim]")
    except Exception:
        pass


def _display_analysis(analysis: VoiceAnalysis):
    """Display analysis results in a formatted table."""
    console.print()
    console.print(Panel(
        f"[bold]{analysis.filename}[/bold]\n"
        f"Duration: {analysis.duration_seconds}s",
        title="Analysis Results",
        border_style="cyan",
    ))

    # Pitch metrics
    pitch_table = Table(title="Pitch Analysis", box=box.ROUNDED)
    pitch_table.add_column("Metric", style="cyan")
    pitch_table.add_column("Value", style="white")

    pitch_table.add_row("Mean Pitch", f"{analysis.pitch_mean:.1f} Hz")
    pitch_table.add_row("Min Pitch", f"{analysis.pitch_min:.1f} Hz")
    pitch_table.add_row("Max Pitch", f"{analysis.pitch_max:.1f} Hz")
    pitch_table.add_row("Pitch Range", f"{analysis.pitch_range:.1f} Hz")
    pitch_table.add_row("Pitch Std Dev", f"{analysis.pitch_std:.1f} Hz")
    pitch_table.add_row("Variability", f"{analysis.pitch_variability_percent:.1f}%")

    console.print(pitch_table)

    # Voice register
    register_table = Table(title="Voice Register (Approximate)", box=box.ROUNDED)
    register_table.add_column("Register", style="cyan")
    register_table.add_column("Percentage", style="white")

    register_table.add_row("Chest Voice", f"{analysis.chest_voice_percent:.1f}%")
    register_table.add_row("Mixed Voice", f"{analysis.mixed_voice_percent:.1f}%")
    register_table.add_row("Head Voice", f"{analysis.head_voice_percent:.1f}%")

    console.print(register_table)

    # Intensity and speaking metrics
    other_table = Table(title="Intensity & Speaking", box=box.ROUNDED)
    other_table.add_column("Metric", style="cyan")
    other_table.add_column("Value", style="white")

    other_table.add_row("Mean Intensity", f"{analysis.intensity_mean:.1f} dB")
    other_table.add_row("Intensity Variation", f"{analysis.intensity_std:.1f} dB")
    other_table.add_row("Voiced Fraction", f"{analysis.voiced_fraction:.1%}")
    other_table.add_row("Speaking Rate", f"{analysis.speaking_rate_estimate:.1f} segments/s")

    console.print(other_table)

    # Expressiveness score
    score = analysis.expressiveness_score
    if score >= 70:
        score_color = "green"
        score_text = "Highly Expressive"
    elif score >= 40:
        score_color = "yellow"
        score_text = "Moderately Expressive"
    else:
        score_color = "red"
        score_text = "Low Expressiveness"

    console.print()
    console.print(Panel(
        f"[bold {score_color}]{score:.1f}/100[/bold {score_color}]\n"
        f"[dim]{score_text}[/dim]",
        title="Expressiveness Score",
        border_style=score_color,
    ))


def main():
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
