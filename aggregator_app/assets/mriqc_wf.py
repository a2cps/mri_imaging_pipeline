from pathlib import Path

import utils
from biomarkers import utils as bu
from mriqc.reports.group import gen_html
from mriqc.utils.misc import generate_tsv


def copy(outdir: Path, inroot: Path) -> None:
    if not outdir.exists():
        outdir.mkdir(parents=True)

    # this glob grabs both sub-##### directories and sub*html files
    for src in inroot.glob("mriqc/*/mriqc/sub*"):
        if src.is_file():
            utils._copy_overwrite(src, outdir / src.name)
        else:
            utils.mergetree_overwrite(src, outdir / src.name)


def make_toplevel(outdir: Path) -> None:
    bu.mkdir_recursive(outdir)
    # https://github.com/nipreps/mriqc/blob/a2c320cce2ffff5a0e32d71213db7df834b5026a/mriqc/cli/run.py#L196-L236
    for modality in ["T1w", "bold"]:
        _, out_tsv = generate_tsv(outdir, modality)
        if Path(out_tsv).exists():
            gen_html(
                out_tsv,
                modality,
                csv_failed=outdir / f"group_variant-failed_{modality}.tsv",
                out_file=outdir / f"group_{modality}.html",
            )
