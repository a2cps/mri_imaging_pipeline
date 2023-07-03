import json
from pathlib import Path

from tapipy.tapis import Tapis

import pandas as pd

ILOG = Path(
    "/corral-secure/projects/A2CPS/community/reports/imaging/imaging-log-latest.csv"
)
MAXJOBS = 500
ACTOR_ID = "8Rmeo8yweGwg6"

user = "urrutia"

PW = json.loads(Path("secrets.json").read_text())
t = Tapis(
    base_url="https://a2cps.tapis.io",
    username=user,
    password=PW.get("password"),
)  # type: ignore
t.get_tokens()

msg = pd.read_csv(
    ILOG,
    usecols=["site", "subject_id", "visit", "bids", "fslanat"],
    nrows=MAXJOBS,
)

response = t.actors.send_json_message(  # type: ignore
    actor_id=ACTOR_ID,
    message=msg.to_dict(orient="list"),
)
