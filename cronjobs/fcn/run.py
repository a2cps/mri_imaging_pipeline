import json
from pathlib import Path

from tapipy.tapis import Tapis

import pandas as pd

ILOG = Path(
    "/corral-secure/projects/A2CPS/community/reports/imaging/imaging-log-latest.csv"
)
ACTOR_ID = ""
MAXMINUTES = 360

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
    usecols=[
        "site",
        "subject_id",
        "visit",
        "fmriprep_rest",
        "fmriprep_cuff",
        "fcn",
    ],
).to_dict(orient="list")
msg["maxMinutes"] = MAXMINUTES

response = t.actors.send_json_message(  # type: ignore
    actor_id=ACTOR_ID,
    message=msg,
)
