import datetime
import itertools
import json
from pathlib import Path

import polars as pl
from mri_actor_utils import config, models

# within docker container
JOB = Path("/opt/job.json")

N_SUBS_PER_NODE = 6

# for ls
MAX_NODES_PER_JOB = 20

# can change by incoming message by specifying "MAXJOBS"
MAXJOBS = N_SUBS_PER_NODE * MAX_NODES_PER_JOB

# amount of time required to copy one sub from /tmp -> /corral-secure
# this will be used to terminate the job early in case of
# prolonged runtime
N_SEC_TO_COPY_ONE_SUB = 60


class SignaturesReactor(models.Reactor):
    def get_runlist(self) -> list[str]:
        rundef = (
            self.ilog.rename(
                {
                    "fMRI Individualized Pressure Received": "CUFF1",
                    "fMRI Standard Pressure Received": "CUFF2",
                    "1st Resting State Received": "REST1",
                    "2nd Resting State Received": "REST2",
                }
            )
            .filter(pl.col("signatures") == 0)
            .filter(pl.col("fmriprep") == 1)
            .filter(
                (pl.col("CUFF1") == 1)
                | (pl.col("CUFF2") == 1)
                | (pl.col("REST1") == 1)
                | (pl.col("REST2") == 1)
            )
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
                    pl.lit("/fmriprep/"),
                    pl.col("sublong"),
                    pl.lit("/fmriprep"),
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
    SignaturesReactor(
        job_name=f"signatures-{datetime.datetime.today().strftime('%Y-%m-%d')}",
        N_SUBS_PER_NODE=N_SUBS_PER_NODE,
        N_SEC_TO_COPY_ONE_SUB=N_SEC_TO_COPY_ONE_SUB,
        JOB=JOB,
        MAXJOBS=MAXJOBS,
    ).parse_and_submit()


if __name__ == "__main__":
    main()
