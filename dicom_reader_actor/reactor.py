import copy
import sys
import json
import os
import re
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

def submit_dicom(config, uploaded_file):
    # Create agave client from reactor object
    client = actors.get_client()
    # copy our job.json from config.yml
    job_def = config['dicom_reader']
    parameters = job_def["parameterSet"]['appArgs']
    # Define the input for the job as the file that
    # was sent in the notificaton message
    parameters[0]["arg"] = uploaded_file
    site_file = os.path.normpath(uploaded_file).split('corral-secure/projects/A2CPS/submissions/')[-1]
    archiveSystemDir = job_def['archiveSystemDir'] + '/' + site_file.split('/')[0]
    job_def['name'] = site_file
    job_def['archiveSystemDir'] = archiveSystemDir

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
        print("Error submitting job: {}".format(e))
        print(e.response.content)
        return
    return


def message_vbr(r,filename,site,subject,session,zipfile,outdir):
    pipeline_config = copy.copy(r.settings.pipelines)
    vbr_actor_alias = pipeline_config['vbr_actor_alias']
    message = {
        "filename": dicoms,
        "site": site,
        "subject_id": subject,
        "session": session,
        "outdir": outdir
    }
    r.send_message(vbr_actor_alias, message)
    #r.send_message(actorId=vbr_actor_alias, message=message)
    return

def main():
    """Main function"""
    context = actors.get_context()  # type: ignore
    message = context.message_dict
    print("Message: ", message)
    with open('/opt/config.yml', 'r') as f:
        config = yaml.load(f, Loader=yaml.FullLoader)

    uploaded_file = message['uploaded_file']

    submit_dicom(config, uploaded_file)
    #message_vbr(r,site,subject,session,dicoms,outdir)
    return



if __name__ == '__main__':
    main()