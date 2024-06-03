from pathlib import Path

import pandas as pd
from biomarkers.models import fslanat
from biomarkers import utils as bu

import utils


def _get_fslanat_table(root: Path) -> pd.DataFrame:
    result = fslanat.FSLAnatResult.from_root(root)
    regions = result.get_volumes().drop(columns="src")
    brain = result.get_t1volumes()
    return pd.concat([regions, brain], axis=1)


def _get_all_volumes(root: Path) -> pd.DataFrame:
    volumes = []
    for src in root.glob("sub*"):
        sub = bu.get_sub_from_sublong(src)
        ses = bu.get_ses_from_sublong(src)
        volumes.append(_get_fslanat_table(src).assign(sub=sub, ses=ses))

    return pd.concat(volumes, ignore_index=True)


def copy(outdir: Path, inroot: Path) -> None:
    bu.mkdir_recursive(outdir)

    for src in inroot.glob("fslanat/*"):
        utils.mergetree_overwrite(src, outdir)


def make_toplevel(outdir: Path) -> None:
    _get_all_volumes(outdir).to_csv(
        outdir / "fslanat.tsv", sep="\t", index=False
    )
