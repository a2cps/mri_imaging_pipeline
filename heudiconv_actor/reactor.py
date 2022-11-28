from reactors.utils import Reactor
import copy
import json
import os
from pathlib import Path


def _make_callback(server: str, alias: str, nonce: str) -> str:
    return f"{server}/actors/v2/{alias}/messages?x-nonce={os.getenv(nonce)}"


def submit_heudiconv(
    r, site: str, subject_id: str, session: str, dicoms: str, outdir: Path
) -> None:
    # Create agave client from reactor object
    ag = r.client
    # copy our job.json from config.yml
    job_def = copy.copy(r.settings.heudiconv)
    parameters = job_def["parameters"]
    # Define the input for the job as the file that
    # was sent in the notificaton message
    parameters["FILES"] = dicoms
    # split subject from path
    parameters["LIST_OF_SUBJECTS"] = subject_id
    parameters["SESSION_FOR_LONGITUDINAL"] = session
    parameters["SITE"] = site
    job_def.parameters = parameters
    archivePath = str(outdir.relative_to("/corral-secure/projects/A2CPS/"))

    job_def.archivePath = str(archivePath)
    job_def.name = f"heudiconv-{outdir.name}"

    try:
        pipeline_config = copy.copy(r.settings.pipelines)

        fmriprep_callback = _make_callback(
            server=pipeline_config["api_server"],
            alias=pipeline_config["fmriprep_alias"],
            nonce="_FMRIPREP_NONCE",
        )

        mriqc_callback = _make_callback(
            server=pipeline_config["api_server"],
            alias=pipeline_config["mriqc_alias"],
            nonce="_MRIQC_NONCE",
        )

        qsiprep_callback = _make_callback(
            server=pipeline_config["api_server"],
            alias=pipeline_config["qsiprep_alias"],
            nonce="_QSIPREP_NONCE",
        )

        cat_callback = _make_callback(
            server=pipeline_config["api_server"],
            alias=pipeline_config["cat_alias"],
            nonce="_CAT12_NONCE",
        )

        qaphantom_callback = _make_callback(
            server=pipeline_config["api_server"],
            alias=pipeline_config["qaphantom_alias"],
            nonce="_QAPHANTOM_NONCE",
        )

    except Exception as e:
        print(e)
        r.logger.error("Unable to generate Audit callback")

    # "filename" is esentially the patient_id.
    # it'll end up as the output directory name for cat12,
    # the jobs names for mriqc/qsiprep
    # and is parsed to get session (ex V1) for qsiprep
    filename = str(outdir.name)

    if "QC" in outdir.name:
        notif = [
            {
                "event": "FINISHED",
                "persistent": False,
                "url": qaphantom_callback
                + "&status=${JOB_STATUS}"
                + "&bids="
                + str(outdir)
                + "&site="
                + site
                + "&filename="
                + filename,
            }
        ]
    else:
        notif = [
            {
                "event": "FINISHED",
                "persistent": False,
                "url": fmriprep_callback
                + "&status=${JOB_STATUS}"
                + "&subject_id="
                + subject_id
                + "&bids="
                + str(outdir)
                + "&filename="
                + filename
                + "&site="
                + site
                + "&next_step=anat",
            },
            {
                "event": "FINISHED",
                "persistent": False,
                "url": mriqc_callback
                + "&status=${JOB_STATUS}"
                + "&subject_id="
                + subject_id
                + "&bids="
                + str(outdir)
                + "&filename="
                + filename
                + "&site="
                + site,
            },
            {
                "event": "FINISHED",
                "persistent": False,
                "url": qsiprep_callback
                + "&status=${JOB_STATUS}"
                + "&subject_id="
                + subject_id
                + "&bids="
                + str(outdir)
                + "&filename="
                + filename
                + "&site="
                + site,
            },
            {
                "event": "FINISHED",
                "persistent": False,
                "url": cat_callback
                + "&status=${JOB_STATUS}"
                + "&bids="
                + str(outdir)
                + "&filename="
                + filename
                + "&site="
                + site
                + "&subject_id="
                + subject_id,
            },
        ]

    job_def.notifications = notif
    # Submit the job in a try/except block
    try:
        # Submit the job and get the job ID
        job_id = ag.jobs.submit(body=job_def)["id"]
        print(job_id)
        print(json.dumps(job_def, indent=4))
    except Exception as e:
        print(json.dumps(job_def, indent=4))
        print(f"Error submitting job: {e}")
        print(e.response.content)
        return
    return


def main() -> None:
    """Main function"""
    # create the reactor object
    r = Reactor()
    r.logger.info(f"Hello this is actor {r.uid}")
    # pull in reactor context
    context = r.context
    # print(context)
    # get the message that was sent to the actor
    message = context.message_dict
    site = message["site_id"]
    subject_id = message["subject_id"]
    session = message["session_id"]
    dicoms: str = message["dicoms"]

    outdir = Path(dicoms.replace("dicoms", "bids")).with_suffix("")

    submit_heudiconv(r, site, subject_id, session, dicoms, outdir)


if __name__ == "__main__":
    main()
