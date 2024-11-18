import copy
import dataclasses
import datetime
import io
import json
import logging
import os
from pathlib import Path
from typing import Any, Sequence

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
# ILOG = "/corral-secure/projects/A2CPS/community/reports/imaging/imaging-log-latest.csv"
ILOG = "corral-secure/projects/A2CPS/shared/urrutia/imaging_report/imaging_log.csv"

# can be overriden by incoming message
_MAXJOBS = 20

SITE_LONG = {
    "NS": "NS_northshore",
    "UI": "UI_uic",
    "UC": "UC_uchicago",
    "UM": "UM_umichigan",
    "SH": "SH_spectrum_health",
    "WS": "WS_wayne_state",
    "RU": "RU_rush",
}

# participants that cannot go through fslanat without
# having images cropped manually
PRECROP_SUBS = {
    "UC10066V1",
    "UC10119V1",
    "UC10147V1",
    "UC10153V1",
    "UC10244V3",
    "UC10315V3",
    "UC10335V1",
    "UC10335V3",
    "UC10363V1",
    "UC10372V1",
    "UC10411V1",
    "UC10416V1",
    "UC10483V1",
    "UC10506V3",
    "UC10513V1",
    "UC10518V3",
    "UC10610V1",
    "UC10610V3",
    "UC10643V1",
    "UC10643V3",
    "UC10732V3",
    "UC10757V1",
    "UC10758V1",
    "UC10766V1",
    "UC10766V3",
    "UC10785V3",
    "UC10789V1",
    "UC10789V3",
    "UC10804V1",
    "UC10810V1",
    "UC10821V3",
    "UC10828V3",
    "UC10844V1",
    "UC10864V1",
    "UC10864V3",
    "UC10867V1",
    "UC10880V1",
    "UC10926V1",
    "UC10949V1",
    "UC10965V1",
    "UC10965V3",
    "UC10972V1",
    "UC10976V3",
    "UC10983V1",
    "UC10983V3",
    "UC10990V3",
    "UC11000V3",
    "UC11001V1",
    "UC11001V3",
    "UC11006V1",
    "UC11006V3",
    "UC11022V1",
    "UC11022V3",
    "UC11027V3",
    "UC11028V1",
    "UC11058V1",
    "UC11078V1",
    "UC11099V1",
    "UC15011V3",
    "UC15032V1",
}

MASK_HIGH_VOXELS_SUBS = {
    "NS10932V3",
    "UI10390V1",
    "UI10459V1",
    "UI10485V3",
    "UI10667V3",
    "UI10852V1",
    "UM25299V1",
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


def get_ilog(client: Tapis) -> Table:
    ilog: bytes = client.files.getContents(  # type: ignore
        systemId="secure.ls6", path=str(ILOG)
    )
    return ibis.memtable(
        pd.read_csv(
            io.BytesIO(ilog),
            na_values="na",
            dtype={"subject_id": str, "fslanat": pd.Int64Dtype()},
        )
    )


def get_runlist(ilog: Table, maxjobs: int | None = _MAXJOBS) -> list[tuple[str, str]]:
    rundef: pd.DataFrame = (
        ilog.select("site", "subject_id", "visit", "bids", "fslanat")
        .filter(_.fslanat == 0)  # type: ignore
        .filter(_.bids == 1)  # type: ignore
        .mutate(
            sublong=_.site.concat(_.subject_id, _.visit),  # type: ignore
            sitelong=_.site.cases(tuple(SITE_LONG.items())),  # type: ignore
        )
        .mutate(OUTPUT_DIR=_.sitelong + "/fslanat/" + _.sublong)  # type: ignore
        .mutate(
            ANATS=lambda x: "/corral-secure/projects/A2CPS/products/mris/"
            + x.sitelong
            + "/bids/"
            + x.sublong  # type: ignore
        )
        .execute()
    )
    runlist = [
        (x, y) for x, y in zip(rundef.ANATS.to_list(), rundef.OUTPUT_DIR.to_list())
    ]
    return runlist[:maxjobs]


def set_inputdirs(job: dict, arg: str) -> dict:
    job2 = copy.deepcopy(job)
    job2.get("parameterSet").get("appArgs")[0] = {"name": "INPUT_DIRS", "arg": arg}  # type: ignore
    return job2


def set_outputdirs(job: dict, arg: str) -> dict:
    job2 = copy.deepcopy(job)
    job2.get("parameterSet").get("appArgs")[1] = {"name": "OUTPUT_DIRS", "arg": arg}  # type: ignore
    return job2


def set_maxminutes(job: dict, maxminutes: int | None = None) -> dict:
    job2 = copy.deepcopy(job)
    if maxminutes:
        job2["maxMinutes"] = maxminutes
    return job2


def set_name(job: dict) -> dict:
    job2 = copy.deepcopy(job)
    job2["name"] = f"fslanat-{datetime.datetime.today().strftime('%Y-%m-%d')}"
    return job2


def set_precrop(job: dict, outputdirs: Sequence[str]) -> dict:
    """Determine whether participants will undergo manual robustfov"""
    precrop = [outputdir in PRECROP_SUBS for outputdir in outputdirs]
    job2 = copy.deepcopy(job)
    job2.get("parameterSet").get("appArgs").append(  # type: ignore
        {
            "name": "PRECROP",
            "arg": "--precrop " + " ".join(str(x) for x in precrop),
        }
    )
    return job2


def set_mask_high_voxels(job: dict, outputdirs: Sequence[str]) -> dict:
    """Determine whether participants will have high intensity voxels masked"""
    mask_high_voxels = [outputdir in MASK_HIGH_VOXELS_SUBS for outputdir in outputdirs]
    job2 = copy.deepcopy(job)
    job2.get("parameterSet").get("appArgs").append(  # type: ignore
        {
            "name": "MASK_HIGH_VOXELS",
            "arg": "--mask-high-voxels " + " ".join(str(x) for x in mask_high_voxels),
        }
    )
    return job2


def get_failurebot_url(client) -> str:
    token: TapisResult = client.sk.readSecret(  # type: ignore
        secretType="user",
        secretName=FAILUREBOT_ADDRESS_SECRET_NAME,
        tenant=os.environ.get("_abaco_api_server")
        .split(".")[0]  # type: ignore
        .split("/")[-1],
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

    job = set_inputdirs(job, "--input-dirs " + " ".join(x[0] for x in runlist))
    job = set_outputdirs(job, "--output-dirs " + " ".join(x[1] for x in runlist))
    job = set_maxminutes(job, context.message_dict.get("maxMinutes"))
    job = set_name(job)
    job = set_precrop(job, [Path(x[1]).name for x in runlist])
    job = set_mask_high_voxels(job, [Path(x[1]).name for x in runlist])
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
