import argparse
import asyncio
import shutil
import typing
from pathlib import Path

from biomarkers.entrypoints import cat, tapismpi
from mpi4py import MPI

tapismpi.configure_mpi_logger()


async def main(
    bids_directory: typing.Sequence[Path], outdirs: typing.Sequence[Path]
) -> None:
    await cat.CATEntrypoint(
        outs=outdirs,
        ins=bids_directory,
        stage_ignore_patterns=shutil.ignore_patterns(
            "*.heudiconv", "sourcedata", "func", "dwi", "fmap"
        ),
    ).run()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dirs", nargs="+", type=Path, required=True)
    parser.add_argument("--output-dirs", nargs="+", type=Path)
    parser.add_argument("--project-dir", type=Path)

    args = parser.parse_args()
    usize = MPI.COMM_WORLD.Get_size()

    if args.output_dirs is None:
        output_dirs = []
        for input_dir in args.input_dirs:
            output_dirs.append(
                Path(
                    str(
                        Path(input_dir).relative_to(
                            "/corral-secure/projects/A2CPS/products/mris"
                        )
                    ).replace("/bids/", "/cat12-v4/")
                )
            )
    else:
        output_dirs = args.output_dirs

    if not (n_input := len(args.input_dirs)) == usize:
        msg = f"Length of input_dirs must equal usize but found {n_input=}, {usize=}"
        raise AssertionError(msg)

    if not (n_output := len(output_dirs)) == usize:
        msg = f"Length of output_dirs must equal usize but found {n_output=}, {usize=}"
        raise AssertionError(msg)

    if not len(output_dirs) == len(set(output_dirs)):
        msg = "Output directories must be unique"
        raise AssertionError(msg)

    if args.project_dir is not None:
        input_dirs = [args.project_dir / input_dir for input_dir in args.input_dirs]
        output_dirs = [args.project_dir / output_dir for output_dir in output_dirs]
    else:
        input_dirs = [input_dir for input_dir in args.input_dirs]

    asyncio.run(main(bids_directory=input_dirs, outdirs=output_dirs))
