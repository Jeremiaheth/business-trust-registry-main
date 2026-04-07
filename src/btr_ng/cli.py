"""Command-line interface for BTR-NG."""

from __future__ import annotations

import typer

from btr_ng import __version__

app = typer.Typer(
    add_completion=False,
    help="BTR-NG developer CLI.",
    no_args_is_help=True,
)


@app.callback()
def main_callback() -> None:
    """Provide a group entrypoint so commands remain explicit subcommands."""


@app.command("version")
def version() -> None:
    """Print the installed package version."""
    typer.echo(__version__)


def main() -> None:
    """Run the CLI application."""
    app()


if __name__ == "__main__":
    main()
