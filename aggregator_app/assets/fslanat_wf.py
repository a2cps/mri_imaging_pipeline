import shutil
from pathlib import Path

import pandas as pd
from fslanat.models import fslanat

import utils


def _get_fslanat_table(root: Path) -> pd.DataFrame:
    result = fslanat.FSLAnatResult.from_root(root)
    regions = result.get_volumes().drop(columns="src")
    brain = result.get_t1volumes()
    return pd.concat([regions, brain], axis=1)


def _get_all_volumes(root: Path) -> pd.DataFrame:
    volumes = []
    for src in root.glob("sub*"):
        sub = utils._get_sub(src)
        ses = utils._get_ses(src)
        volumes.append(_get_fslanat_table(src).assign(sub=sub, ses=ses))

    return pd.concat(volumes, ignore_index=True)


def main(outdir: Path, inroot: Path) -> None:
    if not outdir.exists():
        outdir.mkdir(parents=True)

    for src in inroot.glob("fslanat/*"):
        shutil.copytree(
            src,
            outdir,
            dirs_exist_ok=True,
            copy_function=utils._copy_if_needed,
        )

    _get_all_volumes(outdir).to_csv(
        outdir / "fslanat.tsv", sep="\t", index=False
    )
