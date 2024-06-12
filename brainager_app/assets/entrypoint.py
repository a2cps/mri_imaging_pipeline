import argparse
import asyncio
import shutil
from pathlib import Path


from biomarkers.entrypoints import tapismpi, brainager
from mpi4py import MPI

tapismpi.configure_mpi_logger()


async def main(input_dirs: list[Path], output_dirs: list[Path]) -> None:
    await brainager.BrainagerEntrypoint(
        ins=input_dirs,
        outs=output_dirs,
        stage_ignore_patterns=shutil.ignore_patterns(
            "*tsv",
            "*heudiconv*",
            "*sourcedata*",
            "*func*",
            "*json",
            "*dwi*",
            "*fmap*",
        ),
    ).run()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dirs", nargs="+", type=Path, required=True)
    parser.add_argument("--output-dirs", nargs="+", type=Path, required=True)

    args = parser.parse_args()
    usize = MPI.COMM_WORLD.Get_size()

    if not (n_input := len(args.input_dirs)) == usize:
        msg = f"Length of input-dirs must equal usize but found {n_input=}, {usize=}"
        raise AssertionError(msg)

    if not (n_output := len(args.output_dirs)) == usize:
        msg = f"Length of output-dirs must equal usize but found {n_output=}, {usize=}"
        raise AssertionError(msg)

    if not len(args.output_dirs) == len(set(args.output_dirs)):
        msg = "Output directories must be unique"
        raise AssertionError(msg)

    asyncio.run(main(input_dirs=args.input_dirs, output_dirs=args.output_dirs))
