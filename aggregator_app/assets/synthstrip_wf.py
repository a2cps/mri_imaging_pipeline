import json
from pathlib import Path

import polars as pl
import utils
from biomarkers import utils as bu

DESCRIPTION = {
    "Name": "SynthStrip",
    "BIDSVersion": "1.11.1",
    "DatasetType": "derivative",
    "GeneratedBy": [{"Name": "SynthStrip", "Version": "1.6"}],
}

README = "A2CPS dataset"

VOLUMES = {
    "sub": {
        "LongName": "Subject",
        "Description": "Study Participant, BIDS Subject ID",
        "TermURL": "https://bids-specification.readthedocs.io/en/v1.9.0/appendices/entities.html#sub",
    },
    "ses": {
        "LongName": "Session",
        "Description": "Visit, Protocol, BIDS Session ID",
        "Levels": {"V1": "baseline_visit", "V3": "3mo_postop"},
        "TermURL": "https://bids-specification.readthedocs.io/en/v1.9.0/appendices/entities.html#ses",
    },
    "n_voxels": {
        "LongName": "Number Voxels",
        "Description": "Count of Voxels Within the Mask",
    },
    "csf": {
        "LongName": "Cerebrospinal Fluid",
        "Description": "Whether the model was configured to include CSF (true should have fewer n_voxels as compared to false)",
    },
}


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


def copyv4(outdir: Path, inroot: Path) -> None:
    # copy files over

    bu.mkdir_recursive(outdir)

    for src in (inroot / "synthstrip-v4").glob("sub*"):
        utils.mergetree_overwrite(src, outdir / src.name)


def make_toplevel(outdir: Path, inroot: Path) -> None:

    pl.scan_csv(f"{inroot}/*/synthstrip/*/volumes.tsv", separator="\t").sink_csv(
        outdir / "volumes.tsv", separator="\t", mkdir=True
    )
    (outdir / "volumes.json").write_text(json.dumps(VOLUMES, indent=2, sort_keys=True))
