import datetime
import itertools
import json
from pathlib import Path

import polars as pl
from mri_actor_utils import config, models

# within docker container
JOB = Path("/opt/job.json")


# numbers for ls6; tested at
# /corral-secure/projects/A2CPS/shared/psadil/jobs/mriqc-upgrade-cores
N_SUBS_PER_NODE = 16

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
    def get_runlist(self) -> list[str]:
        rundef = (
            self.ilog.filter(pl.col("mriqc") == 0)
            .filter(pl.col("bids") == 1)
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
    MRIQCReactor(
        job_name=f"mriqc-{datetime.datetime.today().strftime('%Y-%m-%d')}",
        N_SUBS_PER_NODE=N_SUBS_PER_NODE,
        N_SEC_TO_COPY_ONE_SUB=N_SEC_TO_COPY_ONE_SUB,
        JOB=JOB,
        MAXJOBS=MAXJOBS,
    ).parse_and_submit()


if __name__ == "__main__":
    main()
