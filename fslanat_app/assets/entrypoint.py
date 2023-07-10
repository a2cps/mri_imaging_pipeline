import argparse
import os
import shutil
import tempfile
from pathlib import Path

from fslanat.cli import fslanat
from fslanat.flows import fslanat as fslanat_flow


def main(
    anats: list[Path],
    output_dir: list[Path],
    n_workers: int = 1,
) -> None:
    if not (uuid := os.environ.get("_tapisJobUUID")):
        msg = "Unable to get environment variable _tapisJobUUID"
        raise AssertionError(msg)
    if not (oldlog := Path("tapisjob.out")).exists():
        msg = "Unable to find expected log file: tapisjob.out"
        raise AssertionError(msg)

    with tempfile.TemporaryDirectory() as _tmpdir:
        tmpdir = Path(_tmpdir)
        fslanat._main(
            anats=frozenset(anats), output_dir=tmpdir, n_workers=n_workers
        )

        for i, o in zip(anats, output_dir):
            if (
                tmpi := fslanat_flow._predict_fsl_anat_output(
                    tmpdir, fslanat_flow._img_stem(i)
                )
            ).exists():
                dst = o / tmpi.name
                if not o.exists():
                    o.mkdir(parents=True)
                shutil.copytree(tmpi, dst)

                shutil.copy2(oldlog, o / f"{uuid}.out")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--anats", nargs="+", type=Path, required=True)
    parser.add_argument("--output-dir", nargs="+", type=Path, required=True)
    parser.add_argument("--n-workers", type=int, default=1)

    args = parser.parse_args()
    main(**vars(args))
