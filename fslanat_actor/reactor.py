import copy
import dataclasses
import json
import logging
import os
from typing import Any
from pathlib import Path

import pandas as pd
import ibis
from ibis import _

from tapipy import actors, util, errors
from tapipy.tapis import Tapis

JOB = Path("/opt/job.json")

SITE_LONG = {
    "NS": "NS_northshore",
    "UI": "UI_uic",
    "UC": "UC_uchicago",
    "UM": "UM_umichigan",
    "SH": "SH_spectrum_health",
    "WS": "WS_wayne_state",
}


@dataclasses.dataclass
class Context(util.AttrDict):
    raw_message: str
    content_type: str
    actor_repo: str
    actor_name: str
    actor_id: str
    actor_dbid: str
    execution_id: str
    worker_id: str
    username: str
    state: str
    raw_message_parse_log: str
    message_dict: dict[str, Any]


def actors_get_client() -> Tapis:
    """
    Returns a pre-authenticated Tapis client using the abaco environment variables.
    """
    # if we have an access token, use that:
    if token := os.environ.get("_abaco_access_token"):
        tp = Tapis(
            base_url=os.environ.get("_abaco_api_server", default="").strip("/"),
            access_token=token,
        )  # type: ignore
    elif server := os.environ.get("_abaco_api_server"):
        # otherwise, create a client with a fake JWT. this will only work if the actor
        # supplies its own token to itself via a config object or the message, etc.
        tp = Tapis(base_url=server.strip("/"), jwt="123")  # type: ignore
    else:
        raise errors.BaseTapyException(
            "Unable to instantiate a Tapis client: no token found."
        )
    return tp


def get_runlist(msg: dict) -> list[tuple[str, str]]:
    ilog: pd.DataFrame = (
        ibis.api._memtable_from_dataframe(msg)
        .select("site", "subject_id", "visit", "bids", "fslanat")
        .filter(_.fslanat == 0)  # type: ignore
        .filter(_.bids == 1)  # type: ignore
        .mutate(subject_id=_.subject_id.cast("str"))  # type: ignore
        .mutate(
            sublong=_.site.concat(_.subject_id, _.visit),  # type: ignore
            sitelong=_.site.cases(tuple(SITE_LONG.items())),  # type: ignore
        )
        .mutate(OUTPUT_DIR=_.sitelong + "/fslanat/" + _.sublong)  # type: ignore
        .mutate(
            ANATS=lambda x: "/corral-secure/projects/A2CPS/products/mris/"
            + x.sitelong
            + "/bids/"
            + x.sublong
            + "/sub-"
            + x.subject_id
            + "/ses-"
            + x.visit
            + "/anat"
            + "/sub-"
            + x.subject_id
            + "_ses-"
            + x.visit
            + "_T1w.nii.gz"  # type: ignore
        )
        .execute()
    )
    return [
        (x, y) for x, y in zip(ilog.ANATS.to_list(), ilog.OUTPUT_DIR.to_list())
    ]


def set_anat(job: dict, arg: str) -> dict:
    job2 = copy.deepcopy(job)
    job2.get("parameterSet").get("appArgs")[0] = {"name": "ANATS", "arg": arg}  # type: ignore
    return job2


def set_outputdir(job: dict, arg: str) -> dict:
    job2 = copy.deepcopy(job)
    job2.get("parameterSet").get("appArgs")[1] = {"name": "OUTPUT_DIR", "arg": arg}  # type: ignore
    return job2


def main() -> None:
    context: Context = actors.get_context()  # type: ignore
    print(json.dumps(context, indent=4))

    runlist = get_runlist(msg=context.message_dict)
    if not len(runlist):
        logging.warning("Did not find any jobs to submit")
        return

    with open(JOB, "r") as f:
        job = json.load(f)

    job = set_anat(job, "--anats " + " ".join(x[0] for x in runlist))
    job = set_outputdir(job, "--output-dir " + " ".join(x[1] for x in runlist))

    print(json.dumps(job, indent=4))

    client = actors_get_client()

    try:
        client.jobs.submitJob(**job)  # type: ignore
    except Exception as e:
        logging.error(f"encountered while trying to submit job: {e}")


if __name__ == "__main__":
    main()
