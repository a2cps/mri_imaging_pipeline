import argparse
import logging
import tempfile
import typing
from pathlib import Path

from biomarkers.entrypoints import brainager

logging.basicConfig(level=logging.INFO)


def main(
    input_dirs: typing.Iterable[Path],
    output_dirs: typing.Iterable[Path],
    n_workers: int = 1,
) -> None:
    with tempfile.TemporaryDirectory() as _tmpd:
        entrypoint = brainager.BrainagerEntrypoint(
            ins=input_dirs,
            outs=output_dirs,
            n_workers=n_workers,
            stage_dir=Path(_tmpd),
        )
        entrypoint.run()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dirs", nargs="+", type=Path, required=True)
    parser.add_argument("--output-dirs", nargs="+", type=Path, required=True)
    parser.add_argument("--n-workers", type=int, default=1)

    args = parser.parse_args()

    main(
        input_dirs=args.input_dirs,
        output_dirs=args.output_dirs,
        n_workers=args.n_workers,
    )
