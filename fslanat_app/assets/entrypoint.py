import argparse
import asyncio
import tempfile
import typing
from pathlib import Path
import logging

from biomarkers import utils
from biomarkers.entrypoints import fslanat

logging.basicConfig(
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    level=logging.INFO,
)


def main(
    input_dirs: typing.Iterable[Path],
    output_dirs: typing.Iterable[Path],
    n_workers: int = 1,
    precrop: typing.Sequence[bool] | None = None,
    mask_high_voxels: typing.Sequence[bool] | None = None,
) -> None:
    with tempfile.TemporaryDirectory() as _tmpd:
        entrypoint = fslanat.FSLAnatEntrypoint(
            ins=input_dirs,
            outs=output_dirs,
            n_workers=n_workers,
            stage_dir=Path(_tmpd),
            precrop=precrop,
            mask_high_voxels=mask_high_voxels,
        )
        asyncio.run(entrypoint.run())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dirs", nargs="+", type=Path, required=True)
    parser.add_argument("--output-dirs", nargs="+", type=Path, required=True)
    parser.add_argument("--n-workers", type=int, default=1)
    parser.add_argument("--precrop", nargs="*", choices=("True", "False"))
    parser.add_argument(
        "--mask-high-voxels", nargs="*", choices=("True", "False")
    )

    args = parser.parse_args()
    precrop = utils.compare_arg_lengths(
        args.precrop, args.input_dirs, ("precrop", "input_dirs")
    )
    mask_high_voxels = utils.compare_arg_lengths(
        args.mask_high_voxels,
        args.input_dirs,
        ("mask_high_voxels", "input_dirs"),
    )

    main(
        input_dirs=args.input_dirs,
        output_dirs=args.output_dirs,
        n_workers=args.n_workers,
        precrop=precrop,
        mask_high_voxels=mask_high_voxels,
    )
