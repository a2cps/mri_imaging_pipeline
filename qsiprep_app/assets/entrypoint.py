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
QSIPREP_CONFIG = Path("/opt/qsiprep_app/qsiprep.toml")

PRODUCTS = Path("/corral-secure/projects/A2CPS/products/mris")


class QSIPRepEntrypoint(qsiprep.QSIPRepEntrypoint):
    # qsiprep >= 26.1 deletes node outputs that no downstream node consumes,
    # including the eddy outputs that eddy_quad reads, so pass a config that
    # keeps them
    config_file: Path = QSIPREP_CONFIG

    def get_args(self, bidsdir: Path, outdir: Path, work_dir: Path) -> list[str]:
        args = super().get_args(bidsdir=bidsdir, outdir=outdir, work_dir=work_dir)
        return [*args, "--config-file", str(self.config_file)]


def get_output_dirs(input_dirs: typing.Sequence[Path], job: str) -> list[Path]:
    # e.g., {PRODUCTS}/NS_northshore/bids/NS10001V1 -> NS_northshore/{job}/NS10001V1
    return [
        Path(str(Path(input_dir).relative_to(PRODUCTS)).replace("/bids/", f"/{job}/"))
        for input_dir in input_dirs
    ]


async def main(
    bids_directory: typing.Sequence[Path],
    outdirs: typing.Sequence[Path],
    n_workers: int | None = None,
    mem_mb: int | None = None,
    unringing_method: str = "mrdegibbs",
    denoise_method: str = "patch2self",
) -> None:
    await QSIPRepEntrypoint(
        outs=outdirs,
        ins=bids_directory,
        eddy_params=EDDY_PARAMS,
        n_workers=n_workers,
        mem_mb=mem_mb,
        stage_ignore_patterns=shutil.ignore_patterns(
            "*sourcedata*", "*func*", "*scans.tsv", "*scans.json", "*fmrib0*"
        ),
        unringing_method=unringing_method,
        denoise_method=denoise_method,
    ).run()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dirs", nargs="+", type=Path, required=True)
    parser.add_argument("--output-dirs", nargs="+", type=Path)
    parser.add_argument("--n-workers", type=int, default=None)
    parser.add_argument("--mem-mb", type=int, default=None)
    parser.add_argument("--unringing-method", type=str, default="mrdegibbs")
    parser.add_argument("--denoise-method", type=str, default="patch2self")
    parser.add_argument("--job", type=str, default="qsiprep-v4")

    args = parser.parse_args()
    usize = MPI.COMM_WORLD.Get_size()

    if args.output_dirs is None:
        output_dirs = get_output_dirs(args.input_dirs, args.job)
    else:
        output_dirs = args.output_dirs

    if (n_input := len(args.input_dirs)) != usize:
        msg = f"Length of input_dirs must equal usize but found {n_input=}, {usize=}"
        raise AssertionError(msg)

    if (n_output := len(output_dirs)) != usize:
        msg = f"Length of output_dirs must equal usize but found {n_output=}, {usize=}"
        raise AssertionError(msg)

    if len(output_dirs) != len(set(output_dirs)):
        msg = "Output directories must be unique"
        raise AssertionError(msg)

    asyncio.run(
        main(
            bids_directory=args.input_dirs,
            outdirs=output_dirs,
            n_workers=args.n_workers,
            mem_mb=args.mem_mb,
            unringing_method=args.unringing_method,
            denoise_method=args.denoise_method,
        )
    )
