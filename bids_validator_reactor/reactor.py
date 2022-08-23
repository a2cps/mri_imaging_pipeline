from reactors.utils import Reactor, agaveutils
import os
import copy
import json
import re
import logging


def _make_callback(server: str, alias: str, nonce: str) -> str:
    return f"{server}/actors/v2/{alias}/messages?x-nonce={os.getenv(nonce)}"


def _get_output_dir(bids: str) -> str:
    return os.path.basename(bids)


def submit_bids_validate(r,bids,filename,subject_id,site):
    # Create agave client from reactor object
    ag = r.client
    # copy our job.json from config.yml
    job_def = copy.copy(r.settings.bids_validator)
    parameters = job_def["parameters"]
    # Define the input for the job as the file that
    # was sent in the notificaton message
    parameters["BIDS_DIRECTORY"] = bids
    job_def.name = 'bids-validate-' + filename
    job_def.parameters = parameters
    archivePath = re.sub('bids', 'bids_validation', bids).split('/corral-secure/projects/A2CPS')[1] 
    job_def.archivePath = archivePath
    try:
        pipeline_config = copy.copy(r.settings.pipelines)
        api_server = pipeline_config['api_server']

        fmriprep_nonce = os.getenv('_FMRIPREP_NONCE')
        fmriprep_alias = pipeline_config['fmriprep_alias']
        fmriprep_callback = api_server + '/actors/v2/' + fmriprep_alias + '/messages?x-nonce=' + fmriprep_nonce

        mriqc_nonce = os.getenv('_MRIQC_NONCE')
        mriqc_alias = pipeline_config['mriqc_alias']
        mriqc_callback = api_server + '/actors/v2/' + mriqc_alias + '/messages?x-nonce=' + mriqc_nonce

        qsiprep_nonce = os.getenv('_QSIPREP_NONCE')
        qsiprep_alias = pipeline_config['qsiprep_alias']
        qsiprep_callback = api_server + '/actors/v2/' + qsiprep_alias + '/messages?x-nonce=' + qsiprep_nonce

        cat_callback = _make_callback(
            server=pipeline_config['api_server'], 
            alias=pipeline_config['cat_alias'], 
            nonce='_CAT_NONCE')

        # bids_validator_nonce = os.getenv('_BIDS_VALIDATOR_NONCE')
        # bids_validator_alias = pipeline_config['bids_validator_alias']
        # bids_validator_callback = api_server + '/actors/v2/' + bids_validator_alias + '/messages?x-nonce=' + bids_validator_nonce

    except Exception as e:
        print(e)
        r.logger.error("Unable to generate Audit callback")

    # notif = [{'event': 'RUNNING',
    #           "persistent": True,
    #           'url': mpj.callback + '&status=${JOB_STATUS}'},
    #          {'event': 'FAILED',
    #           "persistent": False,
    #           'url': mpj.callback + '&status=${JOB_STATUS}'},
    #          {'event': 'FINISHED',
    #           "persistent": False,
    #           'url': mpj.callback + '&status=${JOB_STATUS}'},
    if "QC" in filename:
        logging.info(f"{filename} appears to be a phantom. pipeline will stop after validation")
    else:
        notif = [
            {
                'event': 'FINISHED',
                "persistent": False,
                'url': fmriprep_callback + '&status=${JOB_STATUS}' +
                '&subject_id=' + subject_id +
                '&bids=' + bids +
                '&filename='+ filename +
                '&site='+ site +
                '&next_step=anat'
            },
            {
                'event': 'FINISHED',
                "persistent": False,
                'url': mriqc_callback + '&status=${JOB_STATUS}' +
                '&subject_id=' + subject_id +
                '&bids=' + bids +
                '&filename='+ filename +
                '&site='+ site
            },
            {
                'event': 'FINISHED',
                "persistent": False,
                'url': qsiprep_callback + '&status=${JOB_STATUS}' +
                '&subject_id=' + subject_id +
                '&bids=' + bids +
                '&filename='+ filename +
                '&site='+ site
            },
            {
                'event': 'FINISHED',
                "persistent": False,
                'url': cat_callback + '&status=${JOB_STATUS}' +
                '&bids=' + bids +
                '&filename=' + _get_output_dir(bids)
            }
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
    # tapis_jobId=message['id']
    # if m['status'] != 'FINISHED':
    #     r.on_failure("Tapis jobId={} has status {}.".format(
    #         tapis_jobId, m['status']) + "Skipping validation.")
    #     exit(0)
    print(message)
    if message['status'] == "FINISHED":
        submit_bids_validate(r,bids,filename,subject_id,site)
    #tapis actors submit -m '{"text": "heudiconv processing complete, outputs available under: /corral-secure/projects/A2CPS/products/mris/UI_uic/bids/UI10003V1/"}' WPYELPWZy48aw



if __name__ == '__main__':
    main()

