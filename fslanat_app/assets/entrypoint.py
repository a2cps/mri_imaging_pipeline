import argparse
import shutil
import tempfile
from pathlib import Path

from biomarkers.cli import fslanat
from biomarkers.flows import fslanat as fslanat_flow
from biomarkers import utils


def main(anats: list[Path], output_dir: list[Path]) -> None:
    with tempfile.TemporaryDirectory() as _tmpdir:
        tmpdir = Path(_tmpdir)
        fslanat._main(anats=frozenset(anats), output_dir=tmpdir, n_workers=len(anats))

        for i, o in zip(anats, output_dir):
            if (
                tmpi := fslanat_flow._predict_fsl_anat_output(tmpdir, utils.img_stem(i))
            ).exists():
                dst = o / tmpi.name
                if not o.exists():
                    o.mkdir(parents=True)
                shutil.copytree(tmpi, dst)
                for pattern in ["*log", "*err", "*out"]:
                    for f in Path("./").glob(pattern):
                        shutil.copy2(f, o)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--anats", nargs="+", type=Path, required=True)
    parser.add_argument("--output-dir", nargs="+", type=Path, required=True)

    args = parser.parse_args()
    main(**vars(args))
