import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import bids_wf
import cat12_wf
import click
import fcn_wf
import fmriprep_wf
import freesurfer_wf
import fslanat_wf
import mriqc_wf
import pandas as pd
import qsiprep_wf
import signatures_wf
import utils

logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s", level=logging.INFO
)

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
)


def _make_sublong(site: str, subject_id: str, visit: str) -> str:
    return f"{site}{subject_id}{visit}"


def is_directory_ready(path: Path) -> bool:
    return (
        path.exists()
        and (len(list(path.glob("*"))) > 0)
        and (any(i.is_dir() for i in path.glob("*")))
    )


def _get_deriv_tocopy(
    outroot: Path, inroot: Path, site_code: str
) -> dict[str, list[str]]:
    ready: pd.DataFrame = (
        pd.read_csv(ILOG)
        .query("site == @site_code")
        .query(
            """fslanat in ['1', 'na'] \
            or fmriprep_anat in ['1', 'na'] \
            or fmriprep_rest in ['1', 'na'] \
            or fmriprep_cuff in ['1', 'na'] \
            or mriqc_anat in ['1', 'na'] \
            or mriqc_rest in ['1', 'na'] \
            or mriqc_cuff in ['1', 'na'] \
            or qsiprep in ['1', 'na'] \
            or cat12 in ['1', 'na'] \
            or fcn in ['1', 'na'] \
            or signatures in ['1', 'na'] \
            or qsiprep in ['1', 'na'] \
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
        # cannot rely on imaging log only, because imaging log will say that a job is
        # done even when there are no outputs
        if row.fmriprep_anat == "1" and is_directory_ready(
            inroot / SITE_LONG[site_code] / "fmriprep" / sublong / "anat"
        ):
            if not (
                outroot / "fmriprep-anat" / f"sub-{row.subject_id}" / f"ses-{row.visit}"
            ).exists():
                jobs.add("fmriprep")
        if row.fmriprep_rest == "1" and is_directory_ready(
            inroot / SITE_LONG[site_code] / "fmriprep" / sublong / "rest"
        ):
            if not (
                outroot / "fmriprep-rest" / f"sub-{row.subject_id}" / f"ses-{row.visit}"
            ).exists():
                jobs.add("fmriprep")
        if row.fmriprep_cuff == "1" and is_directory_ready(
            inroot / SITE_LONG[site_code] / "fmriprep" / sublong / "cuff"
        ):
            if not (
                outroot / "fmriprep-cuff" / f"sub-{row.subject_id}" / f"ses-{row.visit}"
            ).exists():
                jobs.add("fmriprep")
        if row.qsiprep == "1" and is_directory_ready(
            inroot / SITE_LONG[site_code] / "qsiprep" / sublong / "qsiprep"
        ):
            if not (
                outroot / "qsiprep" / f"sub-{row.subject_id}" / f"ses-{row.visit}"
            ).exists():
                jobs.add("qsiprep")
        if row.cat12 == "1" and is_directory_ready(
            inroot / SITE_LONG[site_code] / "cat12" / sublong
        ):
            if not (
                outroot
                / "cat12"
                / "report"
                / f"catreport_sub-{row.subject_id}_ses-{row.visit}_T1w.pdf"
            ).exists():
                jobs.add("cat12")
        if (
            (
                row.mriqc_anat == "1"
                and is_directory_ready(
                    inroot / SITE_LONG[site_code] / "mriqc" / sublong / "anat"
                )
            )
            or (
                row.mriqc_rest == "1"
                and is_directory_ready(
                    inroot / SITE_LONG[site_code] / "mriqc" / sublong / "rest"
                )
            )
            or (
                row.mriqc_cuff == "1"
                and is_directory_ready(
                    inroot / SITE_LONG[site_code] / "mriqc" / sublong / "cuff"
                )
            )
        ):
            # mriqc has tiny outputs, so always arrange copy
            jobs.add("mriqc")
        if row.fslanat == "1" and is_directory_ready(
            inroot / SITE_LONG[site_code] / "fslanat" / sublong
        ):
            if not (
                outroot / "fslanat" / f"sub-{row.subject_id}_ses-{row.visit}_T1w.anat"
            ).exists():
                jobs.add("fslanat")
        if row.fcn == "1" and is_directory_ready(
            inroot / SITE_LONG[site_code] / "fcn" / sublong
        ):
            if not (
                outroot
                / "fcn"
                / "connectivity"
                / f"sub={row.subject_id}"
                / f"ses={row.visit}"
            ).exists():
                jobs.add("fcn")
        if row.signatures == "1" and is_directory_ready(
            inroot / SITE_LONG[site_code] / "signatures" / sublong
        ):
            if not all(
                (
                    outroot
                    / "signatures"
                    / sig
                    / f"sub={row.subject_id}"
                    / f"ses={row.visit}"
                ).exists()
                for sig in [
                    "signature-by-part",
                    "signature-by-run",
                    "signature-by-tr",
                    "signature-labels",
                ]
            ):
                jobs.add("signatures")

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
            and target[2][0].endswith(".nii.gz")
            and not (to_del := Path(target[2][0])).is_symlink()
        ):
            logging.warning(f"deleting isolated file: {to_del}")
            to_del.unlink()

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
    )[["site", "subject_id", "visit"]]  # type: ignore
    exists: list[bool] = []
    for row in bids_avail.itertuples():
        exists.append(
            (outroot / "bids" / f"sub-{row.subject_id}" / f"ses-{row.visit}").exists()
        )
    bids_avail["exists"] = exists
    out = bids_avail.query("not exists")
    return set(f"{row.site}{row.subject_id}{row.visit}" for row in out.itertuples())


def _synthstrip(src: Path, n_threads: int = 1) -> Path:
    with tempfile.NamedTemporaryFile(suffix=".nii.gz") as brain:
        subprocess.run(
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
        src.unlink()
        shutil.copy2(brain.name, src)
        os.chmod(src, 0o640)
    return src


@click.command()
@click.argument(
    "inroot",
    type=click.Path(exists=True, file_okay=False, resolve_path=True, path_type=Path),
)
@click.argument(
    "outroot",
    type=click.Path(exists=False, file_okay=False, resolve_path=True, path_type=Path),
)
@click.option("--max-subs", type=float, default=float("inf"))
@click.option("--n-threads", type=int, default=1)
def _main(
    inroot: Path,
    outroot: Path,
    max_subs: float | int = float("inf"),
    n_threads: int = 1,
) -> None:
    logging.warning("tidying output directory")
    _prep_staged_dir(outroot=outroot)
    with tempfile.TemporaryDirectory() as tmpd:
        tmpdir = Path(tmpd)
        for site_code, site_long in SITE_LONG.items():
            logging.info(f"Working on participants from {site_long}")

            # first, get all new raw (bids) data
            tmp_site = tmpdir / site_long
            bidstocopy = _get_bids_tocopy(outroot=outroot, site_code=site_code)
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
                    _synthstrip(t1w, n_threads=n_threads)

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
                logging.info(f"Making initial symlinks for {subsesd} derivatives")
                for job in jobs:
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
                del subses_tocopy[s]

            # now aggregate all new participants
            # testing for len(subses_tocopy) to handle cases where no participants
            # were copied into the ouptut directory (e.g., during testing)
            if len(subses_tocopy):
                logging.info("Storing derivatives in final location")
                cat12_wf.copy(inroot=tmp_site, outdir=outroot / "cat12")
                qsiprep_wf.main(inroot=tmp_site, outdir=outroot / "qsiprep")
                mriqc_wf.copy(inroot=tmp_site, outdir=outroot / "mriqc")
                fmriprep_wf.copy(inroot=tmp_site, outdir=outroot / "fmriprep-anat")
                fmriprep_wf.copy(inroot=tmp_site, outdir=outroot / "fmriprep-cuff")
                fmriprep_wf.copy(inroot=tmp_site, outdir=outroot / "fmriprep-rest")
                freesurfer_wf.copy(inroot=tmp_site, outdir=outroot / "freesurfer")
                fslanat_wf.copy(inroot=tmp_site, outdir=outroot / "fslanat")
                fcn_wf.copy(inroot=tmp_site, outdir=outroot / "fcn")
                signatures_wf.copy(inroot=tmp_site, outdir=outroot / "signatures")

        # finally, handle all toplevel file material
        logging.info("Adding toplevel files")
        # NOTE: no cat12 toplevel files
        bids_wf.make_toplevel(outdir=outroot / "bids")
        mriqc_wf.make_toplevel(outdir=outroot / "mriqc")
        qsiprep_wf.make_toplevel(outdir=outroot / "qsiprep")
        fmriprep_wf.make_toplevel(outdir=outroot / "fmriprep-anat")
        fmriprep_wf.make_toplevel(outdir=outroot / "fmriprep-cuff")
        fmriprep_wf.make_toplevel(outdir=outroot / "fmriprep-rest")
        freesurfer_wf.make_toplevel(outdir=outroot / "freesurfer")
        fslanat_wf.make_toplevel(outdir=outroot / "fslanat")


if __name__ == "__main__":
    _main()  # type: ignore
