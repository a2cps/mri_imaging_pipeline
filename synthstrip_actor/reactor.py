import datetime
import itertools
import json
from pathlib import Path

import polars as pl
from mri_actor_utils import config, models

# within docker container
JOB = Path("/opt/job.json")

# numbers for ls6
# even 8 subs uses to much of /tmp
N_SUBS_PER_NODE = 64

# for ls
MAX_NODES_PER_JOB = 32

# can be overridden by incoming message
MAXJOBS = N_SUBS_PER_NODE * MAX_NODES_PER_JOB


# amount of time required to copy one sub from /tmp -> /corral-secure
# this will be used to terminate the job early in case of
# prolonged runtime
N_SEC_TO_COPY_ONE_SUB = 180

# NOTE: the job.json parameters --n-workers and --mem-mb are not modified
#       so, best to set them according to the maximum number of subs
#       that could be run on a single node


class SynthStripReactor(models.Reactor):
    def get_runlist(self) -> tuple[list[str]]:
        rundef = (
            self.ilog.filter(pl.col("T1 Received") == 1)
            .filter(pl.col("bids") == 1)
            .filter(pl.col("synthstrip") == 0)
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
                )
            )
            .sort(
                "visit", "Surgery Week", "subject_id"
            )  # ensure V1 run before V3, and do oldest scans
        )

        runlist = (
            rundef.select(pl.col("INPUT_DIRS"))
            .to_series()
            .to_list()[: self.maxjobs * self.n_submissions]
        )
        return runlist

    def parse_and_submit(self) -> None:
        print(json.dumps(self.context, indent=4))

        runlist = self.get_runlist()
        for r, input_dirs in enumerate(itertools.batched(runlist[0], self.maxjobs)):
            n_jobs = len(input_dirs)
            self.set_app_arg(
                name="INPUT_DIRS", value="--input-dirs " + " ".join(input_dirs)
            )
            self.job.name = f"{self.job_name}-{r}"

            self.set_common(n_jobs=n_jobs)
            self.submit()


def main() -> None:
    SynthStripReactor(
        job_name=f"synthstrip-{datetime.datetime.today().strftime('%Y-%m-%d')}",
        N_SUBS_PER_NODE=N_SUBS_PER_NODE,
        N_SEC_TO_COPY_ONE_SUB=N_SEC_TO_COPY_ONE_SUB,
        JOB=JOB,
        MAXJOBS=MAXJOBS,
    ).parse_and_submit()


if __name__ == "__main__":
    main()
