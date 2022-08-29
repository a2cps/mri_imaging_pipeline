import json
import re
import pathlib
from reactors.utils import Reactor

"""
default actor to print the message from user input
"""


def submit(ag, job_def) -> None:
    # Submit the job in a try/except block
    try:
        # Submit the job and get the job ID
        job_id = ag.jobs.submit(body=job_def)["id"]
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
    context = r.context  # Actor context
    print(json.dumps(context, indent=4))
    bids = pathlib.Path(context.bids)

    job_def = r.settings.main
    job_def.name = f"qaphantom_{bids.name}"
    job_def.archivePath = str(
        bids.relative_to("/corral-secure/projects/A2CPS")
    ).replace("/bids/", "/aa-fmri-phantom-qa/")
    job_def["parameters"]["BIDS"] = str(bids)

    submit(ag=r.client, job_def=job_def)

    return


if __name__ == "__main__":
    main()
