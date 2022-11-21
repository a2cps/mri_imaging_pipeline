import pathlib
import argparse
from typing import List


def main(
    bind_dir: pathlib.Path,
    container: str,
    bidsdir: List[pathlib.Path],
    outdir: List[pathlib.Path],
    launchfile: pathlib.Path = pathlib.Path("launchfile"),
    n_proc: int = 1
) -> None:

    lines = []
    for t, (bids, logdir) in enumerate(zip(bidsdir, outdir)):
        if not logdir.exists():
            logdir.mkdir(parents=True)
        lines.append(
            f"singularity run -B {bind_dir}:{bind_dir} --cleanenv {container} --bids-dir {bids} --output-dir {logdir} --n-proc {n_proc} > {logdir}/{t}.out 2> {logdir}/{t}.err"
        )
    launchfile.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("BIND_DIR", type=pathlib.Path)
    parser.add_argument("CONTAINER_IMAGE")
    parser.add_argument("--bidsdir", nargs="+", type=pathlib.Path, required=True)
    parser.add_argument("--outdir", nargs="+", type=pathlib.Path, required=True)
    parser.add_argument(
        "--launchfile", default=pathlib.Path("launchfile"), type=pathlib.Path
    )
    parser.add_argument("--n-proc", type=int)

    args = parser.parse_args()
    main(
        bind_dir=args.BIND_DIR,
        container=args.CONTAINER_IMAGE,
        bidsdir=args.bidsdir,
        outdir=args.outdir,
        launchfile=args.launchfile,
        n_proc=args.n_proc
    )
