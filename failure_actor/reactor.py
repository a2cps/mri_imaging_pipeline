import datetime
import os
import typing

import requests
from pydantic import BaseModel, Json
from tapipy import actors, errors, util
from tapipy.tapis import Tapis, TapisResult

# TODO
SLACKBOT_ADDRESS_SECRET_NAME = ""
SLACKBOT_ADDRESS_SECRET_KEY = ""


class DeliveryTarget(BaseModel):
    deliveryMethod: typing.Literal["WEBHOOK", "EMAIL"]
    deliveryAddress: str


class EventData(BaseModel):
    newJobStatus: str | None
    oldJobStatus: str | None
    jobStatus: str | None
    blockedCount: int
    remoteJobId: str
    remoteJobId2: str | None
    remoteOutcome: str
    remoteResultInfo: str
    remoteQueue: str | None
    remoteSubmitted: datetime.datetime | None
    remoteStarted: datetime.datetime | None
    remoteEnded: datetime.datetime | None
    jobName: str
    jobUuid: str
    jobOwner: str
    message: str


class Event(BaseModel):
    source: str
    type: str
    subject: str
    data: Json[EventData]
    seriesId: str
    timestamp: datetime.datetime
    deleteSubscriptionsMatchingSubject: bool
    tenant: str
    user: str
    uuid: str


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
        tenant=os.environ.get("_tapisTenant"),
        user=os.environ.get("_tapisEffectiveUserId"),
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

    notification = Notification(**context.message_dict)

    msg = f"""
    Potential failure detected:
    {
        notification.event.data.json(
            indent=2, 
            include={
                "remoteSubmitted", 
                "jobName", 
                "jobUuid",
                "message"
            }
        )
    }
    """

    post_notification(msg)


if __name__ == "__main__":
    main()
