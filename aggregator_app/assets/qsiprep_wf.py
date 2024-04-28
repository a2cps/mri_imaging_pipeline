from pathlib import Path

import pandas as pd
import utils


def main(outdir: Path, inroot: Path) -> None:
    if not outdir.exists():
        outdir.mkdir(parents=True)

    for src in inroot.glob("qsiprep/*/qsiprep/sub*"):
        if src.is_file():
            sub = utils._get_sub(src)
            ses = utils._get_ses(src)

            # assumes that the src is a file like sub-#####.html
            # and that there's only one
            utils._copy_overwrite(
                src,
                outdir / f"sub-{sub}_ses-{ses}.html",
            )
        else:
            utils.mergetree_overwrite(src, outdir / src.name)


def make_toplevel(outdir: Path) -> None:
    dwiqc = []
    for d in outdir.glob("*"):
        dwiqc.append(pd.read_csv(d))

    pd.concat(dwiqc, ignore_index=True).to_csv(
        outdir / "desc-ImageQC_dwi.tsv", sep="\t", index=False, na_rep="n/a"
    )
