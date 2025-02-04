import argparse
import asyncio
from pathlib import Path

from biomarkers.entrypoints import dtifit, tapismpi
from mpi4py import MPI

tapismpi.configure_mpi_logger()


async def main(
    qsiprep: list[Path],
    outdirs: list[Path],
    participant_labels: list[str],
    ses_labels: list[str],
) -> None:
    await dtifit.DTIFitEntrypoint(
        outs=outdirs,
        ins=qsiprep,
        fs_license_file=Path("/opt/qsirecon_app/license"),
        participant_label=participant_labels,
        ses_label=ses_labels,
    ).run()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dirs", nargs="+", type=Path, required=True)
    parser.add_argument("--output-dirs", nargs="+", type=Path)
    parser.add_argument("--participant-labels", nargs="+", required=True)
    parser.add_argument("--ses-labels", nargs="+", required=True)

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
                    ).replace("/qsiprep/", "/qsirecon-fsl-dtifit/")
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

    if not (n_sub := len(args.participant_labels)) == usize:
        msg = f"Length of participant_labels must equal usize but found {n_sub=}, {usize=}"
        raise AssertionError(msg)

    if not (n_ses := len(args.ses_labels)) == usize:
        msg = f"Length of ses_labels must equal usize but found {n_ses=}, {usize=}"
        raise AssertionError(msg)

    if not len(output_dirs) == len(set(output_dirs)):
        msg = "Output directories must be unique"
        raise AssertionError(msg)

    asyncio.run(
        main(
            qsiprep=args.input_dirs,
            outdirs=output_dirs,
            participant_labels=args.participant_labels,
            ses_labels=args.ses_labels,
        )
    )
