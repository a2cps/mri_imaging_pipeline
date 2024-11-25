import datetime
import json
import logging
from pathlib import Path

import polars as pl
from mri_actor_utils import config, models

# within docker container
JOB = Path("/opt/job.json")

# numbers for ls6
N_SUBS_PER_NODE = 30

# for ls
MAX_NODES_PER_JOB = 32

# can be overridden by incoming message
MAXJOBS = N_SUBS_PER_NODE * MAX_NODES_PER_JOB

# amount of time required to copy one sub from /tmp -> /corral-secure
# this will be used to terminate the job early in case of
# prolonged runtime
N_SEC_TO_COPY_ONE_SUB = 60


class CAT12Reactor(models.Reactor):
    def get_runlist(self) -> list[str]:
        rundef = (
            self.ilog.filter(pl.col("T1 Received") == 1)
            .filter(pl.col("bids") == 1)
            .filter(pl.col("cat12") == 0)
            .with_columns(
                sublong=pl.concat_str(
                    pl.col("site"), pl.col("subject_id"), pl.col("visit")
                ),
                sitelong=pl.col("site").replace(config.SITE_LONG),
            )
            .with_columns(
                INPUT_DIR=pl.concat_str(
                    pl.lit("/corral-secure/projects/A2CPS/products/mris/"),
                    pl.col("sitelong"),
                    pl.lit("/bids/"),
                    pl.col("sublong"),
                )
            )
            .sort(
                "visit", "Surgery Week", "subject_id"
            )  # ensure V1 run before V3, and do oldest scans
        )

        runlist = [
            x for x in rundef.select(pl.col("INPUT_DIR")).to_series().to_list()
        ]
        return runlist[
            : self.context.message_dict.get("MAXJOBS", self.MAXJOBS)
        ]

    def submit(self) -> None:
        print(json.dumps(self.context, indent=4))

        runlist = self.get_runlist()
        n_jobs = len(runlist)
        if not n_jobs:
            logging.warning("Did not find any jobs to submit")
            return

        n_nodes = self.get_node_count(n_jobs)
        self.set_app_arg(
            name="INPUT_DIRS",
            value="--input-dirs " + " ".join(x for x in runlist),
        )

        self.set_env_var(
            key="MIN_ARCHIVE_DURATION",
            value=str(n_jobs * self.N_SEC_TO_COPY_ONE_SUB),
        )
        if max_minutes := self.context.message_dict.get("maxMinutes"):
            self.job.maxMinutes = max_minutes

        self.job.name = self.job_name

        self.set_cmd_prefix(image=self.container_image, n_jobs=n_jobs)

        # corresponds to SBATCH option -N,--nodes, SLURM_JOB_NUM_NODES
        self.job.nodeCount = n_nodes

        # corresponds to SBATCH option -n,--ntask, SLURM_NPROCS, SLURM_NTASKS
        # all nodes will have all cores available, but this needs to be set for ibrun
        self.job.coresPerNode = self.N_SUBS_PER_NODE

        if self.context.message_dict.get("SKIP_FAILUREBOT", False):
            self.job.subscriptions = None
        else:
            self.set_subscription_url(url=self.failurebot_url)

        if FAILURE_LOG_DST := self.context.message_dict.get("FAILURE_LOG_DST"):
            self.set_env_var(key="FAILURE_LOG_DST", value=FAILURE_LOG_DST)

        print(
            self.job.model_dump_json(
                indent=4, exclude_unset=True, exclude_none=True
            )
        )

        try:
            submitted = self.client.jobs.submitJob(  # type: ignore
                **self.job.model_dump(exclude_unset=True, exclude_none=True)
            )
            print(submitted.uuid)
        except Exception:
            logging.exception("encountered while trying to submit job")


def main() -> None:
    reactor = CAT12Reactor(
        job_name=f"cat12-{datetime.datetime.today().strftime('%Y-%m-%d')}",
        N_SUBS_PER_NODE=N_SUBS_PER_NODE,
        N_SEC_TO_COPY_ONE_SUB=N_SEC_TO_COPY_ONE_SUB,
        JOB=JOB,
        MAXJOBS=MAXJOBS,
    )
    reactor.submit()


if __name__ == "__main__":
    main()
