import argparse
import asyncio
import shutil
import typing
from pathlib import Path

from biomarkers.entrypoints import fmriprep, tapismpi
from biomarkers.models import fmriprep as fmriprep_models
from mpi4py import MPI

tapismpi.configure_mpi_logger()

# defined in Dockerfile
SYNTHSTRIP_MODEL = Path("/opt/synthstrip.1.pt")
FS_LICENSE = Path("/opt/fmriprep_app/license.txt")


async def main(
    bids_directory: typing.Sequence[Path],
    outdirs: typing.Sequence[Path],
    n_workers: int | None = None,
    mem_mb: int | None = None,
    cifti_output: fmriprep_models.CIFTI_OUTPUT = "91k",
    dummy_scans: int | None = None,
    bold2anat_dof: fmriprep_models.BOLD2ANAT_DOF = 6,
    output_spaces: typing.Sequence[fmriprep_models.OUTPUT_SPACE] = (
        typing.get_args(fmriprep_models.OUTPUT_SPACE)
    ),
) -> None:
    await fmriprep.FMRIPRepEntrypoint(
        outs=outdirs,
        ins=bids_directory,
        fs_license_file=FS_LICENSE,
        synthstrip_model=SYNTHSTRIP_MODEL,
        n_workers=n_workers,
        mem_mb=mem_mb,
        cifti_output=cifti_output,
        dummy_scans=dummy_scans,
        bold2anat_dof=bold2anat_dof,
        output_spaces=output_spaces,
        stage_ignore_patterns=shutil.ignore_patterns(
            "*.heudiconv", "sourcedata"
        ),
    ).run()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dirs", nargs="+", type=Path, required=True)
    parser.add_argument("--output-dirs", nargs="+", type=Path)
    parser.add_argument("--n-workers", type=int, default=None)
    parser.add_argument("--mem-mb", type=int, default=None)
    parser.add_argument(
        "--cifti-output",
        type=str,
        choices=typing.get_args(fmriprep_models.CIFTI_OUTPUT),
        default="91k",
    )
    parser.add_argument("--dummy-scans", type=int, default=None)
    parser.add_argument(
        "--bold2anat-dof",
        choices=typing.get_args(fmriprep_models.BOLD2ANAT_DOF),
        default=6,
    )
    parser.add_argument(
        "--output-spaces",
        nargs="+",
        choices=typing.get_args(fmriprep_models.OUTPUT_SPACE),
        default=typing.get_args(fmriprep_models.OUTPUT_SPACE),
    )

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
                    ).replace("/bids/", "/fmriprep/")
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
            cifti_output=args.cifti_output,
            dummy_scans=args.dummy_scans,
            bold2anat_dof=args.bold2anat_dof,
            output_spaces=args.output_spaces,
        )
    )
