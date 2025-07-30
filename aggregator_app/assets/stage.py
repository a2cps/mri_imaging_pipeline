import argparse
import logging
import os
import shutil
import tempfile
from pathlib import Path

import bedpostx_wf
import bids_wf
import brainager_wf
import cat12_wf
import fcn_wf
import fmriprep_wf
import freesurfer_wf
import fslanat_wf
import gift_wf
import idps
import mriqc_wf
import polars as pl
import postdtifit_wf
import qsiprep_wf
import qsirecon_fsl_dtifit_wf
import signatures_wf
import synthstrip_wf
import utils
from biomarkers import utils as bu
from biomarkers.models import fslanat

bu.configure_root_logger()


SITE_LONG = {
    "NS": "NS_northshore",
    "UI": "UI_uic",
    "UC": "UC_uchicago",
    "UM": "UM_umichigan",
    "SH": "SH_spectrum_health",
    "WS": "WS_wayne_state",
    "RU": "RU_rush",
}


ILOG = Path(
    "/corral-secure/projects/A2CPS/shared/urrutia/imaging_report/imaging_log.csv"
)


BIDS_IGNORE_PATTERNS = shutil.ignore_patterns(
    "sourcedata",
    "*007.out",
    "*007.err",
    "__pycache__",
    ".heudiconv",
    ".agave.log",
)


DERIV_IGNORE_PATTERNS = shutil.ignore_patterns(
    "work",
    "*_wf",
    "*007.out",
    "*007.err",
    "__pycache__",
    ".agave.log",
)


def _make_sublong(site: str, subject_id: str, visit: str) -> str:
    return f"{site}{subject_id}{visit}"


def is_fmriprep_aggregated(path: Path, row) -> bool:
    sub = row["subject_id"]
    ses = row["visit"]
    all_ready = False

    target = path / f"sub-{sub}" / f"ses-{ses}"
    if target.exists():
        all_ready = (path / f"sub-{sub}_ses-{ses}.html").exists()
        if not all_ready:
            logging.error(f"{sub=}, {ses=} did not pass fmriprep validation")
            shutil.rmtree(target)

    return all_ready


def is_qsiprep_aggregated(path: Path, row) -> bool:
    sub = row["subject_id"]
    ses = row["visit"]
    qsiprep_dir = Path(f"{path}-{ses}")
    qsiprep_target = qsiprep_dir / f"sub-{sub}" / f"ses-{ses}"
    eddy_target = path / "eddyqc" / f"sub-{sub}" / f"ses-{ses}"
    all_ready = (
        qsiprep_target.exists()
        & (qsiprep_dir / f"sub-{sub}.html").exists()
        & eddy_target.exists()
    )

    if not all_ready:
        if eddy_target.exists():
            shutil.rmtree(eddy_target)
        if qsiprep_target.exists():
            shutil.rmtree(qsiprep_target)

    return all_ready


def is_qsirecon_fsl_dtifit_aggregated(path: Path, row) -> bool:
    sub = row["subject_id"]
    ses = row["visit"]
    qsirecon_dir = path / "qsirecon-fsl"
    qsirecon_target = (
        qsirecon_dir
        / "derivatives"
        / "qsirecon-FSL"
        / f"sub-{sub}"
        / f"ses-{ses}"
        / "dwi"
    )
    split_shells_target = path / "split_shells" / f"sub-{sub}" / f"ses-{ses}" / "dwi"
    dtifit_dirs = [
        path / "dtifit" / bval / f"sub-{sub}" / f"ses-{ses}"
        for bval in ["b1000", "b2000", "b3000", "multishell"]
    ]
    all_ready = (
        qsirecon_target.exists()
        & split_shells_target.exists()
        & all(dtifit_dir.exists() for dtifit_dir in dtifit_dirs)
    )

    if not all_ready:
        if qsirecon_target.exists():
            shutil.rmtree(qsirecon_target)
        if split_shells_target.exists():
            shutil.rmtree(split_shells_target)
        for dtifit_dir in dtifit_dirs:
            if dtifit_dir.exists():
                shutil.rmtree(dtifit_dir)

    return all_ready


def is_mriqc_aggregated(mriqc_root: Path, row) -> bool:
    sub = row["subject_id"]
    ses = row["visit"]

    target = mriqc_root / f"sub-{sub}" / f"ses-{ses}"
    all_ready = False
    if target.exists():
        htmls = []
        if row["T1 Received"] == 1:
            htmls.append((mriqc_root / f"sub-{sub}_ses-{ses}_T1w.html").exists())
        if row["fMRI Individualized Pressure Received"] == 1:
            htmls.append(
                (
                    mriqc_root / f"sub-{sub}_ses-{ses}_task-cuff_run-01_bold.html"
                ).exists()
            )
        if row["fMRI Standard Pressure Received"] == 1:
            htmls.append(
                (
                    mriqc_root / f"sub-{sub}_ses-{ses}_task-cuff_run-02_bold.html"
                ).exists()
            )
        if row["1st Resting State Received"] == 1:
            htmls.append(
                (
                    mriqc_root / f"sub-{sub}_ses-{ses}_task-rest_run-01_bold.html"
                ).exists()
            )
        if row["2nd Resting State Received"] == 1:
            htmls.append(
                (
                    mriqc_root / f"sub-{sub}_ses-{ses}_task-rest_run-02_bold.html"
                ).exists()
            )

        all_ready = all(htmls)
        if not all_ready:
            logging.info(f"{sub=}, {ses=} did not pass mriqc validation")
            shutil.rmtree(target)

    return all_ready


def _cleaned_niis_avail(cleaned_root: Path, row) -> bool:
    sub = row["subject_id"]
    ses = row["visit"]
    niis = []
    if row["fMRI Individualized Pressure Received"] == 1:
        niis.append(
            (
                cleaned_root
                / f"sub-{sub}_ses-{ses}_task-cuff_run-1_desc-preproc_bold.nii.gz"
            ).exists()
        )
    if row["fMRI Standard Pressure Received"] == 1:
        niis.append(
            (
                cleaned_root
                / f"sub-{sub}_ses-{ses}_task-cuff_run-2_desc-preproc_bold.nii.gz"
            ).exists()
        )
    if row["1st Resting State Received"] == 1:
        niis.append(
            (
                cleaned_root
                / f"sub-{sub}_ses-{ses}_task-rest_run-1_desc-preproc_bold.nii.gz"
            ).exists()
        )
    if row["2nd Resting State Received"] == 1:
        niis.append(
            (
                cleaned_root
                / f"sub-{sub}_ses-{ses}_task-rest_run-2_desc-preproc_bold.nii.gz"
            ).exists()
        )
    return all(niis)


def is_signatures_aggregated(path: Path, row) -> bool:
    all_dirs = [
        (path / sig / f"sub={row['subject_id']}" / f"ses={row['visit']}")
        for sig in [
            "signature-by-part",
            "signature-by-run",
            "signature-by-tr",
            "signature-labels",
            "signature-rawdata",
        ]
    ]
    all_ready = False
    if all([d.exists() for d in all_dirs]):
        all_ready = _cleaned_niis_avail(path / "signature-cleaned", row)
        if not all_ready:
            logging.error(
                f"sub={row['subject_id']}, ses={row['visit']} did not pass signatures validation"
            )
            for d in all_dirs:
                shutil.rmtree(d)

    return all_ready


def is_fcn_aggregated(path: Path, row) -> bool:
    all_dirs = (
        (path / fcn / f"sub={row['subject_id']}" / f"ses={row['visit']}")
        for fcn in ["acompcor", "connectivity", "connectivity-confounds"]
    )
    all_ready = False
    if all([d.exists() for d in all_dirs]):
        all_ready = _cleaned_niis_avail(path / "connectivity-cleaned", row)
        if not all_ready:
            logging.error(
                f"sub={row['subject_id']}, ses={row['visit']} did not pass fcn validation"
            )
            for d in all_dirs:
                shutil.rmtree(d)

    return all_ready


def is_brainager_aggregated(path: Path, row) -> bool:
    target = (
        path
        / f"sub-{row['subject_id']}"
        / f"ses-{row['visit']}"
        / f"sub-{row['subject_id']}_ses-{row['visit']}_T1w.nii"
    )
    all_ready = False
    if target.exists():
        all_ready = (
            target.with_name(f"{target.stem}_tissue_volumes.tsv").exists()
            and target.with_suffix(".tsv").exists()
            and target.with_name(f"slicesdir_{target.name}").exists()
        )
        if not all_ready:
            logging.error(
                f"sub={row['subject_id']}, ses={row['visit']} did not pass brainager validation"
            )
            shutil.rmtree(target.parent)

    return all_ready


def is_fslanat_aggregated(path: Path, row) -> bool:
    target = path / f"sub-{row['subject_id']}_ses-{row['visit']}_T1w.anat"
    all_ready = False
    if target.exists():
        try:
            fslanat.FSLAnatResult.from_root(target)
            all_ready = True
        except Exception:
            logging.exception(f"{target} did not pass fslanat validation")
            shutil.rmtree(target)

    return all_ready


def is_cat12_aggregated(path: Path, row) -> bool:
    return (
        path
        / "report"
        / f"catreport_sub-{row['subject_id']}_ses-{row['visit']}_T1w.pdf"
    ).exists()


def is_gift_aggregated(path: Path, row) -> bool:
    return (path / f"sub-{row['subject_id']}" / f"ses-{row['visit']}").exists()


def is_bedpostx_aggregated(path: Path, row) -> bool:
    return (path / f"sub-{row['subject_id']}" / f"ses-{row['visit']}").exists()


def is_postgift_aggregated(path: Path, row) -> bool:
    all_dirs = (
        (path / subdir / f"sub={row['subject_id']}" / f"ses={row['visit']}")
        for subdir in ["amplitude", "biomarkers", "connectivity"]
    )
    return all([d.exists() for d in all_dirs])


def is_postdtifit_aggregated(path: Path, row) -> bool:
    return (
        path
        / "diffusion_regional"
        / f"sub-{row['subject_id']}"
        / f"ses-{row['visit']}"
        / "dwi"
        / f"sub-{row['subject_id']}_ses-{row['visit']}_space-dwi_desc-JHUICBM_dseg.nii.gz"
    ).exists() and (
        path
        / "diffusion_regional_stats"
        / f"sub={row['subject_id']}"
        / f"ses-{row['visit']}"
        / "0.parquet"
    ).exists()


def is_dwi_biomarker1_aggregated(path: Path, row) -> bool:
    all_dirs = (
        (path / subdir / f"sub-{row['subject_id']}" / f"ses-{row['visit']}")
        for subdir in ["move_masks", "networks", "probtrackx"]
    )
    return all([d.exists() for d in all_dirs])


def get_deriv_tocopy(outroot: Path, site_code: str) -> dict[str, list[str]]:
    ready = pl.read_csv(ILOG, null_values=["", "na", "n/a"]).filter(
        pl.col("site") == site_code
    )

    job_aggregators = {
        "fmriprep": is_fmriprep_aggregated,
        "qsiprep": is_qsiprep_aggregated,
        "brainager": is_brainager_aggregated,
        "cat12": is_cat12_aggregated,
        "mriqc": is_mriqc_aggregated,
        "fslanat": is_fslanat_aggregated,
        "fcn": is_fcn_aggregated,
        "signatures": is_signatures_aggregated,
        "gift": is_gift_aggregated,
        "qsirecon_fsl_dtifit": is_qsirecon_fsl_dtifit_aggregated,
        "bedpostx": is_bedpostx_aggregated,
        "postgift": is_postgift_aggregated,
        "postdtifit": is_postdtifit_aggregated,
        "dwi_biomarker1": is_dwi_biomarker1_aggregated,
    }

    # now, get list of jobs that will need to be copied over,
    # which can differ for each sub/ses (e.g., no dwi means no qsiprep)
    # this is rare, but see NS10205V1 (for which there is nothing)
    derivatives: dict[str, list[str]] = dict()
    for row in ready.iter_rows(named=True):
        jobs = set()
        for name, is_aggregated in job_aggregators.items():
            if row[name] == 1 and not is_aggregated(outroot / name, row):
                jobs.add(name)

        if len(to_agg := list(jobs)) >= 0:
            derivatives.update(
                {_make_sublong(row["site"], row["subject_id"], row["visit"]): to_agg}
            )

    return derivatives


def prep_staged_dir(outroot: Path) -> None:
    # delete broken symlinks (e.g., files created by previous run of heudiconv
    # that no longer exist)
    for target in os.walk(outroot):
        tar_dir = Path(target[0])
        for f in target[2]:
            if not (broken := tar_dir / f).exists():
                logging.warning(f"deleting broken symlink: {broken}")
                broken.unlink()

    # delete empty directories
    for target in os.walk(outroot, topdown=False):
        if len(target[1] + target[2]) == 0:
            to_del = Path(target[0])
            logging.warning(f"deleting empty directory: {to_del}")
            os.removedirs(to_del)


def get_bids_tocopy(inroot: Path, outroot: Path, site_code: str) -> set[str]:
    bids_avail = (
        pl.read_csv(ILOG, null_values=["", "na", "n/a"])
        .filter(pl.col("bids") == 1, pl.col("site") == site_code)
        .select("site", "subject_id", "visit")
    )
    exists: dict[str, bool] = {}
    for row in bids_avail.iter_rows(named=True):
        sublong = _make_sublong(row["site"], row["subject_id"], row["visit"])  # type: ignore
        exists[sublong] = (
            len(list((inroot / SITE_LONG[site_code] / "bids" / sublong).glob("*out")))
            > 0
        ) and not (
            outroot / "bids" / f"sub-{row['subject_id']}" / f"ses-{row['visit']}"
        ).exists()
    return set(k for k, v in exists.items() if v)


def main(
    inroot: Path, outroot: Path, max_subs: float | int = float("inf"), tidy: bool = True
) -> None:
    if tidy:
        logging.info("tidying output directory")
        prep_staged_dir(outroot=outroot)
    with tempfile.TemporaryDirectory() as tmpd:
        tmpdir = Path(tmpd)
        for site_code, site_long in SITE_LONG.items():
            logging.info(f"Working on participants from {site_long}")

            # first, get all new raw (bids) data
            tmp_site = tmpdir / site_long
            bidstocopy = get_bids_tocopy(
                inroot=inroot, outroot=outroot, site_code=site_code
            )
            for i, subsesd in enumerate(bidstocopy):
                if i >= max_subs:
                    break
                logging.info(f"Making bids symlinks for {subsesd}")
                out_job_dir = tmp_site / "bids"
                shutil.copytree(
                    inroot / site_long / "bids" / subsesd,
                    out_job_dir / subsesd,
                    copy_function=utils.symlink_if_needed,
                    ignore=BIDS_IGNORE_PATTERNS,
                )

            if len(bidstocopy):
                logging.info("Copying bids files to destination")
                bids_wf.copy(inroot=tmp_site, outdir=outroot / "bids")

            # grab only sub/ses that do not already exist in output
            subses_tocopy = get_deriv_tocopy(outroot=outroot, site_code=site_code)

            # then, get all available derivatives
            for i, (subsesd, jobs) in enumerate(subses_tocopy.items()):
                if i >= max_subs:
                    break
                logging.info(f"Making initial symlinks for {subsesd} derivatives")
                for job in jobs:
                    logging.info(f"Making links for {job}")
                    shutil.copytree(
                        inroot / site_long / job / subsesd,
                        tmp_site / job / subsesd,
                        copy_function=utils.symlink_if_needed,
                        ignore=DERIV_IGNORE_PATTERNS,
                    )

            # now aggregate all new participants
            # testing for len(subses_tocopy) to handle cases where no participants
            # were copied into the ouptut directory (e.g., during testing)
            if len(subses_tocopy):
                logging.info("Storing derivatives in final location")
                cat12_wf.copy(inroot=tmp_site, outdir=outroot / "cat12")
                qsiprep_wf.copy(inroot=tmp_site, outdir=outroot)
                qsirecon_fsl_dtifit_wf.copy(
                    inroot=tmp_site, outdir=outroot / "qsirecon_fsl_dtifit"
                )
                brainager_wf.copy(inroot=tmp_site, outdir=outroot / "brainager")
                mriqc_wf.copy(inroot=tmp_site, outdir=outroot / "mriqc")
                fmriprep_wf.copy(inroot=tmp_site, outdir=outroot / "fmriprep")
                synthstrip_wf.copy(
                    inroot=tmp_site,
                    outdir=outroot / "synthstrip",
                    bidsdir=outroot / "bids",
                )
                freesurfer_wf.copy(inroot=tmp_site, outdir=outroot / "freesurfer")
                fslanat_wf.copy(inroot=tmp_site, outdir=outroot / "fslanat")
                fcn_wf.copy(inroot=tmp_site, outdir=outroot / "fcn")
                signatures_wf.copy(inroot=tmp_site, outdir=outroot / "signatures")
                gift_wf.copy(inroot=tmp_site, outdir=outroot / "gift")
                bedpostx_wf.copy(inroot=tmp_site, outdir=outroot / "bedpostx")
                utils.copy_with_subdirs(
                    inroot=tmp_site / "postgift",
                    outdir=outroot / "postgift",
                    subdirs=["amplitude", "biomarkers", "connectivity"],
                )
                postdtifit_wf.copy(inroot=tmp_site, outdir=outroot / "postdtifit")
                utils.copy_with_subdirs(
                    inroot=tmp_site / "dwi_biomarker1",
                    outdir=outroot / "dwi_biomarker1",
                    subdirs=["move_masks", "networks", "probtrackx"],
                )
            if tmp_site.exists():
                logging.info(f"Removing temporary directory for {site_long}")
                shutil.rmtree(tmp_site)

        # finally, handle all toplevel file material
        logging.info("Adding toplevel files")
        bids_wf.make_toplevel(outdir=outroot / "bids")
        cat12_wf.make_toplevel(outdir=outroot / "cat12")
        mriqc_wf.make_toplevel(outdir=outroot / "mriqc")
        fcn_wf.make_toplevel(outdir=outroot / "fcn")
        fmriprep_wf.make_toplevel(outdir=outroot / "fmriprep")
        freesurfer_wf.make_toplevel(outdir=outroot / "freesurfer")
        fslanat_wf.make_toplevel(outdir=outroot / "fslanat")
        qsirecon_fsl_dtifit_wf.make_toplevel(outdir=outroot / "qsirecon_fsl_dtifit")
        idps.make_toplevel(outroot)

        logging.info("Finished!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("inroot", type=Path)
    parser.add_argument("outroot", type=Path)
    parser.add_argument("--max-subs", type=float, default=float("inf"))
    parser.add_argument("--tidy", action=argparse.BooleanOptionalAction, default=True)

    args = parser.parse_args()

    main(
        inroot=args.inroot, outroot=args.outroot, max_subs=args.max_subs, tidy=args.tidy
    )
