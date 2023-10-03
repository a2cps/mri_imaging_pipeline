import argparse
import logging
from pathlib import Path

from snapshot.flows import (
    add_ria_wf,
    archive_wf,
    copy_v1_to_dst_wf,
    init_datalad_wf,
)

logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s", level=logging.INFO
)


def main(
    inroot: Path,
    outroot: Path,
    riadir: Path,
    n_workers: int = 1,
    copy: bool = False,
    init_datalad: bool = False,
    archive: bool = False,
) -> None:
    if copy:
        logging.info("making initial copy")
        copy_v1_to_dst_wf.main(inroot=inroot, outroot=outroot)

    if init_datalad:
        logging.info("initializing datalad")
        init_datalad_wf.main(inroot=outroot, n_jobs=n_workers)

    if archive:
        ria = f"ria+file://{riadir.resolve()}"
        logging.info(f"configuring ria at {ria=}")
        add_ria_wf.main(releasedir=outroot, ria=ria)

        logging.info("archiving to ria")
        archive_wf.main(releasedir=outroot, ria=riadir, n_jobs=n_workers)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--inroot", type=Path, required=True)
    parser.add_argument("--outroot", type=Path, required=True)
    parser.add_argument("--riadir", type=Path, required=True)
    parser.add_argument(
        "--copy", action=argparse.BooleanOptionalAction, default=False
    )
    parser.add_argument(
        "--init-datalad", action=argparse.BooleanOptionalAction, default=False
    )
    parser.add_argument(
        "--archive", action=argparse.BooleanOptionalAction, default=False
    )
    parser.add_argument("--n-workers", type=int, default=1)

    args = parser.parse_args()
    main(**vars(args))
