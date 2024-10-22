# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "pandas>=2.0",
# ]
# ///

import csv
import logging
import os
import re
import socket
from pathlib import Path

import pandas as pd


host = socket.gethostname()
logging.basicConfig(
    format=f"%(asctime)s | %(levelname)-8s | {host=} | %(message)s",
    level=logging.INFO,
)

FAILURE_LOG_DST = Path(
    os.environ.get(
        "FAILURE_LOG_DST",
        "/corral-secure/projects/A2CPS/products/development/mris/logs",
    )
)
MRIS = Path("/corral-secure/projects/A2CPS/products/mris")

SITES = [
    "NS_northshore",
    "RU_rush",
    "SH_spectrum_health",
    "UC_uchicago",
    "UI_uic",
    "UM_umichigan",
    "WS_wayne_state",
]

APP_STEPS = [
    "bids",
    "fslanat",
    "fmriprep",
    "mriqc",
    "qsiprep",
    "cat12",
    "brainager",
    "fcn",
    "signatures",
    "gift_rest",
]


def get_ses_from_sublong(sublong: str) -> str:
    maybe_ses = re.findall("V[13]", sublong)
    if not len(maybe_ses) > 0:
        msg = f"Unable to get ses from {sublong}"
        raise RuntimeError(msg)
    return maybe_ses[0]


def get_sub_from_sublong(sublong: str) -> str:
    maybe_sub = re.findall(r"\d{5}", sublong)
    if not len(maybe_sub) > 0:
        msg = f"Unable to get sub from {sublong}"
        raise RuntimeError(msg)
    return maybe_sub[0]


def check_output_failed(sublong: str, job) -> bool:
    return len(list((FAILURE_LOG_DST / job / sublong).glob("*.out"))) > 0


def check_output_exists(bids_path: Path, job: str) -> int:
    to_check = Path(str(bids_path).replace("bids", job))
    if len(list(to_check.glob("*out"))):
        out = 1
    else:
        logging.info(f"no {job} for {to_check.name}")
        out = 0
    return out


def get_acq_datetime(bids_path: Path):
    for scans_file in bids_path.rglob("*scans.tsv"):
        scans = pd.read_csv(scans_file, sep="\t", parse_dates=True)
        return scans[scans["filename"].str.contains("T1w")]["acq_time"][0]


def get_output_status(bids_path: Path):
    out = dict()
    for job in APP_STEPS:
        if check_output_failed(bids_path.name, job):
            out[job] = 2
        else:
            out[job] = check_output_exists(bids_path, job)

    return out


def find_heudiconv_outputs(bids_path: Path):
    for scans_file in bids_path.rglob("*scans.tsv"):
        scan_list = pd.read_csv(scans_file, sep="\t", usecols=["filename"])[
            "filename"
        ].to_list()

        search_scans = {
            "t1": re.compile(r"anat/[\w\W]+_T1w.nii.gz"),
            "dwi": re.compile(r"dwi/[\w\W]+_dwi.nii.gz"),
            "cuff1": re.compile(r"func/[\w\W]+cuff_run-01_bold.nii.gz"),
            "cuff2": re.compile(r"func/[\w\W]+cuff_run-02_bold.nii.gz"),
            "rest1": re.compile(r"func/[\w\W]+rest_run-01_bold.nii.gz"),
            "rest2": re.compile(r"func/[\w\W]+rest_run-02_bold.nii.gz"),
        }
        found_scans = dict()
        for scan_name, scan_pattern in search_scans.items():
            # If the scan is in our file list set to 1
            if any(scan_pattern.match(ascan) for ascan in scan_list):
                found_scans[f"{scan_name}_received"] = 1

    return found_scans


def main():
    list_of_dict = []

    for site in SITES:
        for bids_path in (MRIS / site / "bids").glob("*V[13]"):
            try:
                job_status = get_output_status(bids_path)

                scans_indicated = {
                    "record_id": get_sub_from_sublong(bids_path.name),
                    "protocol_id": get_ses_from_sublong(bids_path.name),
                    "acq_time": get_acq_datetime(bids_path),
                }

                processed_scans = find_heudiconv_outputs(bids_path)

                list_of_dict.append(
                    {
                        **job_status,
                        **processed_scans,
                        **scans_indicated,
                    }
                )

            except Exception:
                logging.exception(bids_path)

    pd.DataFrame(list_of_dict).drop_duplicates(inplace=True).to_csv(
        "report.csv", index=False, quoting=csv.QUOTE_MINIMAL
    )

    return


if __name__ == "__main__":
    main()
