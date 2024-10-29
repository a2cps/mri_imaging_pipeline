import argparse
import pandas as pd
from pathlib import Path

SITE_LONG = {
    "NS": "NS_northshore",
    "UI": "UI_uic",
    "UC": "UC_uchicago",
    "UM": "UM_umichigan",
    "SH": "SH_spectrum_health",
    "WS": "WS_wayne_state",
    "RU": "RU_rush",
}


def get_uploaded() -> pd.DataFrame:
    raw = [
        {"site": "NS", "subject_id": "travel1", "visit": "NS"},
        {"site": "NS", "subject_id": "travel2", "visit": "NS"},
        {"site": "RU", "subject_id": "travel1", "visit": "RU"},
        {"site": "RU", "subject_id": "travel2", "visit": "RU"},
        {"site": "SH", "subject_id": "travel2", "visit": "SH"},
        {"site": "UC", "subject_id": "travel1", "visit": "UC"},
        {"site": "UC", "subject_id": "travel2", "visit": "UC"},
        {"site": "UI", "subject_id": "travel1", "visit": "UI"},
        {"site": "UI", "subject_id": "travel2", "visit": "UI"},
        {"site": "UM", "subject_id": "travel2", "visit": "UM1"},
        {"site": "UM", "subject_id": "travel2", "visit": "UM2"},
        {"site": "WS", "subject_id": "travel2", "visit": "WS"},
    ]

    return pd.DataFrame.from_records(raw)


def find_outputs(bids_path: Path):
    fmriprep_path = Path(str(bids_path).replace("bids", "fmriprep"))
    mriqc_path = Path(str(bids_path).replace("bids", "mriqc"))
    qsiprep_path = Path(str(bids_path).replace("bids", "qsiprep"))
    cat12_path = Path(str(bids_path).replace("bids", "cat12"))
    fslanat_path = Path(str(bids_path).replace("bids", "fslanat"))
    fcn_path = Path(str(bids_path).replace("bids", "fcn"))
    signatures_path = Path(str(bids_path).replace("bids", "signatures"))
    brainager_path = Path(str(bids_path).replace("bids", "brainager"))

    processing = {}
    processing["bids"] = len(list(bids_path.glob("*out"))) > 0
    processing["fmriprep_anat"] = (
        len(list((fmriprep_path / "anat").glob("*out"))) > 0
    )
    processing["fmriprep_cuff"] = (
        len(list((fmriprep_path / "cuff").glob("*out"))) > 0
    )
    processing["fmriprep_rest"] = (
        len(list((fmriprep_path / "rest").glob("*out"))) > 0
    )
    processing["mriqc_anat"] = (
        len(list((mriqc_path / "anat").glob("*out"))) > 0
    )
    processing["mriqc_cuff"] = (
        len(list((mriqc_path / "cuff").glob("*out"))) > 0
    )
    processing["mriqc_rest"] = (
        len(list((mriqc_path / "rest").glob("*out"))) > 0
    )
    processing["qsiprep"] = len(list(qsiprep_path.glob("*out"))) > 0
    processing["cat12"] = len(list(cat12_path.glob("*out"))) > 0
    processing["fslanat"] = len(list(fslanat_path.glob("*out"))) > 0
    processing["fcn"] = len(list(fcn_path.glob("*out"))) > 0
    processing["signatures"] = len(list(signatures_path.glob("*out"))) > 0
    processing["brainager"] = len(list(brainager_path.glob("*out"))) > 0

    return processing


def find_heudiconv_outputs(bids_dir: Path):

    search_scans = {
        "T1 Received": len(list(bids_dir.glob("sub*/ses*/anat/*T1w.nii.gz")))
        > 0,
        "DWI Received": len(list(bids_dir.glob("sub*/ses*/dwi/*dwi.nii.gz")))
        > 0,
        "fMRI Individualized Pressure Received": len(
            list(bids_dir.glob("sub*/ses*/func/*cuff*01*.nii.gz"))
        )
        > 0,
        "fMRI Standard Pressure Received": len(
            list(bids_dir.glob("sub*/ses*/func/*cuff*02*.nii.gz"))
        )
        > 0,
        "1st Resting State Received": len(
            list(bids_dir.glob("sub*/ses*/func/*rest*01*.nii.gz"))
        )
        > 0,
        "2nd Resting State Received": len(
            list(bids_dir.glob("sub*/ses*/func/*rest*02*.nii.gz"))
        )
        > 0,
    }
    return search_scans


def main(dst: Path):

    list_of_dict = []
    uploaded = get_uploaded()

    for row in uploaded.itertuples():
        bids_path = (
            Path(
                "/corral-secure/projects/A2CPS/community/resources/imaging/traveling"
            )
            / SITE_LONG[row.site]  # type: ignore
            / "bids"
            / f"{row.visit}{row.subject_id}"
        )
        processing = find_outputs(bids_path)

        scans_indicated = {
            "site": row.site,
            "subject_id": row.subject_id,
            "visit": row.visit,
        }

        processed_scans = find_heudiconv_outputs(bids_path)
        bool_dicts = {**processed_scans, **processing}
        str_dicts = {k: str(int(v)) for k, v in bool_dicts.items()}

        scan_report = {**scans_indicated, **str_dicts}

        # remove preprocessing if scans not indicated
        if (
            scan_report.get("fmriprep_rest") == "na"
            and scan_report.get("fmriprep_cuff") == "na"
        ):
            scan_report["fcn"] = "na"
            scan_report["signatures"] = "na"

        list_of_dict.append(scan_report)

    pd.DataFrame(list_of_dict).to_csv(dst, index=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("dst", type=Path)
    args = parser.parse_args()
    main(dst=args.dst)
