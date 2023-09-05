import logging
import os
import shutil
import tempfile
from pathlib import Path

import bids_wf
import cat12_wf
import click
import fmriprep_wf
import freesurfer_wf
import fslanat_wf
import mriqc_wf
import pandas as pd
import utils
from mriqc.interfaces import synthstrip

SYNTHSTRIP_MODEL = Path("/opt/synthstrip.1.pt")

SITE_LONG = {
    "NS": "NS_northshore",
    "UI": "UI_uic",
    "UC": "UC_uchicago",
    "UM": "UM_umichigan",
    "SH": "SH_spectrum_health",
    "WS": "WS_wayne_state",
}

JOBS_DERIVATIVES = ["fmriprep", "cat12", "mriqc", "fslanat"]

ILOG = Path(
    "/corral-secure/projects/A2CPS/community/reports/imaging/imaging-log-latest.csv"
)

IGNORE_PATTERNS = shutil.ignore_patterns(
    "work",
    "*_wf",
    "sourcedata",
    "*007.out",
    "*007.err",
    "__pycache__",
)


def _check_if_already_aggregated(subsesdir: Path, outroot: Path) -> bool:
    sub = utils._get_sub(subsesdir)
    ses = utils._get_ses(subsesdir)
    already_aggregated_simple = all(
        (outroot / j / f"sub-{sub}" / f"ses-{ses}").exists()
        for j in ["fmriprep-anat", "fmriprep-cuff", "fmriprep-rest", "mriqc"]
    )
    already_aggregated_fs = (
        outroot / "freesurfer" / f"sub-{sub}_ses-{ses}"
    ).exists()
    already_aggregated_fslanat = (
        outroot / "fslanat" / f"sub-{sub}_ses-{ses}.anat"
    ).exists()
    already_aggregated_cat = (
        outroot / "cat12" / "report" / f"catreport_sub-{sub}_ses-{ses}_T1w.pdf"
    ).exists()

    return (
        already_aggregated_simple
        and already_aggregated_fs
        and already_aggregated_fslanat
        and already_aggregated_cat
    )


def _get_deriv_tocopy(outroot: Path, site_code: str) -> set[str]:
    ready: pd.DataFrame = (
        pd.read_csv(ILOG)
        .query("site == @site_code")
        .query(
            """fslanat in ['1', 'na'] and \
            fmriprep_anat in ['1', 'na'] and \
            fmriprep_rest in ['1', 'na'] and \
            fmriprep_cuff in ['1', 'na'] and \
            mriqc_anat in ['1', 'na'] and \
            mriqc_rest in ['1', 'na'] and \
            mriqc_cuff in ['1', 'na'] and \
            cat12 in ['1', 'na']"""
        )[["site", "subject_id", "visit"]]
    )
    ready["already_aggregated"] = [
        _check_if_already_aggregated(
            f"{row.site}{row.subject_id}{row.visit}", outroot=outroot  # type: ignore
        )
        for row in ready.itertuples()
    ]
    out = ready.query("not already_aggregated")
    return set(
        f"{row.site}{row.subject_id}{row.visit}" for row in out.itertuples()
    )


def _prep_staged_dir(outroot: Path) -> None:
    # delete broken symlinks (e.g., files created by previous run of heudiconv
    # that no longer exist)
    for target in os.walk(outroot):
        tar_dir = Path(target[0])
        for f in target[2]:
            if not (broken := tar_dir / f).exists():
                logging.warning(f"deleting broken symlink: {broken}")
                broken.unlink()
        # if the only remaining file is a nii.gz that is a real file, it
        # is a holdover and should also be deleted
        if (
            len(target[2]) == 1
            and target[2][0].endswith(".nii.gz")
            and not (todelete := Path(target[2][0])).is_symlink()
        ):
            todelete.unlink()

    # delete empty directories
    for target in os.walk(outroot, topdown=False):
        if (len(target[1] + target[2]) == 0) and (
            (to_del := Path(target[0])).name
            not in [
                "tmp",
                "bak",
                "trash",
            ]  # from FreeSurfer, generally empty (and should be kept)
        ):
            logging.warning(f"deleting empty directory: {to_del}")
            os.removedirs(to_del)


def _get_bids_tocopy(outroot: Path, site_code: str) -> set[str]:
    bids_avail: pd.DataFrame = pd.read_csv(ILOG).query(
        "bids == 1 and site == @site_code"
    )[["site", "subject_id", "visit"]]
    exists: list[bool] = []
    for row in bids_avail.itertuples():
        exists.append(
            (
                outroot / "bids" / f"sub-{row.subject_id}" / f"ses-{row.visit}"
            ).exists()
        )
    bids_avail["exists"] = exists
    out = bids_avail.query("not exists")
    return set(
        f"{row.site}{row.subject_id}{row.visit}" for row in out.itertuples()
    )


def _synthstrip(src: Path) -> Path:
    with tempfile.NamedTemporaryFile(suffix=".nii.gz") as mask:
        with tempfile.NamedTemporaryFile(suffix=".nii.gz") as brain:
            strip = synthstrip.SynthStrip()
            strip.inputs.in_file = src
            strip.inputs.out_file = brain.name
            strip.inputs.out_mask = mask.name
            strip.inputs.model = SYNTHSTRIP_MODEL
            strip.run()
            src.unlink()
            shutil.copy2(brain.name, src)
    return src


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
    logging.warning("tidying output directory")
    _prep_staged_dir(outroot=outroot)
    with tempfile.TemporaryDirectory() as tmpd:
        tmpdir = Path(tmpd)
        for site_code, site_long in SITE_LONG.items():
            print(f"Working on participants from {site_long}")

            # first, get all new raw (bids) data
            tmp_site = tmpdir / site_long
            bidstocopy = _get_bids_tocopy(outroot=outroot, site_code=site_code)
            for i, subsesd in enumerate(bidstocopy):
                if i >= max_subs:
                    break
                print(f"Making bids symlinks for {subsesd}")
                out_job_dir = tmp_site / "bids"
                shutil.copytree(
                    inroot / site_long / "bids" / subsesd,
                    out_job_dir / subsesd,
                    copy_function=utils._symlink_if_needed,
                    ignore=IGNORE_PATTERNS,
                )
                print(f"Defacing anatomicals for {subsesd}")
                for t1w in (out_job_dir / subsesd).rglob("*T1w.nii.gz"):
                    _synthstrip(t1w)

            if len(bidstocopy):
                print("Copying bids files to destination")
                bids_wf.main(inroot=tmp_site, outdir=outroot / "bids")

            # grab only sub/ses that do not already exist in output
            # and that have complete jobs
            subses_tocopy = _get_deriv_tocopy(
                outroot=outroot, site_code=site_code
            )

            # then, get all available derivatives
            subses_toremove: set[str] = set()
            for i, subsesd in enumerate(subses_tocopy):
                if i >= max_subs:
                    break
                print(f"Making initial symlinks for {subsesd} derivatives")
                for job in JOBS_DERIVATIVES:
                    shutil.copytree(
                        inroot / site_long / job / subsesd,
                        tmp_site / job / subsesd,
                        copy_function=utils._symlink_if_needed,
                        ignore=IGNORE_PATTERNS,
                    )

                # mask all images
                if not utils._deface_all_derivatives(
                    subsesdir=Path(subsesd), tmp_site=tmp_site
                ):
                    for d in tmp_site.glob(f"*/{subsesd}"):
                        shutil.rmtree(d)
                    subses_toremove.add(subsesd)

            for s in subses_toremove:
                subses_tocopy.remove(s)

            # now aggregate all new participants
            # testing for len(subses_tocopy) to handle cases where no participants
            # were copied into the ouptut directory (e.g., during testing)
            if len(subses_tocopy):
                print("Storing derivatives in final location")
                cat12_wf.copy(inroot=tmp_site, outdir=outroot / "cat12")
                # qsiprep_wf.main(inroot=tmp_site, outdir=outroot / "qsiprep")
                mriqc_wf.copy(inroot=tmp_site, outdir=outroot / "mriqc")
                fmriprep_wf.copy(
                    inroot=tmp_site, outdir=outroot / "fmriprep-anat"
                )
                fmriprep_wf.copy(
                    inroot=tmp_site, outdir=outroot / "fmriprep-cuff"
                )
                fmriprep_wf.copy(
                    inroot=tmp_site, outdir=outroot / "fmriprep-rest"
                )
                freesurfer_wf.copy(
                    inroot=tmp_site, outdir=outroot / "freesurfer"
                )
                fslanat_wf.copy(inroot=tmp_site, outdir=outroot / "fslanat")

        # finally, handle all toplevel file material
        mriqc_wf.make_toplevel(outdir=outroot / "mriqc")
        fmriprep_wf.make_toplevel(outdir=outroot / "fmriprep-anat")
        fmriprep_wf.make_toplevel(outdir=outroot / "fmriprep-cuff")
        fmriprep_wf.make_toplevel(outdir=outroot / "fmriprep-rest")
        freesurfer_wf.make_toplevel(outdir=outroot / "freesurfer")
        fslanat_wf.make_toplevel(outdir=outroot / "fslanat")


if __name__ == "__main__":
    _main()  # type: ignore
