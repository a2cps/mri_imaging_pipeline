import datetime
import logging
import json
from pathlib import Path

import polars as pl

from mri_actor_utils import config, models

FAILUREBOT_ADDRESS_SECRET_NAME = "FAILUREBOT_ADDRESS_SECRET_NAME"
FAILUREBOT_ADDRESS_SECRET_KEY = "FAILUREBOT_ADDRESS_SECRET_KEY"

# within docker container
JOB = Path("/opt/job.json")

# on TACC
# can be changed from this default by specifying "ILOG" in actor message
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

# NOTE: the job.json parameters --n-workers and --mem-mb are not modified
#       so, best to set them according to the maximum number of subs
#       that could be run on a single node


class FMRIPrepReactor(models.Reactor):

    def get_runlist(self) -> list[tuple[str, str]]:
        rundef = (
            self.ilog.rename(
                {
                    "fMRI Individualized Pressure Received": "CUFF1",
                    "fMRI Standard Pressure Received": "CUFF2",
                    "1st Resting State Received": "REST1",
                    "2nd Resting State Received": "REST2",
                }
            )
            .filter(pl.col("T1 Received") == 1)
            .filter(pl.col("bids") == 1)
            .filter(pl.col("fmriprep") == 0)
            .with_columns(
                sublong=pl.concat_str(
                    pl.col("site"), pl.col("subject_id"), pl.col("visit")
                ),
                sitelong=pl.col("site").replace(config.SITE_LONG),
                ANAT_ONLY=(
                    (pl.col("CUFF1") == 0)
                    & (pl.col("CUFF2") == 0)
                    & (pl.col("REST1") == 0)
                    & (pl.col("REST2") == 0)
                ),
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
                "visit", "acquisition_week"
            )  # ensure V1 run before V3, and do oldest scans
        )

        runlist = [
            (x, str(z))
            for x, z in zip(
                rundef.select(pl.col("INPUT_DIR")).to_series().to_list(),
                rundef.select(pl.col("ANAT_ONLY")).to_series().to_list(),
            )
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
            value="--input-dirs " + " ".join(x[0] for x in runlist),
        )
        self.set_app_arg(
            name="ANAT_ONLY",
            value="--anat-only " + " ".join(x[1] for x in runlist),
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
            self.set_env_var(
                key="FAILURE_LOG_DST",
                value=FAILURE_LOG_DST,
            )

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
        except Exception as e:
            logging.exception(f"encountered while trying to submit job: {e}")


def main() -> None:
    reactor = FMRIPrepReactor(
        job_name=f"fmriprep-{datetime.datetime.today().strftime('%Y-%m-%d')}",
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
