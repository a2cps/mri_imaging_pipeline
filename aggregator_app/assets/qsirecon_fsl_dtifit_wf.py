import json
import shutil
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
*_timeseries.tsv
"""


DESCRIPTION = {
    "BIDSVersion": "1.1.1",
    "CodeURL": "https://github.com/pennbbl/qsiprep",
    "DatasetLinks": {
        "preprocessed": "/tmp/tmp3_ux1pv6",
        "templateflow": "https://github.com/templateflow/templateflow",
    },
    "DatasetType": "derivative",
    "GeneratedBy": [
        {
            "CodeURL": "https://github.com/PennLINC/qsirecon/archive/1.0.1.dev0+gf78c888.d20250114.tar.gz",
            "Name": "qsirecon",
            "Version": "1.0.1.dev0+gf78c888.d20250114",
        },
        {
            "CodeURL": "https://github.com/pennbbl/qsiprep/archive/0.21.5.dev0+g36b93fe.d20240504.tar.gz",
            "Name": "qsiprep",
            "Version": "0.21.5.dev0+g36b93fe.d20240504",
        },
    ],
    "Name": "QSIRecon output",
    "PipelineDescription": {
        "CodeURL": "https://github.com/pennbbl/qsiprep/archive/0.21.5.dev0+g36b93fe.d20240504.tar.gz",
        "Name": "qsiprep",
        "Version": "0.21.5.dev0+g36b93fe.d20240504",
    },
    "SourceDatasetsURLs": ["https://doi.org/TODO: eventually a DOI for the dataset"],
}

DESCRIPTION2 = {
    "BIDSVersion": "1.1.1",
    "CodeURL": "https://github.com/pennbbl/qsiprep",
    "DatasetLinks": {
        "preprocessed": "/tmp/tmp3_ux1pv6",
        "qsirecon": "/tmp/tmpoq6ix8er/qsirecon-fsl",
        "templateflow": "https://github.com/templateflow/templateflow",
    },
    "DatasetType": "derivative",
    "GeneratedBy": [
        {
            "CodeURL": "https://github.com/PennLINC/qsirecon/archive/1.0.1.dev0+gf78c888.d20250114.tar.gz",
            "Name": "qsirecon",
            "Version": "1.0.1.dev0+gf78c888.d20250114",
        },
        {
            "CodeURL": "https://github.com/pennbbl/qsiprep/archive/0.21.5.dev0+g36b93fe.d20240504.tar.gz",
            "Name": "qsiprep",
            "Version": "0.21.5.dev0+g36b93fe.d20240504",
        },
    ],
    "Name": "QSIRecon output",
    "PipelineDescription": {
        "CodeURL": "https://github.com/pennbbl/qsiprep/archive/0.21.5.dev0+g36b93fe.d20240504.tar.gz",
        "Name": "qsiprep",
        "Version": "0.21.5.dev0+g36b93fe.d20240504",
    },
    "SourceDatasetsURLs": ["https://doi.org/TODO: eventually a DOI for the dataset"],
}


def copy(outdir: Path, inroot: Path) -> None:
    for product in ["qsirecon-fsl", "split_shells", "dtifit"]:
        bu.mkdir_recursive(outdir / product)
        for src in (inroot / "qsirecon_fsl_dtifit").glob(f"*/{product}"):
            if product == "qsirecon-fsl":
                ignore = shutil.ignore_patterns(
                    ".bidsignore", "logs", "dataset_description.json"
                )
            else:
                ignore = None

            utils.mergetree_overwrite(
                src,
                outdir / product,
                ignore=ignore,
            )


def make_toplevel(outdir: Path) -> None:
    # create top-level files
    bu.mkdir_recursive(outdir)

    (outdir / "qsirecon-fsl" / "dataset_description.json").write_text(
        json.dumps(DESCRIPTION, indent=2)
    )

    (
        outdir
        / "qsirecon-fsl"
        / "derivatives"
        / "qsirecon-FSL"
        / "dataset_description.json"
    ).write_text(json.dumps(DESCRIPTION2, indent=2))

    (outdir / "qsirecon-fsl" / ".bidsignore").write_text(BIDS_IGNORE)
    (
        outdir / "qsirecon-fsl" / "derivatives" / "qsirecon-FSL" / ".bidsignore"
    ).write_text(BIDS_IGNORE)
