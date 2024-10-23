from pathlib import Path

import utils
from biomarkers import utils as bu


def copy(outdir: Path, inroot: Path) -> None:
    bu.mkdir_recursive(outdir / "qsiprep-V1")
    bu.mkdir_recursive(outdir / "qsiprep-V3")

    for src in inroot.glob("qsiprep/*/qsiprep/sub*"):
        ses = bu.get_ses_from_sublong(src)
        if src.is_file():
            utils._symlink_if_needed(
                src,
                outdir / f"qsiprep-{ses}" / src.name,
            )
        else:
            utils.mergetree_overwrite(src, outdir / f"qsiprep-{ses}" / src.name)

    for src in inroot.glob("qsiprep/*/eddyqc"):
        sub = bu.get_sub_from_sublong(src)
        ses = bu.get_ses_from_sublong(src)

        out_subses = outdir / "eddyqc" / f"sub-{sub}" / f"ses-{ses}"
        bu.mkdir_recursive(out_subses)

        utils.mergetree_overwrite(src, out_subses)
