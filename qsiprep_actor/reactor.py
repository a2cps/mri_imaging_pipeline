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
# ILOG = "/corral-secure/projects/A2CPS/community/reports/imaging/imaging-log-latest.csv"
ILOG = "/corral-secure/projects/A2CPS/system/cronjob/imaging_report/report.csv"

# can be overridden by incoming message
MAXJOBS = 1000

# assume deployed on frontera
# # https://docs.tacc.utexas.edu/hpc/frontera/#table1
# N_SUBS_PER_NODE = 7
# N_CORES_PER_NODE = 56  # this is total number for a node
# MEM_PER_NODE = 192000  # MB

# numbers for ls6
N_SUBS_PER_NODE = 12
N_CORES_PER_NODE = 128  # this is total number for a node
MEM_PER_NODE = 256000  # MB

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


# context=Context(raw_message="", content_type="", actor_repo="", actor_name="", actor_dbid="", execution_id="", worker_id="", username="", state="", raw_message_parse_log="", message_dict={"a":""}, actor_id="")


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
    return ibis.memtable(
        pd.read_csv(
            io.BytesIO(ilog),
            na_values=["na", ""],
            dtype={"subject_id": str, "qsiprep": pd.Int64Dtype()},
        )
    )


def get_runlist(ilog: Table, maxjobs: int = MAXJOBS) -> list[tuple[str, str]]:
    rundef: pd.DataFrame = (
        ilog.select("site", "subject_id", "visit", "bids", "qsiprep")
        .filter(_.qsiprep == 0)  # type: ignore
        .filter(_.bids == 1)  # type: ignore
        .mutate(
            sublong=_.site.concat(_.subject_id, _.visit),  # type: ignore
            sitelong=_.site.cases(tuple(SITE_LONG.items())),  # type: ignore
        )
        .mutate(OUTDIR=_.sitelong + "/qsiprep/" + _.sublong)  # type: ignore
        .mutate(
            BIDSDIR=lambda x: "/corral-secure/projects/A2CPS/products/mris/"
            + x.sitelong
            + "/bids/"  # type: ignore
            + x.sublong
        )
        .execute()
    )
    runlist = [
        (x, y)
        for x, y in zip(rundef.BIDSDIR.to_list(), rundef.OUTDIR.to_list())
    ]
    return runlist[:maxjobs]


def get_node_count(n_jobs: int) -> int:
    return math.ceil(n_jobs / N_SUBS_PER_NODE)


def get_cmd_prefix(image: str, n_jobs: int) -> str:
    return f"apptainer pull {image} && ibrun -n {n_jobs}"


def set_bidsdir(job: dict, arg: str) -> None:
    job.get("parameterSet").get("appArgs")[0] = {"name": "BIDSDIR", "arg": arg}  # type: ignore


def set_outdir(job: dict, arg: str) -> None:
    job.get("parameterSet").get("appArgs")[1] = {"name": "OUTDIR", "arg": arg}  # type: ignore


def set_nthreads(job: dict, n_nodes: int, n_jobs: int) -> None:
    if n_nodes > 1:
        n_threads = math.floor(N_CORES_PER_NODE / N_SUBS_PER_NODE)
    else:
        n_threads = math.floor(N_CORES_PER_NODE / n_jobs)

    job.get("parameterSet").get("appArgs")[2] = {"name": "NTHREADS", "arg": f"--nthreads {n_threads}"}  # type: ignore


def set_mem_mb(job: dict, n_nodes: int, n_jobs: int) -> None:
    if n_nodes > 1:
        n_threads = math.floor(MEM_PER_NODE / N_SUBS_PER_NODE)
    else:
        n_threads = math.floor(MEM_PER_NODE / n_jobs)

    job.get("parameterSet").get("appArgs")[3] = {"name": "MEM_MB", "arg": f"--mem-mb {n_threads}"}  # type: ignore


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


def set_subscription_url(job: dict, arg: str) -> None:
    job.get("subscriptions")[0].get("deliveryTargets")[0].update(  # type: ignore
        {"deliveryAddress": arg}
    )


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
    set_bidsdir(job, "--bidsdir " + " ".join(x[0] for x in runlist))
    set_outdir(job, "--outdir " + " ".join(x[1] for x in runlist))
    set_nthreads(job, n_nodes=n_nodes, n_jobs=n_jobs)
    set_mem_mb(job, n_nodes=n_nodes, n_jobs=n_jobs)
    set_key_value(
        job, key="maxMinutes", value=context.message_dict.get("maxMinutes")
    )
    set_key_value(
        job,
        key="name",
        value=f"qsiprep-{datetime.datetime.today().strftime('%Y-%m-%d')}",
    )
 
    # get image
    image = client.apps.getApp(appId=job["appId"], appVersion=job["appVersion"]).containerImage
    set_key_value(job, key="cmdPrefix", value=get_cmd_prefix(image, n_jobs))

    # corresponds to SBATCH option -N,--nodes, SLURM_JOB_NUM_NODES
    set_key_value(job, key="nodeCount", value=n_nodes)

    # corresponds to SBATCH option -n,--ntask, SLURM_NPROCS, SLURM_NTASKS
    # all nodes will have all cores available, but this needs to be set for ibrun
    set_key_value(
        job,
        key="coresPerNode",
        value=N_SUBS_PER_NODE
    )

    failurebot_url = get_failurebot_url(client=client)
    set_subscription_url(job, arg=failurebot_url)

    print(json.dumps(job, indent=4))

    try:
        submitted = client.jobs.submitJob(**job)  # type: ignore
        print(submitted.uuid)
    except Exception as e:
        logging.error(f"encountered while trying to submit job: {e}")


if __name__ == "__main__":
    main()
