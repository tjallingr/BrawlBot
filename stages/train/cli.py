import click
from data.features.dataset import compile_dataset, write_dataset

@click.group()
def cli():
    pass

@cli.command("compile")
@click.option("--min-fights", type=int, default=2, help="Skip bouts where either fighter has fewer prior fights.")
def compile_set(min_fights: int):
    frame = compile_dataset(get_session(get_engine()), min_fights=min_fights)
    path = write_dataset(frame)
    click.echo(f"wrote {path} ({len(frame)} rows x {frame.shape[1]} columns)")

if __name__ == "__main__":
    cli()
