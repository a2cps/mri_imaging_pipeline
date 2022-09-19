import shutil
import pathlib
import argparse
from typing import List, Tuple


def get_io(
    indirs: List[pathlib.Path], outdirs: List[pathlib.Path]
) -> Tuple[List[pathlib.Path], List[pathlib.Path]]:
    nii = []
    out = []
    for i, o in zip(indirs, outdirs):
        # cat12 has poor control over where results are placed; it's always relative to the input image
        # so, we manually create the output directory, then move the input image into it, and the
        # resulting copied file will be fed to cat12
        if not o.exists():
            o.mkdir(parents=True, exist_ok=True)

        # NOTE: this will overwrite existing files without asking
        for t1w in i.glob("**/*_T1w.nii.gz"):
            nii.append(pathlib.Path(shutil.copy2(t1w, o)))
            # if the bids folder had multiple t1w (e.g., run on some aggregated dataset), they will all be
            # deposited into the same output directory
            out.append(o)

    return nii, out


def main(
    bind_dir: pathlib.Path,
    container: str,
    batch: pathlib.Path,
    bidsdir: List[pathlib.Path],
    outdir: List[pathlib.Path],
    a1: int = 1,
    launchfile: pathlib.Path = pathlib.Path("launchfile"),
) -> None:

    nifti, outdir = get_io(bidsdir, outdir)

    lines = []
    for t, (t1w, logdir) in enumerate(zip(nifti, outdir)):
        lines.append(
            f"singularity run -B {bind_dir}:{bind_dir} --cleanenv  {container} -b {batch} -a1 {a1} {t1w} > {logdir}/{t}.out 2> {logdir}/{t}.err"
        )
    launchfile.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":

    """
    python make_launcher.py /corral-secure/projects/A2CPS cat12.sif batch.m T1w.nii.gz second_T1w.nii.gz
    """

    parser = argparse.ArgumentParser(
        description="write lines of launcher script for running "
    )
    parser.add_argument("BIND_DIR", type=pathlib.Path)
    parser.add_argument("CONTAINER_IMAGE")
    parser.add_argument("BATCH", type=pathlib.Path)
    parser.add_argument("--bidsdir", nargs="+", type=pathlib.Path, required=True)
    parser.add_argument("--outdir", nargs="+", type=pathlib.Path, required=True)
    parser.add_argument(
        "--launchfile", default=pathlib.Path("launchfile"), type=pathlib.Path
    )
    parser.add_argument("--a1", default=1, type=int)

    args = parser.parse_args()
    main(
        bind_dir=args.BIND_DIR,
        container=args.CONTAINER_IMAGE,
        batch=args.BATCH,
        bidsdir=args.bidsdir,
        a1=args.a1,
        outdir=args.outdir,
        launchfile=args.launchfile,
    )
