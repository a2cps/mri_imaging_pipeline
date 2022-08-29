import argparse
import pathlib
from typing import List, Tuple


def get_io(
    indirs: List[pathlib.Path], outdirs: List[pathlib.Path]
) -> Tuple[pathlib.Path, pathlib.Path]:
    nii = []
    out = []

    for i, o in zip(indirs, outdirs):

        for n in i.glob("**/*bold.nii.gz"):
            outsub = o / n.stem.removesuffix(".nii")
            if not outsub.exists():
                outsub.mkdir(parents=True, exist_ok=True)
            nii.append(n)
            out.append(outsub)

    return nii, out


def main(
    bind_dir: pathlib.Path,
    container: str,
    bidsdir: List[pathlib.Path],
    outdir: List[pathlib.Path],
    launchfile: pathlib.Path = pathlib.Path("launchfile"),
) -> None:

    nii, out = get_io(bidsdir, outdir)

    lines = []
    for i, (img, o) in enumerate(zip(nii, out)):
        lines.append(
            f"singularity run -B {bind_dir}:{bind_dir} --cleanenv  {container} --input {img} --output {o} > {o.parent}/{i}.out 2> {o.parent}/{i}.err"
        )
    launchfile.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    """
    python make_launcher.py --bind-dir /corral-secure/projects/A2CPS --container docker://psadil/phantom-qa:latest --bids b --out o
    python make_launcher.py --bind-dir /corral-secure/projects/A2CPS --container docker://psadil/phantom-qa:latest --bids b1 b2 --out o1 o2
    b=(b0 b1 b2)
    o=(o0 o1 o2)
    python make_launcher.py --bind-dir /corral-secure/projects/A2CPS --container docker://psadil/phantom-qa:latest --bids "${b[@]}" --out "${o[@]}"
    """

    parser = argparse.ArgumentParser(
        description="write lines of launcher script for TACC"
    )
    parser.add_argument("--bind-dir", required=True)
    parser.add_argument("--container", required=True)
    parser.add_argument(
        "--bids",
        required=True,
        nargs="+",
        help="list of anatomical files to parse, separated by spaces",
        type=pathlib.Path,
    )
    parser.add_argument("--out", required=True, nargs="+", type=pathlib.Path)
    parser.add_argument("--launchfile", default="launchfile", type=pathlib.Path)

    args = parser.parse_args()
    main(
        bind_dir=args.bind_dir,
        container=args.container,
        bidsdir=args.bids,
        outdir=args.out,
        launchfile=args.launchfile,
    )
