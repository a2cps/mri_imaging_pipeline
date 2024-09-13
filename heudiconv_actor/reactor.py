import copy
import json
import os
from pathlib import Path
import yaml
from tapipy import actors, errors, util
from tapipy.tapis import Tapis, TapisResult

def get_failurebot_url(client) -> str:
    token: TapisResult = client.sk.readSecret(  # type: ignore
        secretType="user",
        secretName='FAILUREBOT_ADDRESS_SECRET_NAME',
        tenant=os.environ.get("_abaco_api_server")
        .split(".")[0]  # type: ignore
        .split("/")[-1],
        user=client.actors.get_actor(
            actor_id=os.environ.get("_abaco_actor_id")
        ).owner,
    )
    url: str | None = token.get("secretMap").get('FAILUREBOT_ADDRESS_SECRET_KEY')  # type: ignore
    if url is None:
        msg = f"unable to find {'FAILUREBOT_ADDRESS_SECRET_KEY'} in secretMap"
        raise AssertionError(msg)

    return url


def set_subscription_url(job: dict, arg: str) -> None:
    job.get("subscriptions")[0].get("deliveryTargets")[0].update(  # type: ignore
        {"deliveryAddress": arg}
    )
    return job


def _make_callback(server: str, alias: str, nonce: str) -> str:
    return f"{server}/actors/v2/{alias}/messages?x-nonce={os.getenv(nonce)}"


def submit_heudiconv(
    config, site: str, subject_id: str, session: str, dicoms: str, outdir: Path
) -> None:
    # Create agave client from reactor object
    client = actors.get_client()
    # copy our job.json from config.yml
    job_def = config['heudiconv']
    envVariables = job_def["parameterSet"]["envVariables"]
    # Define the input for the job as the file that
    # was sent in the notificaton message
    for d in envVariables:
        d.update(("value", dicoms) for k,v in d.items() if d['key'] == "FILES")
        d.update(("value", "--subjects " + subject_id) for k,v in d.items() if d['key'] == "LIST_OF_SUBJECTS")
        d.update(("value", "--ses " + session) for k,v in d.items() if d['key'] == "SESSION_FOR_LONGITUDINAL")
        d.update(("value", site) for k,v in d.items() if d['key'] == "SITE")


    #archivePath = str(outdir.relative_to("/corral-secure/projects/A2CPS/"))
    job_def['archiveSystemDir'] = str(outdir)
    job_def['name'] = f"heudiconv-{outdir.name}"
    failurebot_url = get_failurebot_url(client=client)
    job_def = set_subscription_url(job_def, arg=failurebot_url)

    # Submit the job in a try/except block
    try:
        # Submit the job and get the job ID
        submitted = client.jobs.submitJob(**job_def)
        #job_id = client.jobs.submit(body=job_def)["id"]
        print(submitted.uuid)
        print(json.dumps(job_def, indent=4))
    except Exception as e:
        print(json.dumps(job_def, indent=4))
        print(f"Error submitting job: {e}")
        print(e.response.content)
        return
    return


def main() -> None:
    """Main function"""
    context = actors.get_context()  # type: ignore
    message = context.message_dict
    print("Message: ", message)
    with open('/opt/config.yml', 'r') as f:
        config = yaml.load(f, Loader=yaml.FullLoader)

    site = message["site_id"]
    subject_id = message["subject_id"]
    session = message["session_id"]
    dicoms: str = message["dicoms"]

    outdir = Path(dicoms.replace("dicoms", "bids")).with_suffix("")

    submit_heudiconv(config, site, subject_id, session, dicoms, outdir)


if __name__ == "__main__":
    main()
