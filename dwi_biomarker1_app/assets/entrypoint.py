import argparse
import asyncio
from pathlib import Path

from biomarkers.entrypoints import dwi_biomarker1, tapismpi
from mpi4py import MPI

tapismpi.configure_mpi_logger()


async def main(
    qsiprep: list[Path],
    outdirs: list[Path],
    participant_labels: list[str],
    ses_labels: list[str],
    bedpostx_dirs: list[Path],
    n_workers: int = 1,
    roi_dir: Path = Path("/opt/tapis/rois"),
) -> None:
    await dwi_biomarker1.DWIBiomarker1Entrypoint(
        outs=outdirs,
        ins=qsiprep,
        participant_label=participant_labels,
        bedpostxdir=bedpostx_dirs,
        ses_label=ses_labels,
        n_workers=n_workers,
        roi_dir=roi_dir,
    ).run()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dirs", nargs="+", type=Path, required=True)
    parser.add_argument("--participant-labels", nargs="+", required=True)
    parser.add_argument("--ses-labels", nargs="+", required=True)
    parser.add_argument("--output-dirs", nargs="+", type=Path)
    parser.add_argument("--bedpostx-dirs", nargs="+", type=Path)
    parser.add_argument("--n-workers", type=int, default=1)

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
                    ).replace("/qsiprep/", "/dwi_biomarker1/")
                ).parent
            )
    else:
        output_dirs = args.output_dirs

    if args.bedpostx_dirs is None:
        bedpostx_dirs = []
        for input_dir in args.input_dirs:
            bedpostx_dirs.append(
                Path(
                    str(
                        Path(input_dir).relative_to(
                            "/corral-secure/projects/A2CPS/products/mris"
                        )
                    ).replace("qsiprep", "bedpostx")
                )
            )
    else:
        bedpostx_dirs = args.bedpostx_dirs

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

    if not (n_bedpostx := len(bedpostx_dirs)) == usize:
        msg = f"Length of bedpostx_dirs must equal usize but found {n_bedpostx=}, {usize=}"
        raise AssertionError(msg)

    if not len(output_dirs) == len(set(output_dirs)):
        msg = "Output directories must be unique"
        raise AssertionError(msg)

    asyncio.run(
        main(
            qsiprep=args.input_dirs,
            outdirs=output_dirs,
            participant_labels=args.participant_labels,
            bedpostx_dirs=bedpostx_dirs,
            ses_labels=args.ses_labels,
            n_workers=args.n_workers,
        )
    )
