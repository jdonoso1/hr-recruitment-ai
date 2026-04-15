from __future__ import annotations

"""
HR Platform CLI
Usage:
    hr run   --job-file job.json --cv-dir ./cvs [options]
    hr serve [--host 0.0.0.0] [--port 8000]
    hr init-db
"""

import json
import sys
from pathlib import Path

import click
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env")

from .db.database import init_db, save_client
from .models.schema import Client, Job
from .orchestrator import run_full_workflow


def _observer(stage: str, msg: str) -> None:
    click.echo(f"  [{stage}] {msg}")


@click.group()
def cli():
    """HR Intelligence Platform — AI-powered hiring pipeline."""


@cli.command("init-db")
@click.option("--migrations", default=None, help="Path to SQL migration file")
def cmd_init_db(migrations: str | None):
    """Initialize (or migrate) the database."""
    init_db(migrations)
    click.echo("Database initialized.")


@cli.command("run")
@click.option("--job-file", required=True, type=click.Path(exists=True), help="JSON file with Job fields")
@click.option("--cv-dir", default=None, type=click.Path(exists=True), help="Directory of PDF CVs to ingest")
@click.option("--linkedin-file", default=None, type=click.Path(exists=True), help="File with LinkedIn profile texts (one per --- separator)")
@click.option("--transcripts-file", default=None, type=click.Path(exists=True), help="JSON file {candidate_id: transcript_text}")
@click.option("--client-name", default="Client", help="HR firm / client display name")
@click.option("--output-dir", default=".", show_default=True, help="Where to save the .pptx report")
def cmd_run(
    job_file: str,
    cv_dir: str | None,
    linkedin_file: str | None,
    transcripts_file: str | None,
    client_name: str,
    output_dir: str,
):
    """Run the full HR pipeline for a job."""
    # Load job
    job_data = json.loads(Path(job_file).read_text())
    job = Job(**job_data)

    # Collect CV paths
    cv_paths: list[str] = []
    if cv_dir:
        cv_paths = [str(p) for p in Path(cv_dir).glob("*.pdf")]
        if not cv_paths:
            click.echo(f"Warning: no PDF files found in {cv_dir}", err=True)

    # Collect LinkedIn profile texts
    linkedin_profiles: list[str] = []
    if linkedin_file:
        raw = Path(linkedin_file).read_text()
        linkedin_profiles = [s.strip() for s in raw.split("---") if s.strip()]

    # Transcripts
    transcripts: dict[str, str] = {}
    if transcripts_file:
        transcripts = json.loads(Path(transcripts_file).read_text())

    if not cv_paths and not linkedin_profiles:
        click.echo("Error: provide --cv-dir and/or --linkedin-file.", err=True)
        sys.exit(1)

    click.echo(f"\nStarting HR pipeline for: {job.title} @ {job.company}")
    click.echo(f"  CVs: {len(cv_paths)}  LinkedIn: {len(linkedin_profiles)}\n")

    result = run_full_workflow(
        job=job,
        cv_paths=cv_paths,
        linkedin_profiles=linkedin_profiles,
        transcripts=transcripts,
        client_name=client_name,
        output_dir=output_dir,
        observer=_observer,
    )

    click.echo("\n─── Results ───────────────────────────────")
    click.echo(f"  Candidates processed : {result.kpi.candidates_processed}")
    click.echo(f"  Candidates screened  : {result.kpi.candidates_screened}")
    click.echo(f"  Interviews generated : {result.kpi.candidates_interviewed}")
    click.echo(f"  Hours saved (est.)   : {result.kpi.hours_saved_estimate:.1f}")
    if result.report_path:
        click.echo(f"  Report               : {result.report_path}")
    if result.errors:
        click.echo("\n  Errors:")
        for e in result.errors:
            click.echo(f"    - {e}", err=True)

    click.echo("\nDone.")


@cli.command("serve")
@click.option("--host", default="127.0.0.1", show_default=True)
@click.option("--port", default=8000, show_default=True)
@click.option("--reload", is_flag=True, default=False)
def cmd_serve(host: str, port: int, reload: bool):
    """Start the FastAPI development server."""
    try:
        import uvicorn
    except ImportError:
        click.echo("uvicorn is required: pip install uvicorn", err=True)
        sys.exit(1)

    click.echo(f"Starting HR API at http://{host}:{port}")
    uvicorn.run(
        "hr_platform.api:app",
        host=host,
        port=port,
        reload=reload,
    )


@cli.command("create-client")
@click.option("--name", required=True)
@click.option("--email", default=None)
@click.option("--plan", default="starter", type=click.Choice(["starter", "pro", "enterprise"]))
def cmd_create_client(name: str, email: str | None, plan: str):
    """Create a new client record in the database."""
    init_db()
    client = Client(name=name, email=email, plan=plan)
    save_client(client)
    click.echo(f"Client created: {client.client_id}  ({name})")


def main():
    cli()
