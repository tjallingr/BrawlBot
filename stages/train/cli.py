import click
from data.features.dataset import compile_dataset, write_dataset

@click.group()
def cli():
    pass

@cli.command("compile")
def create_dataset():
    print("creating dataset")
    dataset = compile_dataset()
    write_dataset(dataset, "data/sets/fights.parquet")
    print("wrote dataset")

