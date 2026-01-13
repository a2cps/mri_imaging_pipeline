import argparse
import logging
import socket
import typing
from pathlib import Path

from snapshot.flows import copy_to_dst_wf
from snapshot.models import jobs

host = socket.gethostname()
logging.basicConfig(
    format=f"%(asctime)s | %(levelname)-8s | {host=} | %(message)s",
    level=logging.INFO,
    force=True,
)

ALL_JOBS = [
    "bedpostx",
    "bids",
    "brainager",
    "cat12",
    "dwi_biomarker1",
    "eddyqc",
    "fcn",
    "fmriprep",
    "freesurfer",
    "fslanat",
    "gift",
    "mriqc",
    "postdtifit",
    "postgift",
    "qsiprep-V1",
    "qsirecon_fsl_dtifit",
    "signatures",
    "synthstrip",
]


def main(
    inroot: Path,
    outroot: Path,
    job: typing.Sequence[jobs.STORE_DIR],
    n_workers: int = 1,
) -> None:
    logging.info("making initial copy")
    copy_to_dst_wf.main(
        inroot=inroot, outroot=outroot, max_workers=n_workers, jobs_to_copy=job
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--inroot", type=Path, required=True)
    parser.add_argument("--outroot", type=Path, required=True)
    parser.add_argument(
        "--job", choices=ALL_JOBS, required=False, nargs="+", default=ALL_JOBS
    )
    parser.add_argument("--n-workers", type=int, default=1)

    args = parser.parse_args()
    main(**vars(args))
