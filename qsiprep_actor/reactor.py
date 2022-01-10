from reactors.utils import Reactor, agaveutils
import copy
import json
import re


def submit(ag, job_def) -> None:
    # Submit the job in a try/except block
    #print(job_def)
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


def specify_jobdef(job_def, subject_id: str, bids: str, filename: str):
    # Define the input for the job as the file that
    # was sent in the notification message

    job_def.name = f'qsiprep-{filename}'
    parameters = job_def["parameters"]
    parameters["PARTICIPANT_LABEL"] = subject_id
    parameters["BIDS_DIRECTORY"] = bids
    # get session from filename
    # TO DO: pass this in the callback from bids_validation instead of string parsing
    session_id = 'ses-' + filename[-2:]
    parameters["SESSION_FOR_LONGITUDINAL"] = session_id
    job_def.parameters = parameters
    job_def.archivePath = re.sub('bids', 'qsiprep', bids).split('/corral-secure/projects/A2CPS/')[1] 
    return job_def


def main() -> None:
    """Main function"""
    # create the reactor object
    r = Reactor()
    #print(r)
    r.logger.info(f"Hello this is actor {r.uid}")
    # pull in reactor context
    context=r.context  # Actor context
    #print(json.dumps(context, indent=4))

    if context.message_dict['status'] != "FINISHED":
        exit(0)

    #print(r.settings)
    job_basic = copy.copy(r.settings.run_qsiprep)
    job_def = specify_jobdef(
        job_def=job_basic,
        subject_id=context.subject_id,
        bids=context.bids,
        filename=context.filename)
    #print(json.dumps(job_def,indent=4))

    submit(
        ag=r.client,
        job_def=job_def)

    return


if __name__ == '__main__':
    main()
