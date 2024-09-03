import copy
import dataclasses
import datetime
import io
import json
import logging
import os
from pathlib import Path
import math
import typing

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

# numbers for ls6
# even 8 subs uses to much of /tmp
N_SUBS_PER_NODE = 6

# for ls
MAX_NODES_PER_JOB = 64

# can be overridden by incoming message
MAXJOBS = N_SUBS_PER_NODE * MAX_NODES_PER_JOB

# amount of time required to copy one sub from /tmp -> /corral-secure
# this will be used to terminate the job early in case of
# prolonged runtime
N_SEC_TO_COPY_ONE_SUB = 180

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
    message_dict: dict[str, typing.Any]


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
        systemId="secure.ls6", path=ILOG
    )
    return ibis.memtable(
        pd.read_csv(
            io.BytesIO(ilog),
            na_values=["na", ""],
            dtype={
                "subject_id": str,
                "fMRI Individualized Pressure Received": bool,
                "fMRI Standard Pressure Received": bool,
                "1st Resting State Received": bool,
                "2nd Resting State Received": bool,
            },
            parse_dates=["acquisition_week"],
        )
    )


def get_runlist(ilog: Table, maxjobs: int = MAXJOBS) -> list[tuple[str, str]]:
    rundef = (
        ilog.select(
            "site",
            "subject_id",
            "visit",
            "bids",
            "fmriprep",
            "fMRI Individualized Pressure Received",
            "fMRI Standard Pressure Received",
            "1st Resting State Received",
            "2nd Resting State Received",
        )
        .rename(
            {
                "CUFF1": "fMRI Individualized Pressure Received",
                "CUFF2": "fMRI Standard Pressure Received",
                "REST1": "1st Resting State Received",
                "REST2": "2nd Resting State Received",
            }
        )
        .filter(_.bids == 1)  # type: ignore
        .filter(_.fmriprep == 0)  # type: ignore
        .mutate(
            sublong=_.site.concat(_.subject_id, _.visit),  # type: ignore
            sitelong=_.site.cases(tuple(SITE_LONG.items())),  # type: ignore
            ANAT_ONLY=ibis.or_(_.CUFF1, _.CUFF2, _.REST1, _.REST2).negate(),
        )
        .mutate(
            INPUT_DIR=lambda x: "/corral-secure/projects/A2CPS/products/mris/"
            + x.sitelong
            + "/bids/"
            + x.sublong  # type: ignore
        )
        .order_by(["visit", "acquisition_week"])  # ensure V1 run before V3
        .execute()
    )

    runlist = [
        (x, str(z))
        for x, z in zip(
            rundef.INPUT_DIR.to_list(),
            rundef.ANAT_ONLY.to_list(),
        )
    ]
    return runlist[:maxjobs]


def get_node_count(n_jobs: int) -> int:
    return math.ceil(n_jobs / N_SUBS_PER_NODE)


def get_cmd_prefix(image: str, n_jobs: int) -> str:
    return f"ibrun -n 1 apptainer run {image} --help && ibrun -n {n_jobs}"


def set_app_arg(job: dict, arg_pos: int, name: str, arg: str) -> dict:
    job2 = copy.deepcopy(job)
    job2.get("parameterSet").get("appArgs")[arg_pos] = {"name": name, "arg": arg}  # type: ignore
    return job2


def set_env_var(job: dict, arg_pos: int, key: str, value: str) -> dict:
    job2 = copy.deepcopy(job)
    job2.get("parameterSet").get("envVariables")[arg_pos] = {"key": key, "value": value}  # type: ignore
    return job2


def set_key_value(job: dict, key: str, value: int | str | None = None) -> None:
    if value:
        job[key] = value


def get_failurebot_url(client) -> str:
    token: TapisResult = client.sk.readSecret(  # type: ignore
        secretType="user",
        secretName=FAILUREBOT_ADDRESS_SECRET_NAME,
        tenant=os.environ.get("_abaco_api_server")
        .split(".")[0]  # type: ignore
        .split("/")[-1],
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
        ilog=ilog, maxjobs=context.message_dict.get("maxjobs", MAXJOBS)
    )
    if not len(runlist):
        logging.warning("Did not find any jobs to submit")
        return

    with open(JOB, "r") as f:
        job = json.load(f)

    n_jobs = len(runlist)
    n_nodes = get_node_count(n_jobs)
    job = set_app_arg(
        job,
        0,
        name="INPUT_DIRS",
        arg="--input-dirs " + " ".join(x[0] for x in runlist),
    )
    job = set_app_arg(
        job,
        1,
        name="ANAT_ONLY",
        arg="--anat-only " + " ".join(x[1] for x in runlist),
    )

    job = set_env_var(
        job,
        arg_pos=0,
        key="MIN_ARCHIVE_DURATION",
        value=str(n_jobs * N_SEC_TO_COPY_ONE_SUB),
    )

    set_key_value(
        job, key="maxMinutes", value=context.message_dict.get("maxMinutes")
    )
    set_key_value(
        job,
        key="name",
        value=f"fmriprep-{datetime.datetime.today().strftime('%Y-%m-%d')}",
    )

    image = client.apps.getApp(
        appId=job["appId"], appVersion=job["appVersion"]
    ).containerImage
    set_key_value(
        job, key="cmdPrefix", value=get_cmd_prefix(n_jobs=n_jobs, image=image)
    )

    # corresponds to SBATCH option -N,--nodes, SLURM_JOB_NUM_NODES
    set_key_value(job, key="nodeCount", value=n_nodes)

    # corresponds to SBATCH option -n,--ntask, SLURM_NPROCS, SLURM_NTASKS
    # all nodes will have all cores available, but this needs to be set for ibrun
    set_key_value(job, key="coresPerNode", value=N_SUBS_PER_NODE)

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
