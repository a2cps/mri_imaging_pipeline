import argparse
import asyncio
import contextlib
import logging
import os
import pathlib
import shutil
import subprocess
import tempfile
import typing
import time

from mpi4py import MPI

# locations that logs will be written to if a failure was detected
# they'll match FAILURE_LOG_DST / outdir.stem
FAILURE_LOG_DST = pathlib.Path(os.environ.get("FAILURE_LOG_DST", "logs"))

# determined by Dockerfile
EDDY_PARAMS = os.environ.get("EDDY_PARAMS")
FS_LICENSE = os.environ.get("FS_LICENSE")

# used to ensure that archive proceeds even when one
# participant is stuck
SLURM_JOB_END_TIME = float(
    os.environ.get("SLURM_JOB_END_TIME", "1893474000")
)  # datetime(2030, 1, 1).timestamp()

# number of seconds before SLURM_JOB_END_TIME to cancel qsiprep
MIN_ARCHIVE_DURATION = int(os.environ.get("MIN_ARCHIVE_DURATION", 1800))

RANK = MPI.COMM_WORLD.Get_rank()
USIZE = MPI.COMM_WORLD.Get_size()

logging.basicConfig(
    format=f"%(asctime)s | %(levelname)-8s | {RANK=} | {USIZE=} | %(message)s",
    level=logging.INFO,
)


def mkdir_recursive(p: pathlib.Path, mode: int = 0o770) -> None:
    for parent in reversed(p.parents):
        if not parent.exists():
            parent.mkdir(mode=mode)
    p.mkdir(mode=mode)


def _get_qsiprep_wait_time() -> float:
    return SLURM_JOB_END_TIME - MIN_ARCHIVE_DURATION - time.time()


@contextlib.asynccontextmanager
async def manage_qsiprep(
    bidsdir: pathlib.Path,
    outdir: pathlib.Path,
    workdir: pathlib.Path,
    nthreads: int | None = None,
    mem_mb: int | None = None,
) -> typing.AsyncIterator[asyncio.subprocess.Process]:
    args = [
        "qsiprep",
        "--fs-license-file",
        FS_LICENSE,
        "--output-resolution",
        "1.7",
        "--hmc_model",
        "eddy",
        "--eddy-config",
        EDDY_PARAMS,
        "--unringing-method",
        "mrdegibbs",
        "--denoise-method",
        "patch2self",
        "--notrack",
        "--skip-bids-validation",
        "--work-dir",
        str(workdir),
    ]
    extra_args = []
    if nthreads:
        extra_args.extend(["--nthreads", nthreads])
    if mem_mb:
        extra_args.extend(["--mem_mb", mem_mb])
    extra_args.extend([str(bidsdir), str(outdir), "participant"])
    args.extend(extra_args)
    logging.info(f"{args=}")

    with open(outdir / f"qsiprep-{RANK}.log", mode="w") as stdout:
        procs = await asyncio.create_subprocess_exec(
            *args, stderr=subprocess.STDOUT, stdout=stdout
        )
        try:
            yield procs
        finally:
            if procs.returncode is None:
                procs.terminate()


@contextlib.asynccontextmanager
async def manage_eddyqc(
    bidsdir: pathlib.Path, workdir: pathlib.Path, outdir: pathlib.Path
) -> typing.AsyncIterator[asyncio.subprocess.Process]:
    qsiprep_wf = workdir / "qsiprep_wf"
    dwi_preproc_ses = None
    for d in qsiprep_wf.glob("single_subject_*_wf/dwi_preproc_ses_*_wf"):
        dwi_preproc_ses = d
        break
    if dwi_preproc_ses is None:
        logging.warning("Unable to find qsiprep_wf! eddyqc will fail")
        # Set this to an arbitrary value so that we can build paths for the subprocess
        dwi_preproc_ses = qsiprep_wf
    bvals = None
    for bv in bidsdir.glob("sub*/ses*/dwi/*bval"):
        bvals = bv
        break
    if bvals is None:
        logging.warning("Unable to find bvals in bidsdir! eddyqc will fail")
        # Set this to an arbitrary value so that we can build paths for the subprocess
        bvals = bidsdir
    hmc_sdc_wf = dwi_preproc_ses / "hmc_sdc_wf"
    basename = hmc_sdc_wf / "eddy" / "eddy_corrected"
    idx = hmc_sdc_wf / "gather_inputs" / "eddy_index.txt"
    par = hmc_sdc_wf / "gather_inputs" / "eddy_acqp.txt"
    mask = (
        hmc_sdc_wf
        / "pre_eddy_b0_ref_wf"
        / "synthstrip_wf"
        / "mask_to_original_grid"
        / "topup_imain_corrected_avg_trans_mask_trans.nii.gz"
    )
    fieldmap = hmc_sdc_wf / "topup" / "fieldmap_HZ.nii.gz"
    args = [
        "eddy_quad",
        basename,
        "-v",
        "-idx",
        idx,
        "-par",
        par,
        "-m",
        mask,
        "-b",
        bvals,
        "-f",
        fieldmap,
        "-o",
        outdir / "eddyqc",
    ]
    logging.info(f"{args=}")

    with open(outdir / f"eddy_quad-{RANK}.log", mode="w") as stdout:
        procs = await asyncio.create_subprocess_exec(
            *[str(arg) for arg in args],
            stderr=subprocess.STDOUT,
            stdout=stdout,
        )
        try:
            yield procs
        finally:
            if procs.returncode is None:
                procs.terminate()


def _copy_tapis_files(outdir: pathlib.Path) -> None:
    # tapis logs tend to be in the form of [jobid].{err,out}
    # this copies them to a destination folder
    for stderr in pathlib.Path.cwd().glob("*.err"):
        shutil.copyfile(stderr, outdir / stderr.name)
    for stdout in pathlib.Path.cwd().glob("*.out"):
        shutil.copyfile(stdout, outdir / stdout.name)


def copy_tapis_logs_to_out(outdirs: list[pathlib.Path]) -> None:
    for rank, outdir in enumerate(outdirs):
        if rank == RANK and outdir.exists():
            _copy_tapis_files(outdir=outdir)
        # ensure that only one copy happens at a time
        MPI.COMM_WORLD.barrier()


def stage(srcs: list[pathlib.Path], dst: pathlib.Path) -> pathlib.Path:
    for rank, src in enumerate(srcs):
        if rank == RANK:
            logging.info(f"Staging files for {src=} -> {dst=}")
            shutil.copytree(
                src,
                dst,
                ignore=shutil.ignore_patterns(
                    "*sourcedata*",
                    "*func*",
                    "*scans.tsv",
                    "*scans.json",
                    "*fmrib0*",
                ),
                dirs_exist_ok=True,
            )
        # ensure that only one copy happens at a time
        MPI.COMM_WORLD.barrier()
    return dst


def archive(
    src: pathlib.Path, dsts: list[pathlib.Path], returncode: int | None
) -> None:
    for rank, dst in enumerate(dsts):
        try:
            if rank == RANK:
                if returncode == 0:
                    logging.info(f"Copying {src} -> {dst}")
                    if not dst.exists():
                        mkdir_recursive(dst, mode=0o770)
                    shutil.copytree(
                        src,
                        dst,
                        dirs_exist_ok=True,
                        copy_function=shutil.copyfile,
                    )
                else:
                    # in case of failures, it's helpful to keep logs around
                    log_dst = FAILURE_LOG_DST / dst.stem
                    logging.warning(
                        f"Failure detected for {dsts[RANK]=}. Copying logs to {log_dst}"
                    )
                    if not log_dst.exists():
                        mkdir_recursive(log_dst, mode=0o770)
                    for log in src.glob("*log"):
                        shutil.copyfile(log, log_dst / log.name)
                    _copy_tapis_files(log_dst)
            # ensure that only one copy happens at a time
        except Exception as e:
            logging.error(f"Failed to archive {dsts[RANK]=}: {e}")
        finally:
            MPI.COMM_WORLD.barrier()


async def main(
    bidsdirs: list[pathlib.Path],
    outdirs: list[pathlib.Path],
    nthreads: int | None = None,
    mem_mb: int | None = None,
) -> None:
    with tempfile.TemporaryDirectory() as _tmpd_in:
        tmpd_in = stage(bidsdirs, pathlib.Path(_tmpd_in))
        with tempfile.TemporaryDirectory() as _tmpd_out:
            tmpd_out = pathlib.Path(_tmpd_out)
            with tempfile.TemporaryDirectory() as _tmpd_work:
                tmpd_work = pathlib.Path(_tmpd_work)
                async with manage_qsiprep(
                    bidsdir=tmpd_in,
                    outdir=tmpd_out,
                    workdir=tmpd_work,
                    nthreads=nthreads,
                    mem_mb=mem_mb,
                ) as qsiprep_proc:
                    try:
                        # qsiprep could get stuck for one process, which would prevent other tasks
                        # from archiving outputs. This forces an error if things have been
                        # going for too long
                        await asyncio.wait_for(
                            qsiprep_proc.wait(),
                            timeout=_get_qsiprep_wait_time(),
                        )
                    except TimeoutError:
                        logging.warning("qsiprep timed out")
                    # if qsiprep failed, likely that eddyqc will fail too.
                    # but it's not so bad to run (will fail quickly)
                    async with manage_eddyqc(
                        bidsdir=tmpd_in, workdir=tmpd_work, outdir=tmpd_out
                    ) as eddyqc_proc:
                        await eddyqc_proc.wait()
                archive(tmpd_out, outdirs, qsiprep_proc.returncode)

    copy_tapis_logs_to_out(outdirs)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--bidsdir", nargs="+", type=pathlib.Path, required=True
    )
    parser.add_argument(
        "--outdir", nargs="+", type=pathlib.Path, required=True
    )
    parser.add_argument("--nthreads", default=None)
    parser.add_argument("--mem-mb", default=None)

    args = parser.parse_args()

    if not (n_bids := len(args.bidsdir)) == USIZE:
        msg = (
            f"Length of bidsdir must equal usize but found {n_bids=}, {USIZE=}"
        )
        raise AssertionError(msg)

    if not (n_out := len(args.outdir)) == USIZE:
        msg = f"Length of outdir must equal usize but found {n_out=}, {USIZE=}"
        raise AssertionError(msg)

    if not len(args.outdir) == len(set(args.outdir)):
        msg = "Output directories must be unique"
        raise AssertionError(msg)

    asyncio.run(
        main(
            bidsdirs=args.bidsdir,
            outdirs=args.outdir,
            nthreads=args.nthreads,
            mem_mb=args.mem_mb,
        )
    )
