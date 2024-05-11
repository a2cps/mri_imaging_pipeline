from pathlib import Path

import utils


def copy(outdir: Path, inroot: Path) -> None:
    outdir_qsiprep = outdir / "qsiprep"
    if not outdir_qsiprep.exists():
        outdir_qsiprep.mkdir(parents=True)

    for src in inroot.glob("qsiprep/*/qsiprep/sub*"):
        if src.is_file():
            sub = utils._get_sub(src)
            ses = utils._get_ses(src)
            # assumes that the src is a file like sub-#####.html
            # and that there's only one
            utils._symlink_if_needed(
                src,
                outdir_qsiprep / f"sub-{sub}_ses-{ses}.html",
            )
            utils._symlink_if_needed(
                src.with_name("dwiqc.json"),
                outdir_qsiprep / f"sub-{sub}_ses-{ses}.json",
            )
        else:
            utils.mergetree_overwrite(src, outdir_qsiprep / src.name)

    for src in inroot.glob("qsiprep/*/eddyqc"):
        sub = utils._get_sub(src)
        ses = utils._get_ses(src)

        out_subses = outdir / "eddyqc" / f"sub-{sub}" / f"ses-{ses}"
        if not out_subses.exists():
            out_subses.mkdir(parents=True)

        utils.mergetree_overwrite(src, out_subses)
