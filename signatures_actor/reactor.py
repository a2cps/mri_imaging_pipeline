import copy
import dataclasses
import io
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import ibis
import ibis.selectors as s
import pandas as pd
from ibis import _
from ibis.expr.types.relations import Table
from tapipy import actors, errors, util
from tapipy.tapis import Tapis, TapisResult

# TODO
FAILUREBOT_ADDRESS_SECRET_NAME = "FAILUREBOT_ADDRESS_SECRET_NAME"
FAILUREBOT_ADDRESS_SECRET_KEY = "FAILUREBOT_ADDRESS_SECRET_KEY"


# within docker container
JOB = Path("/opt/job.json")

# on TACC
# ILOG = "/corral-secure/projects/A2CPS/community/reports/imaging/imaging-log-latest.csv"
ILOG = "/corral-secure/projects/A2CPS/system/cronjob/imaging_report/report.csv"

# can be overriden by incoming message
_MAXJOBS = 50

SITE_LONG = {
    "NS": "NS_northshore",
    "UI": "UI_uic",
    "UC": "UC_uchicago",
    "UM": "UM_umichigan",
    "SH": "SH_spectrum_health",
    "WS": "WS_wayne_state",
    "RU": "RU_rush",
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
            base_url=os.environ.get("_abaco_api_server", default="").strip(
                "/"
            ),
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


def get_ilog(client: Tapis) -> Table:
    ilog: bytes = client.files.getContents(  # type: ignore
        systemId="secure.corral", path=str(ILOG)
    )
    return ibis.memtable(pd.read_csv(io.BytesIO(ilog)))


def get_runlist(
    ilog: Table, maxjobs: int | None = _MAXJOBS
) -> list[tuple[str, str]]:
    rundef: pd.DataFrame = (
        ilog.select(
            "site",
            "subject_id",
            "visit",
            "fmriprep_rest",
            "fmriprep_cuff",
            "signatures",
        )
        .mutate(
            fmriprep_cuff=_.fmriprep_cuff.cast(str),  # type: ignore
            fmriprep_rest=_.fmriprep_rest.cast(str),  # type: ignore
        )
        # exclude rows that were already processed
        .filter(_.signatures == "0")  # type: ignore
        # include rows with both fmriprep jobs ready
        .filter(
            (
                ((_.fmriprep_cuff == "1") & (_.fmriprep_rest == "1"))
                | ((_.fmriprep_cuff == "1") & (_.fmriprep_rest == "na"))
                | ((_.fmriprep_cuff == "na") & (_.fmriprep_rest == "1"))
            )  # type: ignore
        )  # type: ignore
        .mutate(subject_id=_.subject_id.cast("str"))  # type: ignore
        .pivot_longer(
            s.c("fmriprep_cuff", "fmriprep_rest"),
            names_to="job",
            values_to="done",
        )
        # exclude rows where there wasn't an fmriprep job
        .filter(~(_.done == "na"))  # type: ignore
        .mutate(
            sublong=_.site.concat(_.subject_id, _.visit),  # type: ignore
            sitelong=_.site.cases(tuple(SITE_LONG.items())),  # type: ignore
            subjob=_.job.cases((("fmriprep_rest", "/rest"), ("fmriprep_cuff", "/cuff"))),  # type: ignore
        )
        .mutate(OUTPUT_DIR=_.sitelong + "/signatures/" + _.sublong)  # type: ignore
        .mutate(
            FMRIPREP_DIR=lambda x: "/corral-secure/projects/A2CPS/products/mris/"
            + x.sitelong
            + "/fmriprep/"
            + x.sublong
            + x.subjob
            + "/fmriprep"  # type: ignore
        )
        .execute()
    )
    runlist = [
        (x, y)
        for x, y in zip(
            rundef.FMRIPREP_DIR.to_list(), rundef.OUTPUT_DIR.to_list()
        )
    ]
    return runlist[:maxjobs]


def set_fmriprep(job: dict, arg: str) -> dict:
    job2 = copy.deepcopy(job)
    job2.get("parameterSet").get("appArgs")[0] = {"name": "FMRIPREP_DIR", "arg": arg}  # type: ignore
    return job2


def set_outputdir(job: dict, arg: str) -> dict:
    job2 = copy.deepcopy(job)
    job2.get("parameterSet").get("appArgs")[1] = {"name": "OUTPUT_DIR", "arg": arg}  # type: ignore
    return job2


def set_name(job: dict) -> dict:
    job2 = copy.deepcopy(job)
    job2["name"] = f"signatures-{datetime.today().strftime('%Y-%m-%d')}"  # type: ignore
    return job2


def set_maxminutes(job: dict, maxminutes: int | None = None) -> dict:
    job2 = copy.deepcopy(job)
    if maxminutes:
        job2["maxMinutes"] = maxminutes
    return job2


def get_failurebot_url(client) -> str:
    token: TapisResult = client.sk.readSecret(  # type: ignore
        secretType="user",
        secretName=FAILUREBOT_ADDRESS_SECRET_NAME,
        tenant=os.environ.get("_abaco_api_server").split('.')[0].split("/")[-1],
        user=client.actors.get_actor(actor_id=os.environ.get("_abaco_actor_id")).owner,
    )
    url: str | None = token.get("secretMap").get(FAILUREBOT_ADDRESS_SECRET_KEY)  # type: ignore
    if url is None:
        msg = f"unable to find {FAILUREBOT_ADDRESS_SECRET_KEY} in secretMap"
        raise AssertionError(msg)

    return url


def set_subscription_url(job: dict, arg: str) -> dict:
    job2 = copy.deepcopy(job)
    job2.get("subscriptions")[0].get("deliveryTargets")[0].update(  # type: ignore
        {"deliveryAddress": arg}
    )
    return job2


def main() -> None:
    context: Context = actors.get_context()  # type: ignore
    print(json.dumps(context, indent=4))

    client = actors_get_client()

    ilog = get_ilog(client=client)

    runlist = get_runlist(
        ilog=ilog, maxjobs=context.message_dict.get("maxjobs", _MAXJOBS)
    )
    if not len(runlist):
        logging.warning("Did not find any jobs to submit")
        return

    with open(JOB, "r") as f:
        job = json.load(f)

    job = set_fmriprep(
        job, "--fmriprep-dir " + " ".join(x[0] for x in runlist)
    )
    job = set_outputdir(job, "--output-dir " + " ".join(x[1] for x in runlist))
    job = set_maxminutes(job, context.message_dict.get("maxMinutes"))
    job = set_name(job)
    failurebot_url = get_failurebot_url(client=client)
    job = set_subscription_url(job, arg=failurebot_url)

    print(json.dumps(job, indent=4))

    try:
        submitted = client.jobs.submitJob(**job)  # type: ignore
        print(submitted.uuid)
    except Exception as e:
        logging.error(f"encountered while trying to submit job: {e}")


if __name__ == "__main__":
    main()
