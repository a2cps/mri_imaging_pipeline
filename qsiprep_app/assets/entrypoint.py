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

from mpi4py import MPI

# determined by Dockerfile
EDDY_PARAMS = os.environ.get("EDDY_PARAMS")
FS_LICENSE = os.environ.get("FS_LICENSE")

RANK = MPI.COMM_WORLD.Get_rank()
USIZE = MPI.COMM_WORLD.Get_size()
logging.basicConfig(
    format=f"%(asctime)s %(levelname)-8s {RANK=}/{USIZE} %(message)s",
    level=logging.INFO,
)


@contextlib.asynccontextmanager
async def get_orchestration_async(
    bidsdir: pathlib.Path,
    outdir: pathlib.Path,
    nthreads: int | None = None,
    mem_mb: int | None = None,
) -> typing.AsyncIterator[asyncio.subprocess.Process]:
    with tempfile.TemporaryDirectory() as workd:
        logging.info(f"qsiprep work-dir set to {workd}")
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
            "--work-dir",
            workd,
        ]
        extra_args = []
        if nthreads:
            extra_args.extend(["--nthreads", nthreads])
        if mem_mb:
            extra_args.extend(["--mem_mb", mem_mb])
        extra_args.extend([str(bidsdir), str(outdir), "participant"])
        args.extend(extra_args)

        with open(outdir / f"rank-{RANK}.log", mode="w") as stdout:
            procs = await asyncio.create_subprocess_exec(
                *args,
                stderr=subprocess.STDOUT,
                stdout=stdout,
            )
            try:
                yield procs
            finally:
                if procs.returncode is None:
                    procs.terminate()


def copy_tapis_logs_to_out(outdirs: list[pathlib.Path]) -> None:
    for outdir in outdirs:
        if outdir.exists():
            # tapis log files to dsts
            for stderr in pathlib.Path.cwd().glob("*.err"):
                shutil.copy2(stderr, outdir)
            for stdout in pathlib.Path.cwd().glob("*.out"):
                shutil.copy2(stdout, outdir)


async def main(
    bidsdirs: list[pathlib.Path],
    outdirs: list[pathlib.Path],
    nthreads: int | None = None,
    mem_mb: int | None = None,
) -> None:
    with tempfile.TemporaryDirectory() as _tmpd_out:
        tmpd_out = pathlib.Path(_tmpd_out)
        async with get_orchestration_async(
            bidsdir=bidsdirs[RANK], outdir=tmpd_out, nthreads=nthreads, mem_mb=mem_mb
        ) as proc:
            await proc.wait()
            if proc.returncode == 0:
                logging.info(f"Copying {tmpd_out} -> {outdirs[RANK]}")
                shutil.copytree(tmpd_out, outdirs[RANK])
            else:
                logging.warning(f"{bidsdirs[RANK]} ended with {proc.returncode=}")

    copy_tapis_logs_to_out(outdirs)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--bidsdir", nargs="+", type=pathlib.Path, required=True)
    parser.add_argument("--outdir", nargs="+", type=pathlib.Path, required=True)
    parser.add_argument("--nthreads", default=None)
    parser.add_argument("--mem-mb", default=None)

    args = parser.parse_args()

    if not (n_bids := len(args.bidsdir)) == USIZE:
        msg = f"Length of bidsdir must equal usize but found {n_bids=}, {USIZE=}"
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
