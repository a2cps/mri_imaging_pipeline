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
    format=f"%(asctime)s | %(levelname)-8s | {RANK=} | {USIZE=} | %(message)s",
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
        logging.info(f"{args=}")

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


def stage(srcs: list[pathlib.Path], dst: pathlib.Path) -> pathlib.Path:
    for rank, src in enumerate(srcs):
        if rank == RANK:
            logging.info(f"Staging files for {src=} -> {dst=}")
            shutil.copytree(
                src,
                dst,
                ignore=shutil.ignore_patterns(
                    "*sourcedata*", "*func*", "*scans.tsv", "*scans.json", "*fmrib0*"
                ),
            )
        # ensure that only one copy happens at a time
        MPI.COMM_WORLD.barrier()
    return dst


def archive(src: pathlib.Path, dsts: list[pathlib.Path], returncode: int | None):
    for rank, dst in enumerate(dsts):
        if rank == RANK:
            if returncode == 0:
                logging.info(f"Copying {src} -> {dst}")
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                logging.warning(f"{dsts[RANK]=} ended with {returncode=}")
        # ensure that only one copy happens at a time
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
            async with get_orchestration_async(
                bidsdir=tmpd_in,
                outdir=tmpd_out,
                nthreads=nthreads,
                mem_mb=mem_mb,
            ) as proc:
                await proc.wait()
                archive(tmpd_out, outdirs, proc.returncode)

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
