import datetime
import logging
import json
from pathlib import Path

from ibis import _

from mri_utils import actor, config, models

FAILUREBOT_ADDRESS_SECRET_NAME = "FAILUREBOT_ADDRESS_SECRET_NAME"
FAILUREBOT_ADDRESS_SECRET_KEY = "FAILUREBOT_ADDRESS_SECRET_KEY"

# within docker container
JOB = Path("/opt/job.json")

# on TACC
# can be changed from this default by specifying "ILOG" in actor message
ILOG = "/corral-secure/projects/A2CPS/shared/urrutia/imaging_report/imaging_log.csv"

# numbers for ls6; tested at
# /corral-secure/projects/A2CPS/shared/psadil/jobs/mriqc-upgrade-cores
N_SUBS_PER_NODE = 20

# for ls
MAX_NODES_PER_JOB = 64

# can change by incoming message by specifying "MAXJOBS"
MAXJOBS = N_SUBS_PER_NODE * MAX_NODES_PER_JOB

# amount of time required to copy one sub from /tmp -> /corral-secure
# this will be used to terminate the job early in case of
# prolonged runtime
N_SEC_TO_COPY_ONE_SUB = 10

# NOTE: the job.json parameters --n-workers and --mem-mb are not modified
#       so, best to set them according to the maximum number of subs
#       that could be run on a single node

class MRIQCReactor(models.Reactor):

    def get_runlist(self) -> list[tuple[str, str]]:
        rundef = (
            self.ilog.select("site", "subject_id", "visit", "bids", "mriqc")
            .filter(_.bids == 1)  # type: ignore
            .filter(_.mriqc == 0)  # type: ignore
            .mutate(
                sublong=_.site.concat(_.subject_id, _.visit),  # type: ignore
                sitelong=_.site.cases(tuple(config.SITE_LONG.items())),  # type: ignore
            )
            .mutate(OUTPUT_DIR=_.sitelong + "/mriqc/" + _.sublong)  # type: ignore
            .mutate(
                INPUT_DIR=lambda x: "/corral-secure/projects/A2CPS/products/mris/"
                + x.sitelong
                + "/bids/"
                + x.sublong  # type: ignore
            )
            .order_by(["visit", "subject_id"])  # ensure V1 run before V3
            .execute()
        )

        runlist = [
            (x, y)
            for x, y in zip(
                rundef.INPUT_DIR.to_list(), rundef.OUTPUT_DIR.to_list()
            )
        ]
        return runlist[:self.context.message_dict.get("MAXJOBS", self.MAXJOBS)]


    def submit(self) -> None:
        print(json.dumps(self.context, indent=4))

        runlist = self.get_runlist()
        n_jobs = len(runlist)
        if not n_jobs:
            logging.warning("Did not find any jobs to submit")
            return

        with open(self.JOB) as f:
            job = json.load(f)

        n_nodes = self.get_node_count(n_jobs)
        job = actor.set_app_arg(
            job,
            0,
            name="INPUT_DIRS",
            arg="--input-dirs " + " ".join(x[0] for x in runlist),
        )
        job = actor.set_app_arg(
            job,
            1,
            name="OUTPUT_DIRS",
            arg="--output-dirs " + " ".join(x[1] for x in runlist),
        )

        job = actor.set_env_var(
            job,
            arg_pos=0,
            key="MIN_ARCHIVE_DURATION",
            value=str(n_jobs * self.N_SEC_TO_COPY_ONE_SUB),
        )

        actor.set_key_value(
            job, key="maxMinutes", value=self.context.message_dict.get("maxMinutes")
        )
        actor.set_key_value(
            job,
            key="name",
            value=self.job_name,
        )

        image = self.client.apps.getApp(  # type: ignore
            appId=job["appId"], appVersion=job["appVersion"]
        ).containerImage

        actor.set_key_value(
            job,
            key="cmdPrefix",
            value=actor.get_cmd_prefix(n_jobs=n_jobs, image=image),
        )

        # corresponds to SBATCH option -N,--nodes, SLURM_JOB_NUM_NODES
        actor.set_key_value(job, key="nodeCount", value=n_nodes)

        # corresponds to SBATCH option -n,--ntask, SLURM_NPROCS, SLURM_NTASKS
        # all nodes will have all cores available, but this needs to be set for ibrun
        actor.set_key_value(
            job, key="coresPerNode", value=self.N_SUBS_PER_NODE
        )

        if self.context.message_dict.get("SKIP_FAILUREBOT", False):
            job.pop("subscriptions", None)
        else:
            job = actor.set_subscription_url(job, arg=self.failurebot_url)

        print(json.dumps(job, indent=4))

        try:
            submitted = self.client.jobs.submitJob(**job)  # type: ignore
            print(submitted.uuid)
        except Exception as e:
            logging.exception(f"encountered while trying to submit job: {e}")



def main() -> None:
    reactor = MRIQCReactor(
        job_name=f"mriqc-{datetime.datetime.today().strftime('%Y-%m-%d')}",
        FAILUREBOT_ADDRESS_SECRET_KEY=FAILUREBOT_ADDRESS_SECRET_KEY,
        FAILUREBOT_ADDRESS_SECRET_NAME=FAILUREBOT_ADDRESS_SECRET_NAME,
        N_SUBS_PER_NODE=N_SUBS_PER_NODE,
        N_SEC_TO_COPY_ONE_SUB=N_SEC_TO_COPY_ONE_SUB,
        ILOG=Path(ILOG),
        JOB=JOB,
        MAXJOBS=MAXJOBS,
    )
    reactor.submit()


if __name__ == "__main__":
    main()
