from reactors.utils import Reactor, agaveutils
import copy
import json
import re


def submit(ag, job_def) -> None:
    # Submit the job in a try/except block
    try:
        # Submit the job and get the job ID
        job_id = ag.jobs.submit(body=job_def)['id']
        print(job_id)
        print(json.dumps(job_def, indent=4))
    except Exception as e:
        print(json.dumps(job_def, indent=4))
        print("Error submitting job: {}".format(e))
        print(e.response.content)
        return
    return


def specify_jobdef(job_def, job: str, subject_id: str, bids: str, filename: str):
    # Define the input for the job as the file that
    # was sent in the notificaton message

    job_def.name = f'mriqc-{job}-{filename}'
    parameters = job_def["parameters"]    
    parameters["PARTICIPANT_LABEL"] = subject_id
    parameters["BIDS_DIRECTORY"] = bids
    #parameters["WORK_DIR"] = f'{parameters["WORK_DIR"]}-{job}'

    # if job == "cuff":
    #     parameters["MODALITIES"] = "bold T1w"
    # elif job == "anat":
    #     parameters["MODALITIES"] = "bold"

    job_def.parameters = parameters
    job_def.archivePath = re.sub('bids', 'mriqc', bids).split('/corral-secure/projects/A2CPS')[1] + '/' + job

    return job_def


def main() -> None:
    """Main function"""
    # create the reactor object
    r = Reactor()
    r.logger.info(f"Hello this is actor {r.uid}")
    # pull in reactor context
    context=r.context  # Actor context
    print(json.dumps(context, indent=4))

    if context.message_dict['status'] != "FINISHED":
        exit(0)

    for job in ['anat', 'cuff', 'rest']:
        if job == 'anat':
            job_basic = copy.copy(r.settings.anat)
        if job == 'cuff':
            job_basic = copy.copy(r.settings.cuff)
        elif job == "rest":
            job_basic = copy.copy(r.settings.rest)

        job_def = specify_jobdef(
            job_def=job_basic, 
            job=job, 
            subject_id=context.subject_id, 
            bids=context.bids, 
            filename=context.filename)

        submit(
            ag=r.client, 
            job_def=job_def)

    return


if __name__ == '__main__':
    main()
