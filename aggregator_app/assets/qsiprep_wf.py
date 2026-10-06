from pathlib import Path

import utils
from biomarkers import utils as bu


def session_dirname(job: str, ses: str) -> str:
    # qsiprep writes the anatomicals without a session entity, so each session
    # is stored separately. a version suffix stays last, e.g.,
    # qsiprep -> qsiprep-V1, qsiprep-v4 -> qsiprep-V1-v4
    base, sep, version = job.partition("-")
    return f"{base}-{ses}{sep}{version}"


def eddyqc_dirname(job: str) -> str:
    # qsiprep -> eddyqc, qsiprep_nodenoise -> eddyqc_nodenoise,
    # qsiprep-v4 -> eddyqc-v4, qsiprep_nodenoise-v4 -> eddyqc_nodenoise-v4
    return job.replace("qsiprep", "eddyqc", 1)


def copy(outdir: Path, inroot: Path, job: str = "qsiprep") -> None:
    bu.mkdir_recursive(outdir / session_dirname(job, "V1"))
    bu.mkdir_recursive(outdir / session_dirname(job, "V3"))

    for src in inroot.glob(f"{job}/*/qsiprep/sub*"):
        # sub/ses are regex-matched against the whole path string, so trim
        # to the globbed root (a tempdir name can contain 5 digits)
        ses = bu.get_ses_from_sublong(src.relative_to(inroot))
        if src.is_file():
            utils.symlink_if_needed(
                src,
                outdir / session_dirname(job, ses) / src.name,
            )
        else:
            utils.mergetree_overwrite(src, outdir / session_dirname(job, ses) / src.name)

    for src in inroot.glob(f"{job}/*/eddyqc"):
        rel = src.relative_to(inroot)
        sub = bu.get_sub_from_sublong(rel)
        ses = bu.get_ses_from_sublong(rel)

        out_subses = outdir / eddyqc_dirname(job) / f"sub-{sub}" / f"ses-{ses}"
        bu.mkdir_recursive(out_subses)

        utils.mergetree_overwrite(src, out_subses)
