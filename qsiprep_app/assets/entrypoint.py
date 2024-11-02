import argparse
import asyncio
import shutil
import typing
from pathlib import Path

from biomarkers.entrypoints import qsiprep, tapismpi
from mpi4py import MPI

tapismpi.configure_mpi_logger()

# determined by Dockerfile
EDDY_PARAMS = Path("/opt/qsiprep_app/eddy_params.json")
FS_LICENSE = Path("/opt/qsiprep_app/license.txt")


async def main(
    bids_directory: typing.Sequence[Path],
    outdirs: typing.Sequence[Path],
    n_workers: int | None = None,
    mem_mb: int | None = None,
) -> None:
    await qsiprep.QSIPRepEntrypoint(
        outs=outdirs,
        ins=bids_directory,
        fs_license_file=FS_LICENSE,
        eddy_params=EDDY_PARAMS,
        n_workers=n_workers,
        mem_mb=mem_mb,
        stage_ignore_patterns=shutil.ignore_patterns(
            "*sourcedata*", "*func*", "*scans.tsv", "*scans.json", "*fmrib0*"
        ),
    ).run()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dirs", nargs="+", type=Path, required=True)
    parser.add_argument("--output-dirs", nargs="+", type=Path)
    parser.add_argument("--n-workers", type=int, default=None)
    parser.add_argument("--mem-mb", type=int, default=None)

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
                    ).replace("/bids/", "/qsiprep/")
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

    asyncio.run(
        main(
            bids_directory=args.input_dirs,
            outdirs=output_dirs,
            n_workers=args.n_workers,
            mem_mb=args.mem_mb,
        )
    )
