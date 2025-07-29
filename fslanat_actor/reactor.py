import datetime
import itertools
import json
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
    "UC11295V1",
    "UC11272V1",
    "UC15011V3",
    "UC15032V1",
    "UC15038V1",
    "UC15039V1",
    "UC15039V3",
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
    def get_runlist(self) -> tuple[list[str], list[str], list[str]]:
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
        runlist = (
            rundef.select(pl.col("INPUT_DIRS"))
            .to_series()
            .to_list()[: self.maxjobs * self.n_submissions],
            rundef.select(pl.col("PRECROP"))
            .to_series()
            .to_list()[: self.maxjobs * self.n_submissions],
            rundef.select(pl.col("MASK_HIGH_VOXELS"))
            .to_series()
            .to_list()[: self.maxjobs * self.n_submissions],
        )

        return runlist

    def parse_and_submit(self) -> None:
        print(json.dumps(self.context, indent=4))

        runlist = self.get_runlist()

        for r, (input_dirs, precrop, mask_high_voxels) in enumerate(
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
            self.set_app_arg(name="PRECROP", value="--precrop " + " ".join(precrop))
            self.set_app_arg(
                name="MASK_HIGH_VOXELS",
                value="--mask-high-voxels " + " ".join(mask_high_voxels),
            )
            self.job.name = f"{self.job_name}-{r}"

            self.set_common(n_jobs=n_jobs)
            self.submit()


def main() -> None:
    FSLAnatReactor(
        job_name=f"fslanat-{datetime.datetime.today().strftime('%Y-%m-%d')}",
        N_SUBS_PER_NODE=N_SUBS_PER_NODE,
        N_SEC_TO_COPY_ONE_SUB=N_SEC_TO_COPY_ONE_SUB,
        JOB=JOB,
        MAXJOBS=MAXJOBS,
    ).parse_and_submit()


if __name__ == "__main__":
    main()
