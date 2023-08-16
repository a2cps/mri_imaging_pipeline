from pathlib import Path

from mriqc.reports.group import gen_html
from mriqc.utils.misc import generate_tsv

import utils


def main(outdir: Path, inroot: Path) -> None:
    if not outdir.exists():
        outdir.mkdir(parents=True)

    for job in ["anat", "cuff", "rest"]:
        # this glob grabs both sub-##### directories and sub*html files
        for src in inroot.glob(f"mriqc/*/{job}/sub*"):
            if src.is_file():
                utils._copy_overwrite(src, outdir / src.name)
            else:
                utils.mergetree_overwrite(src, outdir / src.name)

    # https://github.com/nipreps/mriqc/blob/a2c320cce2ffff5a0e32d71213db7df834b5026a/mriqc/cli/run.py#L196-L236
    for modality in ["T1w", "bold"]:
        _, out_tsv = generate_tsv(outdir, modality)
        gen_html(
            out_tsv,
            modality,
            csv_failed=outdir / f"group_variant-failed_{modality}.tsv",
            out_file=outdir / f"group_{modality}.html",
        )
