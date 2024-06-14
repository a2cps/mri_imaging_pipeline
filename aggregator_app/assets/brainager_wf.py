from pathlib import Path
import shutil

import pandas as pd

from biomarkers import utils as bu

import utils


def copy(outdir: Path, inroot: Path) -> None:
    bu.mkdir_recursive(outdir)

    for src in inroot.rglob("brainager/*/*"):
        sub = bu.get_sub_from_sublong(src)
        ses = bu.get_ses_from_sublong(src)

        out_subses = outdir / f"sub-{sub}" / f"ses-{ses}"
        bu.mkdir_recursive(out_subses)

        # brainager outputs csvs, but all tables in aggregation
        # could be tsv
        if src.suffix == ".csv":
            pd.read_csv(src).to_csv(
                out_subses / src.with_suffix(".tsv").name,
                sep="\t",
                index=False,
                na_rep="n/a",
            )
    for src in inroot.rglob("brainager/*"):
        sub = bu.get_sub_from_sublong(src)
        ses = bu.get_ses_from_sublong(src)
        utils.mergetree_overwrite(
            src,
            out_subses,
            ignore=shutil.ignore_patterns(
                "*remove.nii.gz", "sub*nii", "brainager_rank*.log", "*csv"
            ),
        )
