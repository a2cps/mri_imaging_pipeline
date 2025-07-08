import shutil
from pathlib import Path

import polars as pl
import utils
from biomarkers import utils as bu
from biomarkers.models import fslanat


def _get_fslanat_table(root: Path) -> pl.DataFrame:
    result = fslanat.FSLAnatResult.from_root(root)
    regions = result.get_volumes().drop(columns="src")
    brain = result.get_t1volumes()
    return pl.concat([pl.from_pandas(regions), pl.from_pandas(brain)], how="horizontal")


def _get_all_volumes(root: Path) -> pl.DataFrame:
    volumes = []
    for src in root.glob("sub*"):
        sub = bu.get_sub_from_sublong(src)
        ses = bu.get_ses_from_sublong(src)
        volumes.append(
            _get_fslanat_table(src).with_columns(sub=pl.lit(sub), ses=pl.lit(ses))
        )

    return pl.concat(volumes)


def copy(outdir: Path, inroot: Path) -> None:
    bu.mkdir_recursive(outdir)

    for src in inroot.glob("fslanat/*"):
        sub = bu.get_sub_from_sublong(src)
        ses = bu.get_ses_from_sublong(src)
        utils.mergetree_overwrite(
            src,
            outdir,
            ignore=shutil.ignore_patterns(
                f"fslanat-sub-{sub}_ses-{ses}_T1w.log", "fslanat_rank*.log"
            ),
        )


def make_toplevel(outdir: Path) -> None:
    bu.mkdir_recursive(outdir)
    _get_all_volumes(outdir).write_csv(outdir / "fslanat.tsv", separator="\t")
