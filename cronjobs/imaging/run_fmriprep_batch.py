import argparse
import logging
from pathlib import Path
import re

import numpy as np
import pandas as pd

import pydantic

import agavepy

"""
This script either 1) produces the jsons that can be used to run fMRIPrep jobs,
or 2) directly submits the produced jobs (when called with the --submit flag). 

The jobs submitted will attempt to handle all participants that are both
ready for fMRIPrep but have not yet gone through fMRIPrep. Participants are processed
in "batches", with 1 batch running on one node, and each batch containing 5 participants.
Each batch is submitted as a separate job. 

There are 3 kinds of fMRIPrep jobs: anat, rest, and cuff. For a participant's rest
and cuff jobs to run, the anat job must have already finished successfully. When both
an anat and functional job (i.e., either cuff or rest) need to be run, only jobs for
the anat are created. No attempt is made to coordinate both anat and functional jobs.
It is up to the user (or chronjob) to submit the functional runs after the anat job
has finished (e.g., by re-running this script). 

The parameters for these jobs are set with the class JobParameters.
JobParameters roughly corresponds to the parameters as defined in app.json (
see also the ALLCAPS variables in the top-level scope, such as those that define
which directories will be bound in the singularity container)

JobDef corresponds to standard Tapis job JSONs. Instances of that class will
be submitted as jobs on TACC.

This script requires python >= 3.9
"""


# Number of participants to run per node
BATCH_SIZE = 5
# memory allocated to each job on a node
MEMMB = 38000
# number of threads allocated to each job on a node
NTHREADS = 11

# Location of Imaging Log on TACC
ILOG_ = Path(
    "/corral-secure/projects/A2CPS/community/reports/imaging/imaging-log-latest.csv"
)

BINDDIR = Path("/corral-secure/projects/A2CPS")
ARCHIVE = BINDDIR / "products" / "mris"

SITE_KEY = {
    "NS": "NS_northshore",
    "SH": "SH_spectrum_health",
    "UC": "UC_uchicago",
    "UI": "UI_uic",
    "UM": "UM_umichigan",
    "WS": "WS_wayne_state",
}


class JobParameters(pydantic.BaseModel):
    # one element per participant
    BIDS_DIRECTORY: list[Path]
    OUTPUT_DIR: list[Path]
    FS_SUBJECTS_DIR: list[Path] = [Path("")]

    # fmriprep options shared for all runs
    ANAT_ONLY: bool = True
    HEAD_MOTION: str = ""
    ICA_AROMA_USE: bool = False
    CIFTI_OUTPUT: str = ""
    FS_NO_RECONALL: bool = False
    ICA_AROMA_USE: bool = False
    ICA_AROMA_DIMENSIONALITY: int = 0
    FD_SPIKE: float = 0
    BIDS_FILTER_FILE: str = ""
    SKIP_BIDS_VALIDATION: bool = True
    DUMMY_SCANS: int = 0

    # other tapis fmriprep_app parameters
    BINDDIR: Path = BINDDIR
    MEMMB: int = MEMMB
    NTHREADS: int = NTHREADS

    @classmethod
    def from_imagetype(cls, d: pd.DataFrame, image_type: str) -> "JobParameters":
        if image_type == "anat":
            updated = {"ANAT_ONLY": True, "CIFTI_OUTPUT": "91k"}
        elif image_type == "cuff":
            updated = {
                "ANAT_ONLY": False,
                "CIFTI_OUTPUT": "91k",
                "ICA_AROMA_USE": False,
                "FD_SPIKE": 0.9,
            }
        elif image_type == "rest":
            updated = {
                "ANAT_ONLY": False,
                "CIFTI_OUTPUT": "91k",
                "ICA_AROMA_USE": True,
                "ICA_AROMA_DIMENSIONALITY": -100,
                "FD_SPIKE": 0.3,
            }
        else:
            raise AssertionError

        params = d.to_dict(orient="list")
        params.update(updated)  # type: ignore

        return cls.parse_obj(params)


class JobDef(pydantic.BaseModel):
    name: str
    parameters: JobParameters
    archivePath: Path = ARCHIVE
    maxRunTime: str = "32:59:00"
    processorsPerNode: int = BATCH_SIZE
    nodeCount: int = 1
    archiveSystem: str = "a2cps.storage-frontera-protected"
    archiveOnAppError: bool = False
    archive: bool = True
    appId: str = "urrutia-fmriprep_LTS-20.2.4"
    systemId: str = "a2cps.hpc-frontera-protected"


def _gen_patientid(d: pd.DataFrame) -> pd.Series:
    return d.apply(lambda x: f"{x['site']}{x['subject_id']}{x['visit']}", axis=1)


def _gen_bidsdirectory(d: pd.DataFrame) -> pd.Series:
    return d.apply(
        lambda x: (
            BINDDIR / f"products/mris/{SITE_KEY.get(x['site'])}/bids/{x['patientid']}"
        ),  # type: ignore
        axis=1,
    )


def _gen_outputdirectory(d: pd.DataFrame, postpatient: str) -> pd.Series:
    return d.apply(
        lambda x: f"{SITE_KEY.get(x['site'])}/fmriprep/{x['patientid']}/{postpatient}",
        axis=1,
    )


def _gen_fsdirectory(d: pd.DataFrame) -> pd.Series:
    return d.apply(
        lambda x: (
            ARCHIVE / re.sub(r"cuff|rest", "anat/freesurfer", x["OUTPUT_DIR"])
        ),  # type: ignore
        axis=1,
    )


def _gen_jobtable(image_type: str) -> pd.DataFrame:
    if image_type == "anat":
        usecols = [
            "site",
            "subject_id",
            "visit",
            "T1 Received",
            "fmriprep_anat",
        ]
        quer = "`T1 Received` == 1 and fmriprep_anat == 0"
    elif image_type == "cuff":
        usecols = [
            "site",
            "subject_id",
            "visit",
            "fMRI Individualized Pressure Received",
            "fMRI Standard Pressure Received",
            "fmriprep_anat",
            "fmriprep_cuff",
        ]
        quer = "fmriprep_anat == 1 and ((`fMRI Individualized Pressure Received` == 1 or `fMRI Standard Pressure Received` == 1) and fmriprep_cuff == 0)"  # noqa: E501
    elif image_type == "rest":
        usecols = [
            "site",
            "subject_id",
            "visit",
            "1st Resting State Received",
            "2nd Resting State Received",
            "fmriprep_anat",
            "fmriprep_rest",
        ]
        quer = "fmriprep_anat == 1 and ((`1st Resting State Received` == 1 or `2nd Resting State Received` == 1) and fmriprep_rest == 0)"  # noqa: E501
    else:
        raise AssertionError

    d = pd.read_csv(ILOG_, usecols=usecols, na_values="na").query(quer)
    if not d.shape[0]:
        logging.warning(f"Did not find any {image_type} jobs to run.")
        return d
    d["patientid"] = _gen_patientid(d)
    d["BIDS_DIRECTORY"] = _gen_bidsdirectory(d)
    d["OUTPUT_DIR"] = _gen_outputdirectory(d, image_type)
    if image_type in ["rest", "cuff"]:
        d["FS_SUBJECTS_DIR"] = _gen_fsdirectory(d)
    return d


def main(submit: bool = False):
    ag = agavepy.Agave.restore()
    for image_type in ["anat", "rest", "cuff"]:
        jobtable = _gen_jobtable(image_type=image_type)

        for jobid, group in jobtable.groupby(np.arange(len(jobtable)) // BATCH_SIZE):
            parameters = JobParameters.from_imagetype(d=group, image_type=image_type)
            job_def = JobDef(
                name=f"fmriprep-{image_type}-{jobid}", parameters=parameters
            ).json()
            if submit:
                ag.jobs.submit(bold=job_def)
            else:
                print(job_def)
    return


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--submit", action=argparse.BooleanOptionalAction)
    args = parser.parse_args()
    main(submit=args.submit)
