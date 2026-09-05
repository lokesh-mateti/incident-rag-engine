"""CLI for the Incident RAG Engine — ingest data and query interactively."""

from __future__ import annotations

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from src.ingestion.chunker import chunk_documents
from src.ingestion.loader import load_incidents
from src.retrieval import chain
from src.retrieval.vectorstore import ingest, reset

app = typer.Typer(help="Incident Resolution RAG Engine")
console = Console()


@app.command()
def ingest_cmd(
    force: bool = typer.Option(False, "--force", "-f", help="Drop collection first"),
) -> None:
    """Load incidents from data/ and ingest into ChromaDB."""
    if force:
        reset()
        console.print("[yellow]Collection reset.[/yellow]")
    docs = load_incidents()
    console.print(f"Loaded {len(docs)} incident files.")
    chunks = chunk_documents(docs)
    n = ingest(chunks)
    console.print(f"[green]Ingested {n} chunks into ChromaDB.[/green]")


@app.command()
def ask(
    question: str = typer.Argument(..., help="Operational question"),
    k: int = typer.Option(5, "--k", "-k", help="Number of chunks to retrieve"),
) -> None:
    """Ask a single question and get a grounded answer."""
    result = chain.query(question, k=k)
    console.print(Panel(Markdown(result.answer), title="Answer", border_style="green"))
    if result.sources:
        console.print("\n[dim]Sources:[/dim]")
        seen: set[str] = set()
        for doc in result.sources:
            src = doc.metadata.get("source", "unknown")
            if src not in seen:
                sev = doc.metadata.get("severity", "")
                label = f"  • {src}"
                if sev:
                    label += f"  (severity: {sev})"
                console.print(label)
                seen.add(src)


@app.command()
def chat() -> None:
    """Interactive REPL — ask questions until you type 'exit'."""
    console.print(
        Panel(
            "Incident RAG Engine — interactive mode\nType [bold]exit[/bold] to quit.",
            border_style="blue",
        )
    )
    while True:
        try:
            question = console.input("[bold cyan]query>[/bold cyan] ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not question or question.lower() in {"exit", "quit", "q"}:
            break
        result = chain.query(question)
        console.print(Panel(Markdown(result.answer), title="Answer", border_style="green"))


if __name__ == "__main__":
    app()
