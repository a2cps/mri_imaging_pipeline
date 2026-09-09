from pathlib import Path

import polars as pl
import utils
from biomarkers import utils as bu
from nilearn import maskers

SMALLWOOD = (
    Path("/opt/tapis/tpl-MNI152NLin2009cAsym_atlas-smallwood_dseg.nii.gz")
    if Path("/opt/tapis/tpl-MNI152NLin2009cAsym_atlas-smallwood_dseg.nii.gz").exists()
    else Path("tpl-MNI152NLin2009cAsym_atlas-smallwood_dseg.nii.gz")
)

HENN = (
    Path(
        "/opt/tapis/tpl-MNI152NLin2009cAsym_atlas-henn_desc-controlspatientgmtfce05_dseg.nii.gz"
    )
    if Path(
        "/opt/tapis/tpl-MNI152NLin2009cAsym_atlas-henn_desc-controlspatientgmtfce05_dseg.nii.gz"
    ).exists()
    else Path(
        "tpl-MNI152NLin2009cAsym_atlas-henn_desc-controlspatientgmtfce05_dseg.nii.gz"
    )
)


def get_atlas_volumes(mridir: Path, atlas: Path) -> pl.DataFrame | None:
    out = []
    masker = maskers.NiftiLabelsMasker(labels_img=atlas, strategy="sum")
    # https://neuro-jena.github.io/cat12-help/#naming
    for p1 in mridir.rglob("*wp1*nii"):
        # sub/ses are regex-matched against the whole path string, so trim
        # to the globbed root (a tempdir name can contain 5 digits)
        rel = p1.relative_to(mridir)
        sub = bu.get_sub_from_sublong(rel)
        ses = bu.get_ses_from_sublong(rel)
        cluster_volume = utils.get_volume(p1, masker)
        volumes = {
            "sub": sub,
            "ses": ses,
            "mri": bu.img_stem(p1),
            "atlas": bu.img_stem(atlas),
            "cluster": list(range(len(cluster_volume))),
            "volume": cluster_volume,
        }
        out.append(pl.DataFrame(volumes))

    return pl.concat(out) if len(out) else None


def make_toplevel(outdir: Path) -> None:
    bu.mkdir_recursive(outdir)
    smallwood_volumes = get_atlas_volumes(mridir=outdir, atlas=SMALLWOOD)
    henn_volumes = get_atlas_volumes(mridir=outdir, atlas=HENN)
    if smallwood_volumes is not None and henn_volumes is not None:
        pl.concat([smallwood_volumes, henn_volumes]).write_csv(
            outdir / "cluster_volumes.tsv", separator="\t"
        )


def copy(outdir: Path, inroot: Path) -> None:
    bu.mkdir_recursive(outdir)

    for subses in inroot.glob("*"):
        # sub/ses are regex-matched against the whole path string, so trim
        # to the globbed root (a tempdir name can contain 5 digits)
        rel = subses.relative_to(inroot)
        sub = bu.get_sub_from_sublong(rel)
        ses = bu.get_ses_from_sublong(rel)
        # the app writes products to a "cat12" subdir whatever the archive
        # directory is named
        for out in ["label", "mri", "report", "surf"]:
            utils.mergetree_overwrite(
                subses / "cat12" / out, outdir / f"sub-{sub}" / f"ses-{ses}" / out
            )
