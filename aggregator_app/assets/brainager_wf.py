import shutil
from pathlib import Path

import polars as pl
import utils
from biomarkers import utils as bu


def copy(outdir: Path, inroot: Path) -> None:
    bu.mkdir_recursive(outdir)

    for src in inroot.rglob("brainager/*/*"):
        sub = bu.get_sub_from_sublong(src)
        ses = bu.get_ses_from_sublong(src)

        out_subses = outdir / f"sub-{sub}" / f"ses-{ses}"
        bu.mkdir_recursive(out_subses)

        # brainager outputs csvs, but all tables in aggregation
        # should be tsv
        if src.suffix == ".csv":
            pl.read_csv(src).write_csv(
                out_subses / src.with_suffix(".tsv").name,
                separator="\t",
                null_value="n/a",
            )
    for src in inroot.rglob("brainager/*"):
        sub = bu.get_sub_from_sublong(src)
        ses = bu.get_ses_from_sublong(src)
        utils.mergetree_overwrite(
            src,
            outdir / f"sub-{sub}" / f"ses-{ses}",
            ignore=shutil.ignore_patterns(
                "*remove.nii.gz", "sub*nii", "brainager_rank*.log", "*csv"
            ),
        )
