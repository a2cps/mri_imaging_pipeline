import datetime
import itertools
import json
from pathlib import Path

import polars as pl
from mri_actor_utils import config, models

# within docker container
JOB = Path("/opt/job.json")

# numbers for frontera (tmp system is half the size of ls6)
N_SUBS_PER_NODE = 2

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


class FMRIPrepReactor(models.Reactor):
    def get_runlist(self) -> tuple[list[str], list[str], list[str]]:
        rundef = (
            self.ilog
            .rename({
                "fMRI Individualized Pressure Received": "CUFF1",
                "fMRI Standard Pressure Received": "CUFF2",
                "1st Resting State Received": "REST1",
                "2nd Resting State Received": "REST2",
            })
            .filter(pl.col("T1 Received") == 1)
            .filter(pl.col("synthstrip-v4") == 1)
            .filter(pl.col("fmriprep-v4") == 0)
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
                )
                .cast(pl.Utf8)
                .str.to_titlecase(),
            )
            .with_columns(
                INPUT_DIRS=pl.concat_str(
                    pl.lit("/corral-secure/projects/A2CPS/products/mris/"),
                    pl.col("sitelong"),
                    pl.lit("/bids/"),
                    pl.col("sublong"),
                ),
                DERIVATIVES=pl.concat_str(
                    pl.lit("/corral-secure/projects/A2CPS/products/mris/"),
                    pl.col("sitelong"),
                    pl.lit("/synthstrip-v4/"),
                    pl.col("sublong"),
                ),
            )
            .sort(
                "visit", "Surgery Week", "subject_id"
            )  # ensure V1 run before V3, and do oldest scans
        )

        runlist = (
            rundef
            .select(pl.col("INPUT_DIRS"))
            .to_series()
            .to_list()[: self.maxjobs * self.n_submissions],
            rundef
            .select(pl.col("ANAT_ONLY"))
            .to_series()
            .to_list()[: self.maxjobs * self.n_submissions],
            rundef
            .select(pl.col("DERIVATIVES"))
            .to_series()
            .to_list()[: self.maxjobs * self.n_submissions],
        )
        return runlist

    def parse_and_submit(self) -> None:
        print(json.dumps(self.context, indent=4))

        runlist = self.get_runlist()
        for r, (input_dirs, anat_only, derivatives) in enumerate(
            zip(
                itertools.batched(runlist[0], self.maxjobs),
                itertools.batched(runlist[1], self.maxjobs),
                itertools.batched(runlist[2], self.maxjobs),
            )
        ):
            n_jobs = len(input_dirs)
            self.set_app_arg(
                name="INPUT_DIRS", value="--input-dirs " + " ".join(input_dirs)
            )
            self.set_app_arg(
                name="ANAT_ONLY", value="--anat-only " + " ".join(anat_only)
            )
            self.set_app_arg(
                name="DERIVATIVES", value="--derivatives " + " ".join(derivatives)
            )
            self.job.name = f"{self.job_name}-{r}"

            self.set_common(n_jobs=n_jobs)
            self.submit()


def main() -> None:
    FMRIPrepReactor(
        job_name=f"fmriprep-{datetime.datetime.today().strftime('%Y-%m-%d')}",
        N_SUBS_PER_NODE=N_SUBS_PER_NODE,
        N_SEC_TO_COPY_ONE_SUB=N_SEC_TO_COPY_ONE_SUB,
        JOB=JOB,
        MAXJOBS=MAXJOBS,
    ).parse_and_submit()


if __name__ == "__main__":
    main()
