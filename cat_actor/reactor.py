import datetime
import itertools
import json
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
            .filter(pl.col("cat12-v4") == 0)
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
        runlist = rundef.select(pl.col("INPUT_DIR")).to_series().to_list()
        return runlist[: self.maxjobs * self.n_submissions]

    def parse_and_submit(self) -> None:
        print(json.dumps(self.context, indent=4))

        runlist = self.get_runlist()
        for r, run in enumerate(itertools.batched(runlist, self.maxjobs)):
            n_jobs = len(run)
            if not n_jobs:
                raise RuntimeError("Did not find any jobs to submit")

            self.set_app_arg(name="INPUT_DIRS", value="--input-dirs " + " ".join(run))
            self.job.name = f"{self.job_name}-{r}"

            self.set_common(n_jobs=n_jobs)
            self.submit()


def main() -> None:
    CAT12Reactor(
        job_name=f"cat12-{datetime.datetime.today().strftime('%Y-%m-%d')}",
        N_SUBS_PER_NODE=N_SUBS_PER_NODE,
        N_SEC_TO_COPY_ONE_SUB=N_SEC_TO_COPY_ONE_SUB,
        JOB=JOB,
        MAXJOBS=MAXJOBS,
    ).parse_and_submit()


if __name__ == "__main__":
    main()
