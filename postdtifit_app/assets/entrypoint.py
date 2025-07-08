import argparse
import asyncio
import re
import shutil
from pathlib import Path

from biomarkers.entrypoints import postdtifit, tapismpi
from mpi4py import MPI

tapismpi.configure_mpi_logger()


async def main(
    ins: list[Path],
    outs: list[Path],
    qsipreps: list[Path],
    participant_labels: list[str],
    ses_labels: list[str],
) -> None:
    await postdtifit.PostDTIFitEntrypoint(
        outs=outs,
        ins=ins,
        qsiprepdir=qsipreps,
        participant_label=participant_labels,
        ses_label=ses_labels,
        stage_ignore_patterns=shutil.ignore_patterns(
            "*b3000*", "*b2000*", "*split_shells*", "log*", "figures", "*html"
        ),
    ).run()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dirs", nargs="+", type=Path, required=True)
    parser.add_argument("--output-dirs", nargs="+", type=Path)
    parser.add_argument("--qsiprep-dirs", nargs="+", type=Path)
    parser.add_argument("--participant-labels", nargs="+")
    parser.add_argument("--ses-labels", nargs="+")
    parser.add_argument(
        "--mris", type=Path, default=Path("/corral-secure/projects/A2CPS/products/mris")
    )

    args = parser.parse_args()
    usize = MPI.COMM_WORLD.Get_size()

    if args.output_dirs is None:
        output_dirs = []
        for input_dir in args.input_dirs:
            output_dirs.append(
                Path(
                    str(Path(input_dir).relative_to(args.mris))
                    .replace("qsirecon_fsl_dtifit", "postdtifit")
                    .replace("/dtifit", "/postdtifit")
                ).parent
            )
    else:
        output_dirs = args.output_dirs

    if args.participant_labels is None:
        participant_labels = [re.findall(r"\d{5}", str(x))[0] for x in args.input_dirs]
    else:
        participant_labels = args.participant_labels

    if args.ses_labels is None:
        ses_labels = [re.findall("V[13]", str(x))[0] for x in args.input_dirs]
    else:
        ses_labels = args.ses_labels

    if args.qsiprep_dirs is None:
        qsiprep_dirs = []
        for input_dir in args.input_dirs:
            qsiprep_dirs.append(
                Path(
                    str(input_dir)
                    .replace("qsirecon_fsl_dtifit", "qsiprep")
                    .replace("dtifit", "qsiprep")
                )
            )
    else:
        qsiprep_dirs = args.qsiprep_dirs

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
            ins=args.input_dirs,
            outs=output_dirs,
            participant_labels=participant_labels,
            ses_labels=ses_labels,
            qsipreps=qsiprep_dirs,
        )
    )
