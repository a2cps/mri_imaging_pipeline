import argparse
import asyncio
import shutil
from pathlib import Path

from biomarkers.entrypoints import gift, tapismpi
from mpi4py import MPI

tapismpi.configure_mpi_logger()

# defined in Dockerfile
CONFIGS = {
    "neuromark_fmri_2.1_modelorder-multi": Path(
        "/opt/gift/config_neuromark_fmri_2.1_modelorder-multi.m"
    ),
    "neuromark_fmri_2.0_modelorder-175": Path(
        "/opt/gift/config_neuromark_fmri_2.0_modelorder-175.m"
    ),
}


async def main(
    fmriprep: list[Path],
    outdirs: list[Path],
    voxel_size: float = 2.0,
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
            "*anat*",
            "*MNI152NLin2009cAsym_desc-preproc_bold*",  # this is another form of "res-native"
            "*sourcedata*",  # to exclude freesurfer
            "*fmap*",
        ),
        voxel_size=voxel_size,
        smooth_fwhm=smooth_fwhm,
    ).run()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dirs", nargs="+", type=Path, required=True)
    parser.add_argument("--output-dirs", nargs="+", type=Path)
    parser.add_argument("--voxel-size", type=float, default=2.0)
    parser.add_argument("--smooth-fwhm", type=float, default=6.0)

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
                    ).replace("/fmriprep/", "/gift/")
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
            fmriprep=args.input_dirs,
            outdirs=output_dirs,
            smooth_fwhm=args.smooth_fwhm,
            voxel_size=args.voxel_size,
        )
    )
