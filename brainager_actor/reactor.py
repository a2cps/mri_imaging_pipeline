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
import pandas as pd
from ibis import _
from ibis.expr.types.relations import Table
from tapipy import actors, errors, util
from tapipy.tapis import Tapis, TapisResult

FAILUREBOT_ADDRESS_SECRET_NAME = "FAILUREBOT_ADDRESS_SECRET_NAME"
FAILUREBOT_ADDRESS_SECRET_KEY = "FAILUREBOT_ADDRESS_SECRET_KEY"


# within docker container
JOB = Path("/opt/job.json")

# on TACC
ILOG = "/corral-secure/projects/A2CPS/shared/urrutia/imaging_report/imaging_log.csv"
#ILOG = "/corral-secure/projects/A2CPS/system/cronjob/imaging_report/report.csv"

# can be overriden by incoming message
_MAXJOBS = 500

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
    return ibis.memtable(pd.read_csv(io.BytesIO(ilog), na_values="na"))


def get_runlist(
    ilog: Table, maxjobs: int = _MAXJOBS
) -> list[tuple[str, str]]:
    rundef: pd.DataFrame = (
        ilog.select("site", "subject_id", "visit", "bids", "brainager")
        # exclude rows that were already processed
        .filter(_.brainager == 0)  # type: ignore
        # include rows bids ready
        .filter((_.bids == 1))  # type: ignore  
        .mutate(subject_id=_.subject_id.cast("str"))  # type: ignore
        .mutate(
            sublong=_.site.concat(_.subject_id, _.visit),  # type: ignore
            sitelong=_.site.cases(tuple(SITE_LONG.items())),  # type: ignore
        )
        .mutate(OUTPUT_DIR=_.sitelong + "/brainager/" + _.sublong)  # type: ignore
        .mutate(
            INPUT_DIR=lambda x: "/corral-secure/projects/A2CPS/products/mris/"
            + x.sitelong
            + "/bids/"
            + x.sublong  # type: ignore
        )
        .execute()
    )
    runlist = [
        (x, y)
        for x, y in zip(
            rundef.INPUT_DIR.to_list(), rundef.OUTPUT_DIR.to_list()
        )
    ]
    return runlist[:maxjobs]


def set_app_arg(job: dict, arg_pos: int, name: str, arg: str) -> dict:
    job2 = copy.deepcopy(job)
    job2.get("parameterSet").get("appArgs")[arg_pos] = {"name": name, "arg": arg}  # type: ignore
    return job2


def set_name(job: dict) -> dict:
    job2 = copy.deepcopy(job)
    job2["name"] = f"brainager-{datetime.today().strftime('%Y-%m-%d')}"  # type: ignore
    return job2


def set_maxminutes(job: dict, maxminutes: int | None = None) -> dict:
    job2 = copy.deepcopy(job)
    if maxminutes:
        job2["maxMinutes"] = maxminutes
    return job2


def get_failurebot_url(client) -> str:
    api_server = os.environ.get("_abaco_api_server")
    if not api_server:
        msg = "Unable to detect tapis tenant"
        raise RuntimeError(msg)

    token: TapisResult = client.sk.readSecret(  # type: ignore
        secretType="user",
        secretName=FAILUREBOT_ADDRESS_SECRET_NAME,
        tenant=api_server.split(".")[0].split("/")[-1],
        user=client.actors.get_actor(
            actor_id=os.environ.get("_abaco_actor_id")
        ).owner,
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

    job = set_app_arg(
        job,
        0,
        name="INPUT_DIRS",
        arg="--input-dirs " + " ".join(x[0] for x in runlist),
    )
    job = set_app_arg(
        job,
        1,
        name="OUTPUT_DIRS",
        arg="--output-dirs " + " ".join(x[1] for x in runlist),
    )
    job = set_maxminutes(
        job, context.message_dict.get("maxMinutes")
    )
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
