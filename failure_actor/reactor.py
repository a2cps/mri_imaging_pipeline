import datetime
import os
import typing

import requests
from pydantic import BaseModel, Json
from tapipy import actors, errors, util
from tapipy.tapis import Tapis, TapisResult

SLACKBOT_ADDRESS_SECRET_NAME = "SLACKBOT_ADDRESS_SECRET_NAME"
SLACKBOT_ADDRESS_SECRET_KEY = "SLACKBOT_ADDRESS_SECRET_KEY"
DEFAULT_TENANT = "a2cps"


class DeliveryTarget(BaseModel):
    deliveryMethod: typing.Literal["WEBHOOK", "EMAIL"]
    deliveryAddress: str


class EventData(BaseModel):
    newJobStatus: str | None = None
    oldJobStatus: str | None = None
    jobStatus: str | None = None
    blockedCount: int | None = None
    remoteJobId: str | None = None
    remoteJobId2: str | None = None
    remoteOutcome: str | None = None
    remoteResultInfo: str | None = None
    remoteQueue: str | None = None
    remoteSubmitted: datetime.datetime | None = None
    remoteStarted: datetime.datetime | None = None
    remoteEnded: datetime.datetime | None = None
    jobName: str | None = None
    jobUuid: str | None = None
    jobOwner: str | None = None
    message: str | None = None


# https://tapis.readthedocs.io/en/latest/technical/notifications.html#event-attributes
class Event(BaseModel):
    source: str
    type: str
    subject: str
    data: Json[EventData] | None = None
    seriesId: str | None = None
    timestamp: datetime.datetime
    deleteSubscriptionsMatchingSubject: bool
    tenant: str
    user: str
    uuid: str


# https://tapis.readthedocs.io/en/latest/technical/notifications.html#notification-attributes
class Notification(BaseModel):
    uuid: str
    tenant: str
    subscriptionName: str
    eventUuid: str
    event: Event
    deliveryTarget: DeliveryTarget
    created: datetime.datetime


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
    message_dict: dict[str, typing.Any]


def actors_get_client() -> Tapis:
    """
    Returns a pre-authenticated Tapis client using the abaco environment variables.
    """
    # if we have an access token, use that:
    if token := os.environ.get("_abaco_access_token"):
        tp = Tapis(
            base_url=os.environ.get("_abaco_api_server", default="").strip(
                "/"
            ),
            access_token=token,
        )  # type: ignore
    elif server := os.environ.get("_abaco_api_server"):
        # otherwise, create a client with a fake JWT. this will only work if the actor
        # supplies its own token to itself via a config object or the message, etc.
        tp = Tapis(base_url=server.strip("/"), jwt="123")  # type: ignore
    else:
        raise errors.BaseTapyException(
            "Unable to instantiate a Tapis client: no token found."
        )
    return tp


def get_slackbot_url() -> str:
    client = actors_get_client()

    token: TapisResult = client.sk.readSecret(  # type: ignore
        secretType="user",
        secretName=SLACKBOT_ADDRESS_SECRET_NAME,
        tenant=os.environ.get("_abaco_api_server", DEFAULT_TENANT)
        .split(".")[0]
        .split("/")[-1],
        user=client.actors.get_actor(
            actor_id=os.environ.get("_abaco_actor_id")
        ).owner,
    )
    url: str | None = token.get("secretMap").get(SLACKBOT_ADDRESS_SECRET_KEY)  # type: ignore
    if url is None:
        msg = f"unable to find {SLACKBOT_ADDRESS_SECRET_KEY} in secretMap"
        raise AssertionError(msg)

    return url


def post_notification(notification: str) -> requests.Response | None:
    slackbot = get_slackbot_url()
    return requests.post(url=slackbot, json={"text": notification})


def main() -> None:
    context: Context = actors.get_context()  # type: ignore
    print("Message: ", context.message_dict)

    notification = Notification(**context.message_dict)
    data = notification.event.data

    if data:
        msg = data.model_dump_json(
            indent=2,
            include={"remoteSubmitted", "jobName", "jobUuid", "message"},
        )
    else:
        msg = notification.event.model_dump_json(indent=2)

    msg = f"""
    Potential failure detected:
    {
        msg
    }
    """

    post_notification(msg)


if __name__ == "__main__":
    main()
