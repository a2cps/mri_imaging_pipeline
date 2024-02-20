import pathlib
import argparse
from typing import List


def main(
    bind_dir: pathlib.Path,
    container: str,
    bidsdir: List[pathlib.Path],
    recon_outdir: List[pathlib.Path],
    workdir: List[pathlib.Path],
    qsiprep_dir: List[pathlib.Path],
    freesurfer_input: List[pathlib.Path],
    launchfile: pathlib.Path = pathlib.Path("launchfile"),
    nthreads: int = 1,
    memmb: int = 1,
    output_resolution: int = 1,
    participant_label: str = 1,
    recon_only: str = 1,
    recon_spec: str = 1,
) -> None:

    lines = []
    for t, (bids, logdir) in enumerate(zip(bidsdir, recon_outdir)):
        if not logdir.exists():
            logdir.mkdir(parents=True)
        lines.append(
            f"singularity run -B {bind_dir}:{bind_dir} --cleanenv {container} {bids} {recon_outdir} -w {workdir} {recon_only} {recon_spec} --recon_input {qsiprep_dir} {participant_label} --freesurfer-input {freesurfer_input} --nthreads {nthreads} --mem_mb {memmb} --output_resolution {output_resolution} > {logdir}/{t}.out 2> {logdir}/{t}.err"
        )
    launchfile.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("BIND_DIR", type=pathlib.Path)
    parser.add_argument("CONTAINER_IMAGE")
    parser.add_argument("--bidsdir", nargs="+", type=pathlib.Path, required=True)
    parser.add_argument("--recon_outdir", nargs="+", type=pathlib.Path, required=True)
    parser.add_argument("--workdir", nargs="+", type=pathlib.Path, required=True)
    parser.add_argument("--qsiprep_dir", nargs="+", type=pathlib.Path, required=True)
    parser.add_argument("--freesurfer_dir", nargs="+", type=pathlib.Path, required=True)
    parser.add_argument(
        "--launchfile", default=pathlib.Path("launchfile"), type=pathlib.Path
    )
    parser.add_argument("--nthreads", type=int)
    parser.add_argument("--memmb", type=int)
    parser.add_argument("--output_resolution", type=int)
    parser.add_argument("--participant_label", type=str)
    parser.add_argument("--recon_only", type=str)
    parser.add_argument("--recon_spec", type=str)

    args = parser.parse_args()
    main(
        bind_dir=args.BIND_DIR,
        container=args.CONTAINER_IMAGE,
        bidsdir=args.bidsdir,
        recon_outdir=args.recon_outdir,
        workdir=args.workdir,
        qsiprep_dir=args.qsiprep_dir,
        freesurfer_dir=args.freesurfer_dir,
        launchfile=args.launchfile,
        nthreads=args.nthreads,
        memmb=args.memmb,
        output_resolution=args.output_resolution,
        participant_label=args.participant_label,
        recon_only=args.recon_only,
        recon_spec=args.recon_spec
    )
