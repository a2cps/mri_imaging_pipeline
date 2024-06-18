import argparse
import logging
import os
import shutil
import subprocess
import tempfile
import re
from pathlib import Path

from biomarkers import utils as bu
from biomarkers.models import brainager, fslanat
import pandas as pd

import bids_wf
import brainager_wf
import cat12_wf
import fcn_wf
import fmriprep_wf
import freesurfer_wf
import fslanat_wf
import mriqc_wf
import qsiprep_wf
import signatures_wf
import gift_wf
import utils

bu.configure_root_logger()


SYNTHSTRIP_MODEL = Path("/opt/synthstrip.1.pt")

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


IGNORE_PATTERNS = shutil.ignore_patterns(
    "work",
    "*_wf",
    "sourcedata",
    "*007.out",
    "*007.err",
    "__pycache__",
    ".heudiconv",
    ".agave.log",
)


def _make_sublong(site: str, subject_id: str, visit: str) -> str:
    return f"{site}{subject_id}{visit}"


def is_directory_ready(path: Path) -> bool:
    return (
        path.exists()
        and (len(list(path.glob("*"))) > 0)
        and (any(i.is_dir() for i in path.glob("*")))
    )


def is_fmriprep_aggregated(path: Path, row) -> bool:
    sub = row.subject_id
    ses = row.visit
    job = re.findall(r"anat|cuff|rest", str(path))
    if not len(job):
        msg = f"unable to indetify fmriprep job in {path}"
        raise AssertionError(msg)
    fmriprep_dir = path / f"fmriprep-{job[0]}"
    return (fmriprep_dir / f"sub-{sub}" / f"ses-{ses}").exists() and (
        fmriprep_dir / f"sub-{sub}_ses-{ses}.html"
    ).exists()


def is_qsiprep_aggregated(path: Path, row) -> bool:
    sub = row.subject_id
    ses = row.visit
    qsiprep_dir = path / f"qsiprep-{ses}"
    eddy_dir = path / "eddyqc"

    return (
        (qsiprep_dir / f"sub-{sub}" / f"ses-{ses}").exists()
        and (qsiprep_dir / f"sub-{sub}.html").exists()
        and (eddy_dir / f"sub-{sub}" / f"ses-{ses}").exists()
    )


def is_mriqc_aggregated(mriqc_root: Path, row) -> bool:
    sub = row.subject_id
    ses = row.visit
    # The column names will be renamed to positional names if they
    # are invalid Python identifiers, repeated, or start with
    # an underscore.
    t1_received = row._5
    cuff1_received = row._8
    cuff2_received = row._10
    rest1_received = row._12
    rest2_received = row._14
    htmls = []
    if t1_received == 1:
        htmls.append((mriqc_root / f"sub-{sub}_ses-{ses}_T1w.html").exists())
    if cuff1_received == 1:
        htmls.append(
            (
                mriqc_root / f"sub-{sub}_ses-{ses}_task-cuff_run-01_bold.html"
            ).exists()
        )
    if cuff2_received == 1:
        htmls.append(
            (
                mriqc_root / f"sub-{sub}_ses-{ses}_task-cuff_run-02_bold.html"
            ).exists()
        )
    if rest1_received == 1:
        htmls.append(
            (
                mriqc_root / f"sub-{sub}_ses-{ses}_task-rest_run-01_bold.html"
            ).exists()
        )
    if rest2_received == 1:
        htmls.append(
            (
                mriqc_root / f"sub-{sub}_ses-{ses}_task-rest_run-02_bold.html"
            ).exists()
        )

    return (mriqc_root / f"sub-{sub}" / f"ses-{ses}").exists() and all(htmls)


def _cleaned_niis_avail(cleaned_root: Path, row) -> bool:
    sub = row.subject_id
    ses = row.visit
    cuff1_received = row._8
    cuff2_received = row._10
    rest1_received = row._12
    rest2_received = row._14
    niis = []
    if cuff1_received == 1:
        niis.append(
            (
                cleaned_root
                / f"sub-{sub}_ses-{ses}_task-cuff_run-1_desc-preproc_bold.nii.gz"
            ).exists()
        )
    if cuff2_received == 1:
        niis.append(
            (
                cleaned_root
                / f"sub-{sub}_ses-{ses}_task-cuff_run-2_desc-preproc_bold.nii.gz"
            ).exists()
        )
    if rest1_received == 1:
        niis.append(
            (
                cleaned_root
                / f"sub-{sub}_ses-{ses}_task-rest_run-1_desc-preproc_bold.nii.gz"
            ).exists()
        )
    if rest2_received == 1:
        niis.append(
            (
                cleaned_root
                / f"sub-{sub}_ses-{ses}_task-rest_run-2_desc-preproc_bold.nii.gz"
            ).exists()
        )
    return all(niis)


def is_signatures_aggregated(path: Path, row) -> bool:
    return all(
        (path / sig / f"sub={row.subject_id}" / f"ses={row.visit}").exists()
        for sig in [
            "signature-by-part",
            "signature-by-run",
            "signature-by-tr",
            "signature-labels",
            "signature-rawdata",
        ]
    ) and _cleaned_niis_avail(path / "signature-cleaned", row)


def is_fcn_aggregated(path: Path, row) -> bool:
    return all(
        (path / fcn / f"sub={row.subject_id}" / f"ses={row.visit}").exists()
        for fcn in [
            "acompcor",
            "connectivity",
            "connectivity-confounds",
        ]
    ) and _cleaned_niis_avail(path / "fcn-cleaned", row)


def is_brainager_aggregated(path: Path, row) -> bool:
    target = (
        path
        / "brainager"
        / f"sub-{row.subject_id}"
        / f"ses-{row.visit}"
        / f"sub-{row.subject_id}_ses-{row.visit}_T1w.nii"
    )
    try:
        brainager.BrainAgeResult.from_nii(target)
        out = True
    except Exception:
        logging.info(f"{target} did not pass validation. Adding to copy list")
        out = False

    return out


def is_fslanat_aggregated(path: Path, row) -> bool:
    target = (
        path / "fslanat" / f"sub-{row.subject_id}_ses-{row.visit}_T1w.anat"
    )
    try:
        fslanat.FIRSTResults.from_root(target)
        out = True
    except Exception:
        logging.info(f"{target} did not pass validation. Adding to copy list.")
        out = False

    return out


def _get_deriv_tocopy(
    outroot: Path, inroot: Path, site_code: str
) -> dict[str, list[str]]:
    ready: pd.DataFrame = (
        pd.read_csv(ILOG, na_values=["", "na", "n/a"])
        .query("site == @site_code")
        .query(
            """(fslanat == 1 | fslanat.isna()) \
            and (fmriprep_anat == 1 | fmriprep_anat.isna()) \
            and (fmriprep_rest == 1 | fmriprep_rest.isna()) \
            and (fmriprep_cuff == 1 | fmriprep_cuff.isna()) \
            and (mriqc_anat == 1 | mriqc_anat.isna()) \
            and (mriqc_rest == 1 | mriqc_rest.isna()) \
            and (mriqc_cuff  == 1 | mriqc_cuff.isna()) \
            and (cat12  == 1 | cat12.isna()) \
            and (fcn  == 1 | fcn.isna()) \
            and (signatures == 1 | signatures.isna()) \
            and (qsiprep  == 1 | qsiprep.isna()) \
            and (brainager  == 1 | brainager.isna()) \
            and (gift_rest  == 1 | gift_rest.isna()) \
            """
        )
    )
    # now, get list of jobs that will need to be copied over,
    # which can differ for each sub/ses (e.g., no dwi means no qsiprep)
    # this is rare, but see NS10205V1 (for which there is nothing)
    derivatives: dict[str, list[str]] = dict()
    for row in ready.itertuples():
        sublong = _make_sublong(row.site, row.subject_id, row.visit)  # type: ignore
        jobs = set()
        already_aggregated = True
        # cannot rely on imaging log only, because imaging log will say that a job is
        # done even when there are no outputs
        if row.fmriprep_anat == 1 and is_directory_ready(
            inroot / SITE_LONG[site_code] / "fmriprep" / sublong / "anat"
        ):
            already_aggregated &= is_fmriprep_aggregated(
                outroot / "fmriprep-anat", row
            )
            jobs.add("fmriprep")
        if row.fmriprep_rest == 1 and is_directory_ready(
            inroot / SITE_LONG[site_code] / "fmriprep" / sublong / "rest"
        ):
            already_aggregated &= is_fmriprep_aggregated(
                outroot / "fmriprep-rest", row
            )
            jobs.add("fmriprep")
        if row.fmriprep_cuff == 1 and is_directory_ready(
            inroot / SITE_LONG[site_code] / "fmriprep" / sublong / "cuff"
        ):
            already_aggregated &= is_fmriprep_aggregated(
                outroot / "fmriprep-cuff", row
            )
            jobs.add("fmriprep")
        if row.qsiprep == 1 and is_directory_ready(
            inroot / SITE_LONG[site_code] / "qsiprep" / sublong
        ):
            already_aggregated &= is_qsiprep_aggregated(outroot, row)
            jobs.add("qsiprep")

        if row.brainager == 1 and is_directory_ready(
            inroot / SITE_LONG[site_code] / "brainager" / sublong
        ):
            already_aggregated &= is_brainager_aggregated(outroot, row)
            jobs.add("brainager")

        if row.cat12 == 1 and is_directory_ready(
            inroot / SITE_LONG[site_code] / "cat12" / sublong
        ):
            already_aggregated &= (
                outroot
                / "cat12"
                / "report"
                / f"catreport_sub-{row.subject_id}_ses-{row.visit}_T1w.pdf"
            ).exists()
            jobs.add("cat12")
        if (
            (
                row.mriqc_anat == 1
                and is_directory_ready(
                    inroot / SITE_LONG[site_code] / "mriqc" / sublong / "anat"
                )
            )
            or (
                row.mriqc_rest == 1
                and is_directory_ready(
                    inroot / SITE_LONG[site_code] / "mriqc" / sublong / "rest"
                )
            )
            or (
                row.mriqc_cuff == 1
                and is_directory_ready(
                    inroot / SITE_LONG[site_code] / "mriqc" / sublong / "cuff"
                )
            )
        ):
            already_aggregated &= is_mriqc_aggregated(
                outroot / "mriqc", row=row
            )
            jobs.add("mriqc")
        if row.fslanat == 1 and is_directory_ready(
            inroot / SITE_LONG[site_code] / "fslanat" / sublong
        ):
            already_aggregated &= is_fslanat_aggregated(outroot, row)
            jobs.add("fslanat")
        if row.fcn == 1 and is_directory_ready(
            inroot / SITE_LONG[site_code] / "fcn" / sublong
        ):
            already_aggregated &= is_fcn_aggregated(outroot / "fcn", row)
            jobs.add("fcn")
        if row.signatures == 1 and is_directory_ready(
            inroot / SITE_LONG[site_code] / "signatures" / sublong
        ):
            already_aggregated &= is_signatures_aggregated(
                outroot / "signatures", row
            )
            jobs.add("signatures")
        if row.gift_rest == 1 and is_directory_ready(
            inroot / SITE_LONG[site_code] / "gift_rest" / sublong
        ):
            already_aggregated &= (
                outroot
                / "gift_rest"
                / f"sub-{row.subject_id}"
                / f"ses-{row.visit}"
            ).exists()
            jobs.add("gift_rest")
        if not already_aggregated:
            derivatives.update({sublong: list(jobs)})

    return derivatives


def _prep_staged_dir(outroot: Path) -> None:
    # delete broken symlinks (e.g., files created by previous run of heudiconv
    # that no longer exist)
    for target in os.walk(outroot):
        tar_dir = Path(target[0])
        for f in target[2]:
            if not (broken := tar_dir / f).exists():
                logging.warning(f"deleting broken symlink: {broken}")
                broken.unlink()
        # if the only remaining file is a nifti that is a real file, it
        # is a holdover and should also be deleted
        if (
            len(target[2]) == 1
            and str(to_del := (Path(target[0]) / target[2][0])).endswith(
                ".nii.gz"
            )
            and not to_del.is_symlink()
        ):
            logging.warning(f"deleting isolated file: {to_del}")
            to_del.unlink()

    # delete fcn directories that have multiple parquet files
    # they are created during reruns without the products being cleared
    # recent versions of the aggregator avoid copying duplicates
    # but there may be some that lingered
    for sub in (outroot / "fcn" / "connectivity").glob("sub=*"):
        for ses in list(sub.glob("ses=*")):
            # just delete the whole subject tree for simplicity
            if len(list(ses.glob("*parquet"))) > 1:
                logging.warning(f"found duplicates in {ses}, deleting")
                shutil.rmtree(ses)
                break

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


def _get_bids_tocopy(inroot: Path, outroot: Path, site_code: str) -> set[str]:
    bids_avail: pd.DataFrame = pd.read_csv(ILOG).query(
        "bids == 1 and site == @site_code"
    )[["site", "subject_id", "visit"]]
    exists: dict[str, bool] = {}
    for row in bids_avail.itertuples():
        sublong = _make_sublong(row.site, row.subject_id, row.visit)  # type: ignore
        exists[sublong] = (
            len(
                list(
                    (inroot / SITE_LONG[site_code] / "bids" / sublong).glob(
                        "*out"
                    )
                )
            )
            > 0
        ) and not (
            outroot / "bids" / f"sub-{row.subject_id}" / f"ses-{row.visit}"
        ).exists()
    return set(k for k, v in exists.items() if v)


def _synthstrip(src: Path, n_threads: int = 1) -> Path:
    with tempfile.NamedTemporaryFile(suffix=".nii.gz") as brain:
        proc = subprocess.run(
            [
                "synthstrip",
                "-i",
                src,
                "-o",
                brain.name,
                "-n",
                str(n_threads),
                "--model",
                SYNTHSTRIP_MODEL,
            ]
        )
        if proc.returncode > 0:
            msg = f"Failed to synthstrip {src}"
            raise RuntimeError(msg)
        src.unlink()
        shutil.copy2(brain.name, src)
        os.chmod(src, 0o640)
    return src


def main(
    inroot: Path,
    outroot: Path,
    max_subs: float | int = float("inf"),
    n_threads: int = 1,
) -> None:
    logging.info("tidying output directory")
    _prep_staged_dir(outroot=outroot)
    with tempfile.TemporaryDirectory() as tmpd:
        tmpdir = Path(tmpd)
        for site_code, site_long in SITE_LONG.items():
            logging.info(f"Working on participants from {site_long}")

            # first, get all new raw (bids) data
            tmp_site = tmpdir / site_long
            bidstocopy = _get_bids_tocopy(
                inroot=inroot, outroot=outroot, site_code=site_code
            )
            failed_skullstrip = set()
            for i, subsesd in enumerate(bidstocopy):
                if i >= max_subs:
                    break
                logging.info(f"Making bids symlinks for {subsesd}")
                out_job_dir = tmp_site / "bids"
                shutil.copytree(
                    inroot / site_long / "bids" / subsesd,
                    out_job_dir / subsesd,
                    copy_function=utils._symlink_if_needed,
                    ignore=IGNORE_PATTERNS,
                )
                logging.info(f"Defacing anatomicals for {subsesd}")
                for t1w in (out_job_dir / subsesd).rglob("*T1w.nii.gz"):
                    try:
                        _synthstrip(t1w, n_threads=n_threads)
                    except Exception:
                        logging.error(f"Failed to deface {t1w}")
                        failed_skullstrip.add(subsesd)

            for subsesd in failed_skullstrip:
                bidstocopy.remove(subsesd)

            if len(bidstocopy):
                logging.info("Copying bids files to destination")
                bids_wf.copy(inroot=tmp_site, outdir=outroot / "bids")

            # grab only sub/ses that do not already exist in output
            subses_tocopy = _get_deriv_tocopy(
                outroot=outroot, inroot=inroot, site_code=site_code
            )

            # then, get all available derivatives
            subses_toremove: set[str] = set()
            for i, (subsesd, jobs) in enumerate(subses_tocopy.items()):
                if i >= max_subs:
                    break
                logging.info(
                    f"Making initial symlinks for {subsesd} derivatives"
                )
                for job in jobs:
                    logging.info(f"Making links for {job}")
                    shutil.copytree(
                        inroot / site_long / job / subsesd,
                        tmp_site / job / subsesd,
                        copy_function=utils._symlink_if_needed,
                        ignore=IGNORE_PATTERNS,
                    )

                # mask all images
                logging.info(f"Attempting to deface derivatives for {subsesd}")
                try:
                    utils.deface_all_derivatives(
                        subsesdir=Path(subsesd), tmp_site=tmp_site
                    )
                except Exception as e:
                    logging.error(e)
                    logging.warning(
                        f"Unable to deface derivatives for {subsesd}, so not aggregating"
                    )
                    for d in tmp_site.glob(f"*/{subsesd}"):
                        shutil.rmtree(d)
                    subses_toremove.add(subsesd)

            for s in subses_toremove:
                del subses_tocopy[s]

            # now aggregate all new participants
            # testing for len(subses_tocopy) to handle cases where no participants
            # were copied into the ouptut directory (e.g., during testing)
            if len(subses_tocopy):
                logging.info("Storing derivatives in final location")
                cat12_wf.copy(inroot=tmp_site, outdir=outroot / "cat12")
                qsiprep_wf.copy(inroot=tmp_site, outdir=outroot)
                brainager_wf.copy(
                    inroot=tmp_site, outdir=outroot / "brainager"
                )
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
                fcn_wf.copy(inroot=tmp_site, outdir=outroot / "fcn")
                signatures_wf.copy(
                    inroot=tmp_site, outdir=outroot / "signatures"
                )
                gift_wf.copy(inroot=tmp_site, outdir=outroot / "gift_rest")
            logging.info(f"Removing temporary directory for {site_long}")
            shutil.rmtree(tmp_site)

        # finally, handle all toplevel file material
        logging.info("Adding toplevel files")
        bids_wf.make_toplevel(outdir=outroot / "bids")
        cat12_wf.make_toplevel(outdir=outroot / "cat12")
        mriqc_wf.make_toplevel(outdir=outroot / "mriqc")
        fmriprep_wf.make_toplevel(outdir=outroot / "fmriprep-anat")
        fmriprep_wf.make_toplevel(outdir=outroot / "fmriprep-cuff")
        fmriprep_wf.make_toplevel(outdir=outroot / "fmriprep-rest")
        freesurfer_wf.make_toplevel(outdir=outroot / "freesurfer")
        fslanat_wf.make_toplevel(outdir=outroot / "fslanat")

        logging.info("Finished!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("inroot", type=Path)
    parser.add_argument("outroot", type=Path)
    parser.add_argument("--max-subs", type=float, default=float("inf"))
    parser.add_argument("--n-threads", type=int, default=1)

    args = parser.parse_args()

    main(
        inroot=args.inroot,
        outroot=args.outroot,
        max_subs=args.max_subs,
        n_threads=args.n_threads,
    )
