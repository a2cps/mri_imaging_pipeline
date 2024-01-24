import argparse
import asyncio
from asyncio import subprocess
from collections import abc
import contextlib
import logging
import os
import shutil
import tempfile
from pathlib import Path

from functional_connectivity.cli import functional_connectivity

logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s", level=logging.INFO
)


def _outputs_valid(root: Path) -> bool:
    valid = (
        (root / "acompcor").exists()
        and (root / "connectivity").exists()
        and (root / "connectivity-confounds").exists()
        and (root / "connectivity-cleaned").exists()
    )
    if not valid:
        logging.warning(f"Directory {root} exists but outputs not valid.")

    return valid


def main(
    fmriprep_dir: list[Path],
    output_dir: list[Path],
    n_workers: int = 1,
    stage_dir: Path | None = None,
) -> None:
    if not (uuid := os.environ.get("_tapisJobUUID")):
        msg = "Unable to get environment variable _tapisJobUUID"
        raise AssertionError(msg)
    if not (oldlog := Path("tapisjob.out")).exists():
        msg = "Unable to find expected log file: tapisjob.out"
        raise AssertionError(msg)
    if stage_dir and (not stage_dir.exists()):
        stage_dir.mkdir(parents=True)

    # use faster filesystem for workflow, which may involve parallel writes
    with tempfile.TemporaryDirectory() as tmpd_:
        tmpd = Path(tmpd_)

        # fmriprep dirs may point to broken symlinks, or folders might not exist
        # so, need to ensure that we get one output dir for each input dir
        fmriprep_subdirs = []
        output_dir_tmp = []
        for ind, outd in zip(fmriprep_dir, output_dir, strict=True):
            logging.info(f"Looking for sub dirs in {ind}")
            subdirs = list(d for d in ind.glob("sub*") if d.is_dir())
            if len(subdirs) == 0:
                logging.warning(f"No valid sub directories found within {ind}")
            for d in subdirs:
                logging.info(f"Will process files in {d}")
                if stage_dir:
                    logging.info(f"Staging {d}")
                    # need extra directory because base pattern for tasks
                    # are often the same (e.g., fmriprep/cuff/sub-travel1 and fmriprep/rest/sub-travel1)
                    # using mkdtemp for simplicity
                    staged_d = shutil.copytree(
                        d, Path(tempfile.mkdtemp(dir=stage_dir)) / d.name
                    )
                    fmriprep_subdirs.append(staged_d)
                else:
                    fmriprep_subdirs.append(d)
                output_dir_tmp.append(tmpd / outd)

        functional_connectivity._main(
            fmriprep_subdirs=fmriprep_subdirs,
            output_dirs=output_dir_tmp,
            n_workers=n_workers,
        )

        for o in set(output_dir_tmp):
            if o.exists() and _outputs_valid(o):
                logging.info(f"Copying {o} to final destination")
                shutil.copy2(oldlog, o / f"{uuid}.out")
                # dirs_exist_ok=True because we are likely gathering results
                # from multiple sources (e.g., a run of fmriprep-cuff and fmriprep-rest)
                # will end up in the same folder
                shutil.copytree(o, o.relative_to(tmpd), dirs_exist_ok=True)
            else:
                logging.warning(f"Expected {o} but that path does not exist")

    if stage_dir:
        shutil.rmtree(stage_dir)

async def _startup() -> subprocess.Process:
    proc = await asyncio.create_subprocess_exec(
        *["/opt/conda/bin/prefect", "server", "start", "--no-ui"]
    )

    # sleep to ensure server started
    await asyncio.sleep(10)

    return proc


@contextlib.contextmanager
def get_prefect() -> abc.Generator[None, None, None]:
    proc = asyncio.run(_startup())
    try:
        yield
    finally:
        proc.terminate()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--fmriprep-dir", nargs="+", type=Path, required=True)
    parser.add_argument("--output-dir", nargs="+", type=Path, required=True)
    parser.add_argument("--n-workers", type=int, default=1)
    parser.add_argument("--stage-dir", type=Path, default=None)

    args = parser.parse_args()
    with get_prefect():
        main(**vars(args))
