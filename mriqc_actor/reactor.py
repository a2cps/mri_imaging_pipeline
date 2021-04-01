from reactors.utils import Reactor, agaveutils
import copy
import sys
import json
import os
import re


def submit_mriqc(r,subject_id,bids,filename,site):
    # Create agave client from reactor object
    ag = r.client
    # copy our job.json from config.yml
    job_def = copy.copy(r.settings.mriqc)
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
    site=context.site
    if message['status'] != "FINISHED":
        exit(0)
    # tapis_jobId=m['id']
    # if m['status'] != 'FINISHED':
    #     r.on_failure("Tapis jobId={} has status {}.".format(
    #         tapis_jobId, m['status']) + "Skipping validation.")
    #     exit(0)
    # print(message)

    # pull in the participant_label
    #participant_label = message['participant_label']
    # use submit function to submit job to fmriprep
    submit_mriqc(r,subject_id,bids,filename,site)
    return



if __name__ == '__main__':
    main()
