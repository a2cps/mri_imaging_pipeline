import shutil
from pathlib import Path

import polars as pl
import utils
from biomarkers import utils as bu


def copy(outdir: Path, inroot: Path) -> None:
    bu.mkdir_recursive(outdir)

    for src in inroot.rglob("brainager/*/*"):
        # sub/ses are regex-matched against the whole path string, so trim
        # to the globbed root (a tempdir name can contain 5 digits)
        rel = src.relative_to(inroot)
        sub = bu.get_sub_from_sublong(rel)
        ses = bu.get_ses_from_sublong(rel)

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
        rel = src.relative_to(inroot)
        sub = bu.get_sub_from_sublong(rel)
        ses = bu.get_ses_from_sublong(rel)
        utils.mergetree_overwrite(
            src,
            outdir / f"sub-{sub}" / f"ses-{ses}",
            ignore=shutil.ignore_patterns(
                "*remove.nii.gz", "sub*nii", "brainager_rank*.log", "*csv"
            ),
        )
