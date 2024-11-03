import datetime
import json
import logging
from pathlib import Path

from mri_actor_utils import models

# within docker container
JOB = Path("/opt/job.json")


class AggregatorQCReactor(models.Reactor):
    # need this concrete method
    def get_runlist(self) -> None:
        pass

    def submit(self) -> None:
        print(json.dumps(self.context, indent=4))

        if max_minutes := self.context.message_dict.get("maxMinutes"):
            self.job.maxMinutes = max_minutes

        self.job.name = self.job_name

        if self.context.message_dict.get("SKIP_FAILUREBOT", False):
            self.job.subscriptions = None
        else:
            self.set_subscription_url(url=self.failurebot_url)

        print(self.job.model_dump_json(indent=4, exclude_unset=True, exclude_none=True))

        try:
            submitted = self.client.jobs.submitJob(  # type: ignore
                **self.job.model_dump(exclude_unset=True, exclude_none=True)
            )
            print(submitted.uuid)
        except Exception:
            logging.exception("encountered while trying to submit job")


def main() -> None:
    AggregatorQCReactor(
        job_name=f"aggregate-{datetime.datetime.today().strftime('%Y-%m-%d')}",
        N_SUBS_PER_NODE=9999,
        N_SEC_TO_COPY_ONE_SUB=1,
        JOB=JOB,
        MAXJOBS=9999,
    ).submit()


if __name__ == "__main__":
    main()
