import typer

app = typer.Typer(name="rig")


@app.command()
def validate():
    """Validate the rig configuration."""
    typer.echo("validate: not yet implemented")


@app.command()
def plan():
    """Preview changes needed to reach desired state."""
    typer.echo("plan: not yet implemented")


@app.command()
def apply():
    """Apply changes to reach desired state."""
    typer.echo("apply: not yet implemented")


@app.command()
def status():
    """Show current rig state."""
    typer.echo("status: not yet implemented")


@app.command()
def diff():
    """Show differences between config versions."""
    typer.echo("diff: not yet implemented")


if __name__ == "__main__":
    app()
