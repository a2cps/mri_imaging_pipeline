import datetime
import json
import logging
from pathlib import Path

import polars as pl
from mri_actor_utils import config, models

# within docker container
JOB = Path("/opt/job.json")

N_SUBS_PER_NODE = 20

# for ls
MAX_NODES_PER_JOB = 1

# can change by incoming message by specifying "MAXJOBS"
MAXJOBS = N_SUBS_PER_NODE * MAX_NODES_PER_JOB

N_SEC_TO_COPY_ONE_SUB = 180


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


class FSLAnatReactor(models.Reactor):
    def get_runlist(self) -> dict[str, list[str]]:
        rundef = (
            self.ilog
            # exclude rows that were already processed
            .filter(pl.col("fslanat") == 0)
            .filter(pl.col("bids") == 1)
            .with_columns(
                sublong=pl.concat_str(
                    pl.col("site"), pl.col("subject_id"), pl.col("visit")
                ),
                sitelong=pl.col("site").replace(config.SITE_LONG),
            )
            .with_columns(
                INPUT_DIRS=pl.concat_str(
                    pl.lit("/corral-secure/projects/A2CPS/products/mris/"),
                    pl.col("sitelong"),
                    pl.lit("/bids/"),
                    pl.col("sublong"),
                ),
                PRECROP=pl.when(pl.col("sublong").is_in(PRECROP_SUBS))
                .then(pl.lit("True"))
                .otherwise(pl.lit("False")),
                MASK_HIGH_VOXELS=pl.when(pl.col("sublong").is_in(MASK_HIGH_VOXELS_SUBS))
                .then(pl.lit("True"))
                .otherwise(pl.lit("False")),
            )
            .sort(
                "visit", "Surgery Week", "subject_id"
            )  # ensure V1 run before V3, and do oldest scans
        )
        runlist: dict[str, list[str]] = {
            "INPUT_DIRS": rundef.select(pl.col("INPUT_DIRS")).to_series().to_list(),
            "PRECROP": rundef.select(pl.col("PRECROP")).to_series().to_list(),
            "MASK_HIGH_VOXELS": rundef.select(pl.col("MASK_HIGH_VOXELS"))
            .to_series()
            .to_list(),
        }

        return {
            k: v[: self.context.message_dict.get("MAXJOBS", self.MAXJOBS)]
            for k, v in runlist.items()
        }

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
            value="--input-dirs " + " ".join(runlist["INPUT_DIRS"]),
        )
        self.set_app_arg(
            name="PRECROP",
            value="--precrop " + " ".join(runlist["PRECROP"]),
        )
        self.set_app_arg(
            name="MASK_HIGH_VOXELS",
            value="--mask-high-voxels " + " ".join(runlist["MASK_HIGH_VOXELS"]),
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

        print(self.job.model_dump_json(indent=4, exclude_unset=True, exclude_none=True))

        try:
            submitted = self.client.jobs.submitJob(  # type: ignore
                **self.job.model_dump(exclude_unset=True, exclude_none=True)
            )
            print(submitted.uuid)
        except Exception:
            logging.exception("encountered while trying to submit job")


def main() -> None:
    FSLAnatReactor(
        job_name=f"fslanat-{datetime.datetime.today().strftime('%Y-%m-%d')}",
        N_SUBS_PER_NODE=N_SUBS_PER_NODE,
        N_SEC_TO_COPY_ONE_SUB=N_SEC_TO_COPY_ONE_SUB,
        JOB=JOB,
        MAXJOBS=MAXJOBS,
    ).submit()


if __name__ == "__main__":
    main()
