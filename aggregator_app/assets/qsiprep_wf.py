from pathlib import Path

import utils
from biomarkers import utils as bu


def copy(outdir: Path, inroot: Path, job: str = "qsiprep") -> None:
    bu.mkdir_recursive(outdir / f"{job}-V1")
    bu.mkdir_recursive(outdir / f"{job}-V3")

    for src in inroot.glob(f"{job}/*/qsiprep/sub*"):
        ses = bu.get_ses_from_sublong(src)
        if src.is_file():
            utils.symlink_if_needed(
                src,
                outdir / f"{job}-{ses}" / src.name,
            )
        else:
            utils.mergetree_overwrite(src, outdir / f"{job}-{ses}" / src.name)

    for src in inroot.glob(f"{job}/*/eddyqc"):
        sub = bu.get_sub_from_sublong(src)
        ses = bu.get_ses_from_sublong(src)

        if "denoise" in job:
            eqc = "eddyqc_nodenoise"
        else:
            eqc = "eddyqc"
        out_subses = outdir / eqc / f"sub-{sub}" / f"ses-{ses}"
        bu.mkdir_recursive(out_subses)

        utils.mergetree_overwrite(src, out_subses)
