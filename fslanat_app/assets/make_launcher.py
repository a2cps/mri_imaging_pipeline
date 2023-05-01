import pathlib
import argparse
from typing import Any, List, Optional
import shlex


def main(
    binddir: pathlib.Path,
    container: str,
    bids_dir: List[pathlib.Path],
    output_dir: List[pathlib.Path],
    launchfile: pathlib.Path = pathlib.Path("launchfile"),
    n_workers: Optional[int] = None,
    prefect_home: pathlib.Path = pathlib.Path("PREFECT_HOME"),
) -> None:
    lines = []
    for t, (bids, outdir) in enumerate(zip(bids_dir, output_dir)):
        if not outdir.exists():
            outdir.mkdir(parents=True)
        args: List[Any] = [
            "singularity",
            "run",
            "--env",
            f"'PREFECT_HOME={prefect_home}'",
            "-e",
            "-B",
            f"{binddir}:{binddir}",
            f"docker://{container}",
            "fslanat",
            "--bids-dir",
            str(bids),
            "--output-dir",
            str(outdir),
        ]
        if n_workers:
            args.extend(["--n-workers", str(n_workers)])

        # Note safety risk!!! (e.g., what if outdir were "out; rm -rf /" !?)
        # https://docs.python.org/3/library/shlex.html#shlex.quote
        line = shlex.join(args) + f" > {outdir}/{t}.out 2> {outdir}/{t}.err"
        lines.append(line)

    launchfile.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--bids-dir", nargs="+", type=pathlib.Path, required=True)
    parser.add_argument("--output-dir", nargs="+", type=pathlib.Path, required=True)
    parser.add_argument("--binddir", type=pathlib.Path, required=True)
    parser.add_argument("--container", required=True)
    parser.add_argument(
        "--launchfile", default=pathlib.Path("launchfile"), type=pathlib.Path
    )
    parser.add_argument("--n-workers", type=int)
    parser.add_argument(
        "--prefect-home", default=pathlib.Path("/tmp/prefect"), type=pathlib.Path
    )

    args = parser.parse_args()
    main(**vars(args))
