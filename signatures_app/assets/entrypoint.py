import argparse
import asyncio
import shutil
from pathlib import Path

from biomarkers.entrypoints import signatures, tapismpi
from mpi4py import MPI

tapismpi.configure_mpi_logger()


async def main(fmriprep: list[Path], outdirs: list[Path]) -> None:
    await signatures.SignatureEntrypoint(
        outs=outdirs,
        ins=fmriprep,
        stage_ignore_patterns=shutil.ignore_patterns(
            "*log*",
            "*figures*",
            "*den-91k*",
            "*gii",
            "*txt",
            "*h5",
            "*MNI152NLin2009cAsym*",
            "*fsLR*",
            "*html",
            "*anat*",
            "*MNI152NLin6Asym_desc-preproc_bold*",  # this is another form of "res-native"
            "*sourcedata*",  # to exclude freesurfer
            "*fmap*",
        ),
        n_non_steady_state_tr=15,
        low_pass=0.1,
        detrend=True,
        winsorize=True,
        compcor_label="WM+CSF",
    ).run()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dirs", nargs="+", type=Path, required=True)
    parser.add_argument("--output-dirs", nargs="+", type=Path)

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
                    ).replace("/fmriprep/", "/signatures/")
                ).parent
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

    asyncio.run(main(fmriprep=args.input_dirs, outdirs=output_dirs))
