import json
import re
from pathlib import Path

import utils

from biomarkers import utils as bu

BIDS_IGNORE = """
*.html
logs/
figures/
*_xfm.*
*.surf.gii
*_boldref.nii.gz
*_bold.func.gii
*_mixing.tsv
*_AROMAnoiseICs.csv
*_timeseries.tsv
"""


DESCRIPTION = {
    "Name": "fMRIPrep - fMRI PREProcessing workflow",
    "BIDSVersion": "1.8.0",
    "DatasetType": "derivative",
    "GeneratedBy": [
        {
            "Name": "fMRIPrep",
            "Version": "20.2.3",
            "CodeURL": "https://github.com/nipreps/fmriprep/archive/20.2.3.tar.gz",
        }
    ],
    "SourceDatasets": [
        {
            "URL": "https://doi.org/TODO: eventually a DOI for the dataset",
            "DOI": "TODO: eventually a DOI for the dataset",
        }
    ],
}


README = "A2CPS dataset"

ASEG = (
    Path("/opt/tapis/desc-aseg_dseg.tsv")
    if Path("/opt/tapis/desc-aseg_dseg.tsv").exists()
    else Path("desc-aseg_dseg.tsv")
)
APARCASEG = (
    Path("/opt/tapis/desc-aparcaseg_dseg.tsv")
    if Path("/opt/tapis/desc-aparcaseg_dseg.tsv").exists()
    else Path("desc-aparcaseg_dseg.tsv")
)


def copy(outdir: Path, inroot: Path) -> None:
    # copy files over

    _job = re.findall(r"(?<=fmriprep-)(anat|cuff|rest)", str(outdir))
    if not _job:
        raise ValueError
    job = _job[0]
    bu.mkdir_recursive(outdir)

    # this grabs both sub-##### directories and sub*html files
    for src in inroot.glob(f"fmriprep/*/{job}/fmriprep/sub*"):
        if src.is_file():
            sub = bu.get_sub_from_sublong(src)
            ses = bu.get_ses_from_sublong(src)
            utils._copy_overwrite(src, outdir / f"sub-{sub}_ses-{ses}.html")
        else:
            utils.mergetree_overwrite(src, outdir / src.name)


def make_toplevel(outdir: Path) -> None:
    # create top-level files
    bu.mkdir_recursive(outdir)

    readme = outdir / "README"
    readme.touch()
    readme.write_text(README)

    description = outdir / "dataset_description.json"
    description.write_text(json.dumps(DESCRIPTION, indent=2))

    bids_ignore = outdir / ".bidsignore"
    bids_ignore.write_text(BIDS_IGNORE)

    utils._copy_overwrite(ASEG, outdir / ASEG.name)
    utils._copy_overwrite(APARCASEG, outdir / APARCASEG.name)
