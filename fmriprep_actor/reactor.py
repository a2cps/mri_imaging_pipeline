from reactors.utils import Reactor, agaveutils
import copy
import sys
import os
import json
import re


# def check_metadata_file(r, file_uri):
#     ag = r.client
#     manifestUrl = file_uri
#     if manifestUrl is None:
#         try:
#             manifestUrl = context.file_uri
#         except Exception as e:
#             print("No file_uri specified")
#             exit(1)
#     (agaveStorageSystem, dirPath, manifestFileName) = \
#         agaveutils.from_agave_uri(uri=manifestUrl)
#     # get the manifest and start parsing it
#     manifestPath = dirPath + "/" + manifestFileName
#     try:
#         mani_file = agaveutils.agave_download_file(
#                     agaveClient=ag,
#                     agaveAbsolutePath=manifestPath,
#                     systemId=agaveStorageSystem,
#                     localFilename=manifestFileName
#                     )
#     except Exception as e:
#         r.on_failure("failed to get manifest {}".format(manifestUrl), e)

#     if mani_file is None:
#         r.on_failure("failed to get manifest {}".format(manifestUrl), e)

#     try:
#         manifest = json.load(open(manifestFileName))
#     except Exception as e:
#         r.on_failure("failed to load manifest {}".format(manifestUrl), e)

#     if 'cuff' in manifest['SeriesDescription']:
#         job_def = copy.copy(r.settings.cuff)
#         r.logger.info("Setting parameters for cuff image")
#     if 'rest' in manifest['SeriesDescription']:
#         job_def = copy.copy(r.settings.rest)
#         r.logger.info("Setting parameters for rest image")
#     else:
#         print("No cuff/rest specification found for: ", manifest['SeriesDescription'])
#         job_def = copy.copy(r.settings.rest)
#     return job_def


def submit_fmriprep(r,subject_id, bids, filename,site,next_step,job_def,image_type):
    # Create agave client from reactor object
    ag = r.client
    parameters = job_def["parameters"]
    job_def.name = 'fmriprep-' + image_type +'-'+filename
    # Define the input for the job as the file that
    # was sent in the notificaton message
    parameters["PARTICIPANT_LABEL"] = 'sub-' + subject_id
    parameters["BIDS_DIRECTORY"] = bids
    if image_type in ['cuff', 'rest']:
         parameters["FS_SUBJECTS_DIR"] = re.sub('bids', 'fmriprep', bids) + '/anat/freesurfer'
    job_def.parameters = parameters
    # archivePath = os.path.dirname(os.path.dirname(os.path.normpath(bids))) \
    #               + '/fmriprep/'+ image_type + '/' + filename
    archivePath = re.sub('bids', 'fmriprep', bids).split('/corral-secure/projects/A2CPS')[1] + '/' + image_type
    job_def.archivePath = archivePath
    try:
        pipeline_config = copy.copy(r.settings.pipelines)
        api_server = pipeline_config['api_server']

        fmriprep_nonce = os.getenv('_FMRIPREP_NONCE')
        fmriprep_alias = pipeline_config['fmriprep_alias']
        fmriprep_callback = api_server + '/actors/v2/' + fmriprep_alias + '/messages?x-nonce=' + fmriprep_nonce

    except Exception as e:
        print(e)
        r.logger.error("Unable to generate Audit callback")

    notif = [
            {'event': 'FINISHED',
            "persistent": False,
            'url': fmriprep_callback + '&status=${JOB_STATUS}' +
            '&subject_id=' + subject_id +
            '&bids=' + bids +
            '&filename='+ filename +
            '&site='+ site +
            '&next_step=' + next_step}
            ]
    job_def.notifications = notif
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

    next_step = context.next_step
    if message['status'] != "FINISHED":
        exit(0)

    if next_step == 'anat':
        next_step = 'cuff_rest'
        job_def = copy.copy(r.settings.anat)
        submit_fmriprep(r,subject_id, bids, filename,site,next_step,job_def, 'anat')
    elif next_step == 'cuff_rest':
        next_step = 'finished'
        job_def = copy.copy(r.settings.cuff)
        submit_fmriprep(r,subject_id, bids, filename,site,next_step,job_def, 'cuff')
        job_def = copy.copy(r.settings.rest)
        submit_fmriprep(r,subject_id, bids, filename,site,next_step,job_def, 'rest')
    # tapis_jobId=message['id']
    # if m['status'] != 'FINISHED':
    #     r.on_failure("Tapis jobId={} has status {}.".format(
    #         tapis_jobId, m['status']) + "Skipping validation.")
    #     exit(0)
    # print(message)
    # check the file_uri from the message
    # depending on the file_uri, set fmriprp parameters for a rest or cuff fmri
    #job_def = check_metadata_file(r, file_uri)
    return



if __name__ == '__main__':
    main()
