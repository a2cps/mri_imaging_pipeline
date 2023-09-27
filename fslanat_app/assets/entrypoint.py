import argparse
import logging
import os
import shutil
import tempfile
import typing
from pathlib import Path

from fslanat.cli import fslanat
from fslanat.flows import fslanat as fslanat_flow


def main(
    anats: typing.Sequence[Path],
    output_dir: typing.Sequence[Path],
    precrops: typing.Sequence[bool],
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
            anats=anats,
            output_dir=tmpdir,
            n_workers=n_workers,
            precrops=precrops,
        )

        for i, o in zip(anats, output_dir):
            if (
                tmpi := fslanat_flow._predict_fsl_anat_output(
                    tmpdir, fslanat_flow._img_stem(i)
                )
            ).exists():
                if o.exists():
                    shutil.copytree(tmpi, o / tmpi.name)
                    shutil.copy2(oldlog, o / f"{uuid}.out")
                else:
                    logging.warning(
                        f"Expected {o} but that path does not exist"
                    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--anats", nargs="+", type=Path, required=True)
    parser.add_argument("--output-dir", nargs="+", type=Path, required=True)
    parser.add_argument("--precrop", nargs="*", choices=("True", "False"))
    parser.add_argument("--n-workers", type=int, default=1)

    args = parser.parse_args()
    if args.precrop:
        if not len(args.anats) == len(args.precrop):
            msg = f"""
            --precrops must have the same lengths as --anats.
            Found {len(args.anats)=} and {len(args.precrops)=}
            """
            raise AssertionError(msg)
        _precrops = [precrop == "True" for precrop in args.precrop]
    else:
        _precrops = [False] * len(args.anats)
    main(
        anats=args.anats,
        output_dir=args.output_dir,
        n_workers=args.n_workers,
        precrops=_precrops,
    )
