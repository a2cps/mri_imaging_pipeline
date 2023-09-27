import argparse
import logging
import os
import shutil
from pathlib import Path

from signatures.cli import signatures

# from signatures.flows.signature import signature_flow
# from prefect.task_runners import SequentialTaskRunner


def main(
    fmriprep_dir: list[Path], output_dir: list[Path], n_workers: int = 1
) -> None:
    if not (uuid := os.environ.get("_tapisJobUUID")):
        msg = "Unable to get environment variable _tapisJobUUID"
        raise AssertionError(msg)
    if not (oldlog := Path("tapisjob.out")).exists():
        msg = "Unable to find expected log file: tapisjob.out"
        raise AssertionError(msg)

    # fmriprep dirs may point to broken symlinks, or folders might not exist
    # so, need to ensure that we get one output dir for each input dir
    fmriprep_subdirs = []
    output_dir_final = []
    for ind, outd in zip(fmriprep_dir, output_dir, strict=True):
        logging.info(f"Looking for sub dirs in {ind}")
        for d in ind.glob("sub*"):
            if d.is_dir():
                logging.info(f"Found! Will process files in {d}")
                fmriprep_subdirs.append(d)
                output_dir_final.append(outd)
            else:
                logging.warning(f"No valid sub directories found within {ind}")

    signatures._main(
        fmriprep_subdirs=fmriprep_subdirs,
        output_dirs=output_dir_final,
        n_workers=n_workers,
    )

    for o in output_dir:
        if o.exists():
            shutil.copy2(oldlog, o / f"{uuid}.out")
        else:
            logging.warning(f"Expected {o} but that path does not exist")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--fmriprep-dir", nargs="+", type=Path, required=True)
    parser.add_argument("--output-dir", nargs="+", type=Path, required=True)
    parser.add_argument("--n-workers", type=int, default=1)

    args = parser.parse_args()
    main(**vars(args))
