from reactors.utils import Reactor, agaveutils
import copy
import json
import re


def submit(ag, subject_id: str, bids: str, filename: str, job_def):

    parameters = job_def["parameters"]
    # Define the input for the job as the file that
    # was sent in the notificaton message
    parameters["PARTICIPANT_LABEL"] = subject_id
    parameters["BIDS_DIRECTORY"] = bids
    job_def.name = 'mriqc-' + filename
    job_def.parameters = parameters
    # archivePath = os.path.dirname(os.path.dirname(os.path.normpath(bids))) \
    #                   + '/mriqc/'+ image_type + '/' + filename
    archivePath = re.sub('bids', 'mriqc', bids).split('/corral-secure/projects/A2CPS')[1]
    job_def.archivePath = archivePath

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


def main():
    """Main function"""
    # create the reactor object
    r = Reactor()
    r.logger.info("Hello this is actor {}".format(r.uid))
    # pull in reactor context
    context=r.context  # Actor context
    print(json.dumps(context, indent=4))
    #archivePath=context.archivePath
    subject_id=context.subject_id
    filename=context.filename
    bids=context.bids
    message=context.message_dict
    if message['status'] != "FINISHED":
        exit(0)

    for job_def in [copy.copy(r.settings.anat), copy.copy(r.settings.cuff), copy.copy(r.settings.rest)]:
        submit(
            ag=r.client, 
            subject_id=subject_id, 
            bids=bids, 
            filename=filename, 
            job_def=job_def)

    return



if __name__ == '__main__':
    main()
