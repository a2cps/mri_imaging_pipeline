import argparse
import asyncio
import re
from pathlib import Path

from biomarkers.entrypoints import bedpostx, tapismpi
from mpi4py import MPI

tapismpi.configure_mpi_logger()


async def main(
    qsirecon: list[Path],
    outdirs: list[Path],
    participant_labels: list[str],
    ses_labels: list[str],
) -> None:
    await bedpostx.BEDPOSTXEntrypoint(
        outs=outdirs,
        ins=qsirecon,
        participant_label=participant_labels,
        ses_label=ses_labels,
    ).run()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dirs", nargs="+", type=Path, required=True)
    parser.add_argument("--output-dirs", nargs="+", type=Path)
    parser.add_argument("--participant-labels", nargs="+")
    parser.add_argument("--ses-labels", nargs="+")

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
                    ).replace("/qsirecon_fsl_dtifit/", "/bedpostx/")
                ).parent.parent.parent
            )
    else:
        output_dirs = args.output_dirs

    if args.participant_labels is None:
        participant_labels = [
            "sub-" + re.findall(r"\d{5}", str(input_dir))[0]
            for input_dir in args.input_dirs
        ]
    else:
        participant_labels = args.participant_labels

    if args.ses_labels is None:
        ses_labels = [
            "ses-" + re.findall(r"V[13]", str(input_dir))[0]
            for input_dir in args.input_dirs
        ]
    else:
        ses_labels = args.ses_labels

    if not (n_input := len(args.input_dirs)) == usize:
        msg = f"Length of input_dirs must equal usize but found {n_input=}, {usize=}"
        raise AssertionError(msg)

    if not (n_output := len(output_dirs)) == usize:
        msg = f"Length of output_dirs must equal usize but found {n_output=}, {usize=}"
        raise AssertionError(msg)

    if not (n_sub := len(participant_labels)) == usize:
        msg = f"Length of participant_labels must equal usize but found {n_sub=}, {usize=}"
        raise AssertionError(msg)

    if not (n_ses := len(ses_labels)) == usize:
        msg = f"Length of ses_labels must equal usize but found {n_ses=}, {usize=}"
        raise AssertionError(msg)

    if not len(output_dirs) == len(set(output_dirs)):
        msg = "Output directories must be unique"
        raise AssertionError(msg)

    asyncio.run(
        main(
            qsirecon=args.input_dirs,
            outdirs=output_dirs,
            participant_labels=participant_labels,
            ses_labels=ses_labels,
        )
    )
