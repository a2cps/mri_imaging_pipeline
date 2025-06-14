from pathlib import Path

import polars as pl
import utils
from biomarkers import utils as bu

IMTYPES = {"T1w": "anat", "T2w": "anat", "bold": "func", "dwi": "dwi"}


def generate_tsv(output_dir: Path, mod: str) -> None:
    """
    Generates a tsv file from all json files in the derivatives directory
    """

    datalist = []
    for jsonfile in output_dir.glob(f"sub-*/**/{IMTYPES[mod]}/sub-*_{mod}.json"):
        datalist.append(
            pl.read_json(jsonfile)
            .drop(
                "bids_meta", "provenance", "bValuesEstimation", "bValues", strict=False
            )
            .with_columns(bids_name=pl.lit(jsonfile.stem))
        )

    if len(datalist):
        pl.concat(datalist, how="vertical_relaxed").unique(
            "bids_name", keep="last"
        ).write_csv(output_dir / (f"group_{mod}.tsv"), separator="\t")


def copy(outdir: Path, inroot: Path) -> None:
    if not outdir.exists():
        outdir.mkdir(parents=True)

    # this glob grabs both sub-##### directories and sub*html files
    for src in inroot.glob("mriqc/*/mriqc/sub*"):
        if src.is_file():
            utils._copy_overwrite(src, outdir / src.name)
        else:
            utils.mergetree_overwrite(src, outdir / src.name)


def make_toplevel(outdir: Path) -> None:
    bu.mkdir_recursive(outdir)
    # https://github.com/nipreps/mriqc/blob/a2c320cce2ffff5a0e32d71213db7df834b5026a/mriqc/cli/run.py#L196-L236
    for modality in ["T1w", "bold", "dwi"]:
        generate_tsv(outdir, modality)
