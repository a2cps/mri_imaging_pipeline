from reactors.utils import Reactor, agaveutils
import copy
import sys
import json
import os
import re


def submit_heudiconv(r,site,subject,session,dicoms,outdir):
    # Create agave client from reactor object
    ag = r.client
    # copy our job.json from config.yml
    job_def = copy.copy(r.settings.heudiconv)
    parameters = job_def["parameters"]
    # Define the input for the job as the file that
    # was sent in the notificaton message
    parameters["FILES"] = dicoms
    # split subject from path
    #parameters['OUTDIR'] = outdir 
    parameters['LIST_OF_SUBJECTS'] = subject
    #parameters['LOCATOR'] = site + '/bids'
    parameters['SESSION_FOR_LONGITUDINAL'] = session
    parameters['SITE'] = site
    job_def.parameters = parameters
    archivePath = outdir.split('/corral-secure/projects/A2CPS/')[1]
    #archivePath = outdir.split('/corral-secure/projects/A2CPS/')[1] + filename
    job_def.archivePath = archivePath
    job_def.name = 'heudiconv-' + outdir.split('/')[-1]

    try:
            pipeline_config = copy.copy(r.settings.pipelines)
            api_server = pipeline_config['api_server']

            # fmriprep_nonce = os.getenv('_FMRIPREP_NONCE')
            # fmriprep_alias = pipeline_config['fmriprep_alias']
            # frmiprep_callback = api_server + '/actors/v2/' + fmriprep_alias + '/messages?x-nonce=' + fmriprep_nonce

            # mriqc_nonce = os.getenv('_MRIQC_NONCE')
            # mriqc_alias = pipeline_config['mriqc_alias']
            # mriqc_callback = api_server + '/actors/v2/' + mriqc_alias + '/messages?x-nonce=' + mriqc_nonce

            bids_validator_nonce = os.getenv('_BIDS_VALIDATOR_NONCE')
            bids_validator_alias = pipeline_config['bids_validator_alias']
            bids_validator_callback = api_server + '/actors/v2/' + bids_validator_alias + '/messages?x-nonce=' + bids_validator_nonce

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
    #           {'event': 'FINISHED',
    #            "persistent": False,
    #            'url': frmiprep_callback + '&status=${JOB_STATUS}' +
    #            '&analysis_type=preprocessing' +
    #            '&subject_id=' + subject +
    #            '&bids=' + archivePath +
    #            '&filename='+ filename},
    #            {'event': 'FINISHED',
    #            "persistent": False,
    #            'url': mriqc_callback + '&status=${JOB_STATUS}' +
    #            '&subject_id=' + subject +
    #            '&bids=' + archivePath +
    #            '&filename='+ filename}]
    notif = [
                {
                'event': 'FINISHED',
                'persistent': False,
                'url': bids_validator_callback + '&status=${JOB_STATUS}' +
                '&subject_id=' + subject +
                '&bids=' + outdir +
                '&filename='+ outdir.split('/')[-1] +
                '&site=' + site
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

def parse_file_metadata(zipfile):
    # get file name, site.redcap_id.visit
    # ex NS10008V1
    filename = os.path.basename(zipfile).split('.zip')[0]
    directory_name=os.path.dirname(zipfile)
    site = os.path.basename(directory_name)
    # split filename into site code, subject, session
    (site_id, subject, v, session, space) = re.split('(\d+)',filename)
    outdir = re.sub('submissions', 'products/mirs', directory_name) + '/bids/'
    return filename, site, subject, session, outdir

def main():
    """Main function"""
    # create the reactor object
    r = Reactor()
    r.logger.info("Hello this is actor {}".format(r.uid))
    # pull in reactor context
    context = r.context
    #print(context)
    # get the message that was sent to the actor
    message = context.message_dict
    #zipfile = message['zipfile']
    #(filename, site, subject, session, outdir) = parse_file_metadata(zipfile)
    site = message['site_id']
    subject = message['subject_id']
    session = message['session_id']
    dicoms = message['dicoms']

    # site=context.site_id
    # subject =context.subject_id
    # dicoms = context.dicoms
    # session=context.session_id
    outdir = re.sub('dicoms', 'bids', dicoms)
    outdir = outdir.split('.zip')[0]

    submit_heudiconv(r,site,subject,session,dicoms,outdir)
    #message_vbr(r,site,subject,session,dicoms,outdir)
    return



if __name__ == '__main__':
    main()
