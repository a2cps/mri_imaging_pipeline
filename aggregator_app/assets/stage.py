import logging
import os
import shutil
import tempfile
from pathlib import Path


import click

import utils
import bids_wf
import cat12_wf
import fmriprep_wf
import freesurfer_wf
import mriqc_wf
#import qsiprep_wf
import fslanat_wf



SITE_LONG = {
    "NS": "NS_northshore",
    "UI": "UI_uic",
    "UC": "UC_uchicago",
    "UM": "UM_umichigan",
    "SH": "SH_spectrum_health",
    "WS": "WS_wayne_state",
}

JOBS = ["bids", "fmriprep", "cat12", "mriqc", "fslanat"]


def _test_sub(
    subsesdir: Path,
    outroot: Path,
    inroot: Path,
    site_long: str,
) -> bool:
    sub = utils._get_sub(subsesdir)
    ses = utils._get_ses(subsesdir)
    not_already_processed = not all(
        (outroot / j / f"sub-{sub}" / f"ses-{ses}").exists()
        for j in [
            "bids",
            "fmriprep-anat",
            "fmriprep-cuff",
            "fmriprep-rest",
            "mriqc",
        ]
    )
    not_already_processed_fs = not (
        (outroot / "freesurfer" / f"sub-{sub}_ses-{ses}").exists()
    )
    not_already_processed_fslanat = not (
        (outroot / "fslanat" / f"sub-{sub}_ses-{ses}.anat").exists()
    )
    not_already_processed_cat = not (
        (
            outroot
            / "cat12"
            / "report"
            / f"catreport_sub-{sub}_ses-{ses}_T1w.pdf"
        ).exists()
    )

    all_regular_outputs_not_empty = all(
        (jobdir := (inroot / site_long / j / subsesdir.name)).exists()
        and len(list(jobdir.iterdir()))
        for j in JOBS
    )
    all_subdirs_not_empty = all(
        (
            modalitydir := (inroot / site_long / j / subsesdir.name / modality)
        ).exists()
        and len(list(modalitydir.iterdir()))
        for j in ["mriqc", "fmriprep"]
        for modality in ["anat", "rest", "cuff"]
    )
    return (
        not_already_processed
        and not_already_processed_fs
        and not_already_processed_fslanat
        and not_already_processed_cat
        and all_regular_outputs_not_empty
        and all_subdirs_not_empty
    )


def _prep_staged_dir(outroot: Path) -> None:
    # delete broken symlinks (e.g., files created by previous run of heudiconv that no longer exist)
    for target in os.walk(outroot):
        tar_dir = Path(target[0])
        for f in target[2]:
            if not (broken := tar_dir / f).exists():
                logging.warning(f"deleting broken symlink: {broken}")
                broken.unlink()

    # delete empty directories
    for target in os.walk(outroot, topdown=False):
        if (len(target[1] + target[2]) == 0) and (
            (to_del := Path(target[0])).name
            not in [
                "tmp",
                "bak",
                "trash",
            ]  # these folders from FreeSurfer are generally empty (and should be kept)
        ):
            logging.warning(f"deleting empty directory: {to_del}")
            os.removedirs(to_del)


@click.command()
@click.argument(
    "inroot",
    type=click.Path(
        exists=True, file_okay=False, resolve_path=True, path_type=Path
    ),
)
@click.argument(
    "outroot",
    type=click.Path(
        exists=False, file_okay=False, resolve_path=True, path_type=Path
    ),
)
@click.option("--max-subs", type=float, default=float("inf"))
def _main(
    inroot: Path, outroot: Path, max_subs: float | int = float("inf")
) -> None:
    _prep_staged_dir(outroot=outroot)
    i = 0
    # only work with subs/sessions that have all jobs done (need fmriprep-anat for masking)
    # and only make copies of subs/sessions that do not already exist in outroot
    with tempfile.TemporaryDirectory() as tmpd:
        tmpdir = Path(tmpd)
        # Recursively create symlinks in the target directory
        for site_code, site_long in SITE_LONG.items():
            subses_tocopy: set[str] = set()
            for job in JOBS:
                in_job_dir = inroot / site_long / job

                # grab only sub/ses that do not already exist in output
                # and that have complete jobs
                for subsesdir in in_job_dir.glob(f"{site_code}*V[13]"):
                    if i >= max_subs:
                        continue
                    if _test_sub(
                        subsesdir=subsesdir,
                        outroot=outroot,
                        inroot=inroot,
                        site_long=site_long,
                    ):
                        subses_tocopy.add(subsesdir.name)
                        i += 1

            tmp_site = tmpdir / site_long
            for subsesd in subses_tocopy:
                subsesdir = Path(subsesd)
                for job in JOBS:
                    out_job_dir = tmp_site / job
                    outsubses = out_job_dir / subsesdir
                    shutil.copytree(
                        inroot / site_long / job / subsesdir,
                        outsubses,
                        copy_function=utils._symlink_if_needed,
                        ignore=shutil.ignore_patterns(
                            "work", "*_wf", "sourcedata"
                        ),
                    )

                # mask all images
                utils._deface_all(subsesdir=subsesdir, tmp_site=tmp_site)

            # now aggregate all new participants
            # testing for len(subses_tocopy) to handle cases where no participants
            # were copied into the ouptut directory (e.g., during testing)
            if len(subses_tocopy):
                bids_wf.main(inroot=tmp_site, outdir=outroot / "bids")
                cat12_wf.main(inroot=tmp_site, outdir=outroot / "cat12")
                # qsiprep_wf.main(inroot=tmp_site, outdir=outroot / "qsiprep")
                mriqc_wf.main(inroot=tmp_site, outdir=outroot / "mriqc")
                fmriprep_wf.main(
                    inroot=tmp_site, outdir=outroot / "fmriprep-anat"
                )
                fmriprep_wf.main(
                    inroot=tmp_site, outdir=outroot / "fmriprep-cuff"
                )
                fmriprep_wf.main(
                    inroot=tmp_site, outdir=outroot / "fmriprep-rest"
                )
                freesurfer_wf.main(
                    inroot=tmp_site, outdir=outroot / "freesurfer"
                )
                fslanat_wf.main(inroot=tmp_site, outdir=outroot / "fslanat")


if __name__ == "__main__":
    _main()  # type: ignore
