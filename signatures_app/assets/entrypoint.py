import argparse
import os
import shutil
from pathlib import Path

from signatures.cli import signatures


def main(
    fmriprep_dir: list[Path], output_dir: list[Path], n_workers: int = 1
) -> None:
    if not (uuid := os.environ.get("_tapisJobUUID")):
        msg = "Unable to get environment variable _tapisJobUUID"
        raise AssertionError(msg)
    if not (oldlog := Path("tapisjob.out")).exists():
        msg = "Unable to find expected log file: tapisjob.out"
        raise AssertionError(msg)

    fmriprep_subdirs = []
    for d in fmriprep_dir:
        fmriprep_subdirs += [x for x in d.glob("sub*") if Path(x).is_dir()]
    signatures._main(
        fmriprep_subdirs=fmriprep_subdirs,
        output_dirs=output_dir,
        n_workers=n_workers,
    )

    for o in output_dir:
        if not o.exists():
            o.mkdir(parents=True)
        shutil.copy2(oldlog, o / f"{uuid}.out")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--fmriprep-dir", nargs="+", type=Path, required=True)
    parser.add_argument("--output-dir", nargs="+", type=Path, required=True)
    parser.add_argument("--n-workers", type=int, default=1)

    args = parser.parse_args()
    main(**vars(args))
