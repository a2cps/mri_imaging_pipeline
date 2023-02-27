import pathlib
import argparse
from typing import List, Optional


def main(
    bind_dir: pathlib.Path,
    container: str,
    bidsdir: List[pathlib.Path],
    outdir: List[pathlib.Path],
    launchfile: pathlib.Path = pathlib.Path("launchfile"),
    nthreads: Optional[int] = None,
    mem_mb: Optional[int] = None,
) -> None:

    lines = []
    for t, (bids, logdir) in enumerate(zip(bidsdir, outdir)):
        if not logdir.exists():
            logdir.mkdir(parents=True)
        msg = f"""singularity run -e \
                -B {bind_dir}:{bind_dir} \
                docker://{container} \
                {bids} {logdir.resolve()} \
                participant \
                --output-resolution 1.7 \
                --denoise-method patch2self \
                --unringing-method mrdegibbs \
                --hmc_model eddy \
                --eddy-config eddy_params.json \
                --fs-license-file license.txt \
                -w {logdir.resolve()}"""
        if nthreads:
            msg += f" --nthreads {nthreads}"
        if mem_mb:
            msg += f" --mem_mb {mem_mb}"
        msg += f" > {logdir}/{t}.out 2> {logdir}/{t}.err"
        lines.append(msg)
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
    parser.add_argument("--nthreads", default=None)
    parser.add_argument("--mem-mb", default=None)

    args = parser.parse_args()
    main(
        bind_dir=args.BIND_DIR,
        container=args.CONTAINER_IMAGE,
        bidsdir=args.bidsdir,
        outdir=args.outdir,
        launchfile=args.launchfile,
        nthreads=args.nthreads,
        mem_mb=args.mem_mb,
    )
