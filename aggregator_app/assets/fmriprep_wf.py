import json
import re
import shutil
from pathlib import Path

import utils

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
    Path("/opt/tapis/desc-aseg_desg.tsv")
    if Path("/opt/tapis/desc-aseg_desg.tsv").exists()
    else "desc-aseg_desg.tsv"
)
APARCASEG = (
    Path("/opt/tapis/desc-aparcaseg_desg.tsv")
    if Path("/opt/tapis/desc-aparcaseg_desg.tsv").exists()
    else "desc-aparcaseg_desg.tsv"
)


def main(outdir: Path, inroot: Path) -> None:
    # copy files over

    _job = re.findall(r"(?<=fmriprep-)(anat|cuff|rest)", str(outdir))
    if not _job:
        raise ValueError
    job = _job[0]
    if not outdir.exists():
        outdir.mkdir(parents=True)

    # this grabs both sub-##### directories and sub*html files
    for src in inroot.glob(f"fmriprep/*/{job}/fmriprep/sub*"):
        if src.is_file():
            sub = utils._get_sub(src)
            ses = utils._get_ses(src)
            utils._copy_if_needed(src, outdir / f"sub-{sub}_ses-{ses}.html")
        else:
            shutil.copytree(
                src,
                outdir / src.name,
                dirs_exist_ok=True,
                copy_function=utils._copy_if_needed,
            )

    # create top-level files
    readme = outdir / "README"
    readme.touch()
    readme.write_text(README)

    description = outdir / "dataset_description.json"
    description.write_text(json.dumps(DESCRIPTION, indent=2))

    bids_ignore = outdir / ".bidsignore"
    bids_ignore.write_text(BIDS_IGNORE)

    shutil.copy2(ASEG, outdir)
    shutil.copy2(APARCASEG, outdir)
