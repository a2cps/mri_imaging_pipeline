import datetime
import json
from pathlib import Path

from tapipy import tapis
from tapipy.tapis import Tapis

import pandas as pd

user = "psadil"

PW = json.loads(Path("secrets.json").read_text())
t = Tapis(
    base_url="https://a2cps.tapis.io",
    username=user,
    password=PW.get("password"),
)  # type: ignore
t.get_tokens()

actor = {
    "image": f"{user}/fslanat_actor",
    "stateless": True,
    "cron": False
    # "webhook": r"https://api.a2cps.org/actors/v2/imaging-slackbot.prod/messages?x-nonce=A2CPS_w1r4M51bYemAQ",
}
t.actors.create_actor(**actor)  # type: ignore
actor_id = "BP6KoXZQJ08NR"

t.actors.get_actor(actor_id=actor_id)

t.actors.list_actors()

t.actors.update_actor(
    cron_schedule=f"{datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d 20')} + 1 hour"
)

msg0 = pd.read_json(
    "/Users/psadil/git/a2cps/mri_imaging_pipeline/fslanat_actor/imaging_log.json"
).iloc[
    :100,
]

msg = msg0[["site", "subject_id", "visit", "bids", "fslanat"]].to_dict(
    orient="list"
)

response = t.actors.send_json_message(
    actor_id=actor_id,
    message=msg,
)

"AGYRzvDq3gzPK"
t.actors.get_execution(actor_id=actor_id, execution_id=response.execution_id)

r: tapis.TapisResult = t.actors.get_execution_logs(
    actor_id=actor_id, execution_id=response.execution_id
)
