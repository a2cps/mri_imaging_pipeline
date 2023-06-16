import dataclasses
import json
import logging
from pathlib import Path

from tapipy import actors, util
from tapipy.tapis import Tapis

JOB = Path("/opt/job.json")


@dataclasses.dataclass
class Context(util.AttrDict):
    raw_message: str
    content_type: str
    actor_repo: str
    actor_name: str
    actor_id: str
    actor_dbid: str
    execution_id: str
    worker_id: str
    username: str
    state: str
    raw_message_parse_log: str
    message_dict: str


def main() -> None:
    context: Context = actors.get_context()  # type: ignore
    print(json.dumps(context, indent=4))

    with open(JOB, "r") as f:
        job = json.load(f)

    print(json.dumps(job, indent=4))

    try:
        client: Tapis = actors.get_client()
        response = client.jobs.submitJob(**job)  # type: ignore
        print(response)
    except Exception as e:
        logging.error(f"encountered while trying to submit job: {e}")


if __name__ == "__main__":
    main()
