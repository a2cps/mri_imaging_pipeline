import copy
import dataclasses
import json
import logging
import os
from pathlib import Path

from tapipy import actors, errors, util
from tapipy.tapis import Tapis, TapisResult

JOB = Path("/opt/job.json")


# TODO
FAILUREBOT_ADDRESS_SECRET_NAME = "FAILUREBOT_ADDRESS_SECRET_NAME"
FAILUREBOT_ADDRESS_SECRET_KEY = "FAILUREBOT_ADDRESS_SECRET_KEY"


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


def actors_get_client() -> Tapis:
    """Returns a pre-authenticated Tapis client using the abaco environment variables."""
    # if we have an access token, use that:
    if token := os.environ.get("_abaco_access_token"):
        tp = Tapis(
            base_url=os.environ.get("_abaco_api_server", default="").strip(
                "/"
            ),
            access_token=token,
        )  # type: ignore
    elif server := os.environ.get("_abaco_api_server"):
        # otherwise, create a client with a fake JWT. this will only work if the actor is supplying its
        # own token to itself via a config object or the message, etc.
        tp = Tapis(base_url=server.strip("/"), jwt="123")  # type: ignore
    else:
        raise errors.BaseTapyException(
            "Unable to instantiate a Tapis client: no token found."
        )
    return tp


def get_failurebot_url(client) -> str:
    token: TapisResult = client.sk.readSecret(  # type: ignore
        secretType="user",
        secretName=FAILUREBOT_ADDRESS_SECRET_NAME,
        tenant=os.environ.get("_abaco_api_server").split('.')[0].split("/")[-1],
        user=client.actors.get_actor(actor_id=os.environ.get("_abaco_actor_id")).owner,
    )
    url: str | None = token.get("secretMap").get(FAILUREBOT_ADDRESS_SECRET_KEY)  # type: ignore
    if url is None:
        msg = f"unable to find {FAILUREBOT_ADDRESS_SECRET_KEY} in secretMap"
        raise AssertionError(msg)

    return url


def set_subscription_url(job: dict, arg: str) -> dict:
    job2 = copy.deepcopy(job)
    job2.get("subscriptions")[0].get("deliveryTargets")[0].update(  # type: ignore
        {"deliveryAddress": arg}
    )
    return job2


def main() -> None:
    context: Context = actors.get_context()  # type: ignore
    print(json.dumps(context, indent=4))

    with open(JOB, "r") as f:
        job = json.load(f)

    client = actors_get_client()
    failurebot_url = get_failurebot_url(client=client)
    job = set_subscription_url(job, arg=failurebot_url)
    print(json.dumps(job, indent=4))

    try:
        submitted = client.jobs.submitJob(**job)  # type: ignore
        print(submitted.uuid)
    except Exception as e:
        logging.error(f"encountered while trying to submit job: {e}")


if __name__ == "__main__":
    main()
