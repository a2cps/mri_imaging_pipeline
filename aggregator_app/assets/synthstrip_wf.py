from pathlib import Path

import utils
from biomarkers import utils as bu

DESCRIPTION = {
    "Name": "SynthStrip",
    "BIDSVersion": "1.10.0",
    "DatasetType": "derivative",
    "GeneratedBy": [{"Name": "SynthStrip", "Version": "1.6"}],
}

README = "A2CPS dataset"


def copy(outdir: Path, inroot: Path, bidsdir: Path) -> None:
    # copy files over

    bu.mkdir_recursive(outdir)

    for src in inroot.glob("fmriprep/*/synthstrip/sub*"):
        utils.mergetree_overwrite(src, outdir / src.name)
        sub = bu.get_sub_from_sublong(src)
        ses = bu.get_ses_from_sublong(src)
        anat_stem = (
            Path(f"sub-{sub}") / f"ses-{ses}" / "anat" / f"sub-{sub}_ses-{ses}_T1w"
        )

        if (anat := bidsdir / f"{anat_stem}.nii.gz").exists():
            utils.symlink_if_needed(anat, outdir / f"{anat_stem}.nii.gz")
            json_stem = f"{anat_stem}.json"
            utils.symlink_if_needed(bidsdir / json_stem, outdir / json_stem)
