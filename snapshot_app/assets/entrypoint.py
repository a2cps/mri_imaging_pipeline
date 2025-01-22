import argparse
import logging
import socket
from pathlib import Path

from snapshot.flows import copy_to_dst_wf
from snapshot.models import jobs

host = socket.gethostname()
logging.basicConfig(
    format=f"%(asctime)s | %(levelname)-8s | {host=} | %(message)s",
    level=logging.INFO,
    force=True,
)


def main(inroot: Path, outroot: Path, job: jobs.STORE_DIR, n_workers: int = 1) -> None:
    logging.info("making initial copy")
    copy_to_dst_wf.main(
        inroot=inroot, outroot=outroot, max_workers=n_workers, jobs_to_copy=[job]
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--inroot", type=Path, required=True)
    parser.add_argument("--outroot", type=Path, required=True)
    parser.add_argument(
        "--job",
        choices=(
            "bids",
            "brainager",
            "cat12",
            "eddyqc",
            "fcn",
            "fmriprep",
            "freesurfer",
            "fslanat",
            "gift",
            "mriqc",
            "qsiprep-V1",
            "signatures",
        ),
        required=True,
    )
    parser.add_argument("--n-workers", type=int, default=1)

    args = parser.parse_args()
    main(**vars(args))
