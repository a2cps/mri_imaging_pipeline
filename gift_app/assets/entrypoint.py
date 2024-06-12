import argparse
import asyncio
import shutil
from pathlib import Path

from biomarkers.entrypoints import gift, tapismpi
from mpi4py import MPI

tapismpi.configure_mpi_logger()

# defined in Dockerfile
CONFIGS = {
    "neuromark_fmri_2.1_modelorder-multi": Path("/opt/gift/config_neuromark_fmri_2.1_modelorder-multi.m"),
    "neuromark_fmri_2.0_modelorder-175": Path("/opt/gift/config_neuromark_fmri_2.0_modelorder-175.m"),
}


async def main(
    fmriprep: list[Path],
    outdirs: list[Path],
    voxel_size: float = 2.4,
    smooth_fwhm: float = 6.0,
) -> None:
    await gift.GIFTEntrypoint(
        outs=outdirs,
        ins=fmriprep,
        configs=CONFIGS,
        stage_ignore_patterns=shutil.ignore_patterns(
            "*sv",
            "*log*",
            "*figures*",
            "*series*",
            "*gii",
            "*txt",
            "*h5",
            "*mask*",
            "*seg*",
            "*MNI152NLin6Asym*",
            "*boldref*",
            "*fsLR*",
            "*html",
            "*anat*"
        ),
        voxel_size=voxel_size,
        smooth_fwhm=smooth_fwhm,
    ).run()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dirs", nargs="+", type=Path, required=True)
    parser.add_argument("--output-dirs", nargs="+", type=Path, required=True)
    parser.add_argument("--voxel-size", type=float, default=2.4)
    parser.add_argument("--smooth-fwhm", type=float, default=6.0)

    args = parser.parse_args()
    usize = MPI.COMM_WORLD.Get_size()

    if not (n_input := len(args.input_dirs)) == usize:
        msg = f"Length of input_dirs must equal usize but found {n_input=}, {usize=}"
        raise AssertionError(msg)

    if not (n_output := len(args.output_dirs)) == usize:
        msg = f"Length of output_dirs must equal usize but found {n_output=}, {usize=}"
        raise AssertionError(msg)

    if not len(args.output_dirs) == len(set(args.output_dirs)):
        msg = "Output directories must be unique"
        raise AssertionError(msg)

    asyncio.run(
        main(
            fmriprep=args.input_dirs,
            outdirs=args.output_dirs,
            smooth_fwhm=args.smooth_fwhm,
            voxel_size=args.voxel_size,
        )
    )
