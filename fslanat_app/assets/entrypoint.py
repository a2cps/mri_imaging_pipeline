import argparse
import asyncio
import shutil
import typing
from pathlib import Path

from biomarkers import utils
from biomarkers.entrypoints import fslanat, tapismpi

tapismpi.configure_mpi_logger()


def main(
    input_dirs: typing.Sequence[Path],
    output_dirs: typing.Sequence[Path],
    precrop: typing.Sequence[bool] | None = None,
    mask_high_voxels: typing.Sequence[bool] | None = None,
) -> None:
    entrypoint = fslanat.FSLAnatEntrypoint(
        ins=input_dirs,
        outs=output_dirs,
        precrop=precrop,
        mask_high_voxels=mask_high_voxels,
        stage_ignore_patterns=shutil.ignore_patterns(
            "*heudiconv",
            "sourcedata",
            "*func*",
            "*tsv",
            "*json",
            "*err",
            "*out",
            "*log",
            "tapis*",
            "README",
            "CHANGES",
            "*dwi*",
            "*fmap*",
        ),
    )
    asyncio.run(entrypoint.run())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dirs", nargs="+", type=Path, required=True)
    parser.add_argument("--output-dirs", nargs="+", type=Path)
    parser.add_argument("--n-workers", type=int, default=1)
    parser.add_argument("--precrop", nargs="*", choices=("True", "False"))
    parser.add_argument("--mask-high-voxels", nargs="*", choices=("True", "False"))

    args = parser.parse_args()

    if args.output_dirs is None:
        output_dirs = []
        for input_dir in args.input_dirs:
            output_dirs.append(
                Path(
                    str(
                        Path(input_dir).relative_to(
                            "/corral-secure/projects/A2CPS/products/mris"
                        )
                    ).replace("/bids/", "/fslanat/")
                )
            )
    else:
        output_dirs = args.output_dirs

    precrop = utils.compare_arg_lengths(
        args.precrop, args.input_dirs, ("precrop", "input_dirs")
    )
    mask_high_voxels = utils.compare_arg_lengths(
        args.mask_high_voxels, args.input_dirs, ("mask_high_voxels", "input_dirs")
    )

    main(
        input_dirs=args.input_dirs,
        output_dirs=output_dirs,
        precrop=precrop,
        mask_high_voxels=mask_high_voxels,
    )
