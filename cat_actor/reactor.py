import json
from reactors.utils import Reactor

"""
default actor to print the message from user input
"""

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


def main() -> None:
    """Main function"""
    # create the reactor object
    r = Reactor()
    r.logger.info(f"Hello this is actor {r.uid}")

    # pull in reactor context
    context=r.context  # Actor context
    print(json.dumps(context, indent=4))
    # if job status not in finished state, exit cleanly 
    if context.message_dict['status'] != "FINISHED":
        exit(0)

    #archivePath=context.archivePath
    #subject_id=context.subject_id
    filename=context.filename
    bids=context.bids
    message=context.message_dict
    site=context.site

    site_codes = \
                {
                    "UI": "UI_uic",
                    "NS": "NS_northshore",
                    "UC": "UC_uchicago",
                    "UM": "UM_umichigan",
                    "WS": "WS_wayne_state",
                    "SH": "SH_spectrum_health"
                }
    site_name = site_codes[site]

    job_def=r.settings.main
    job_def.name = 'cat12_' + filename
    job_def.archivePath = 'products/mris/{}/cat12/'.format(site_name)
    parameters = job_def["parameters"]
    parameters['BIDS'] = bids
    parameters['OUTDIR'] = filename

    #print(json.dumps(job_def, indent=4))
    submit(ag=r.client, job_def=job_def)

    return

if __name__ == '__main__':
    main()

