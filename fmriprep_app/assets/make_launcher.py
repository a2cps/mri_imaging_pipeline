import pathlib
import argparse
from typing import Any, List, Optional, Literal
import shlex


def main(
    binddir: pathlib.Path,
    container: str,
    bidsdir: List[pathlib.Path],
    outdir: List[pathlib.Path],
    launchfile: pathlib.Path = pathlib.Path("launchfile"),
    nthreads: Optional[int] = None,
    mem_mb: Optional[int] = None,
    skip_bids_validation: bool = False,
    fs_subjects_dir: Optional[List[pathlib.Path]] = None,
    fs_no_reconall: bool = False,
    bids_filter_file: Optional[pathlib.Path] = None,
    anat_only: bool = False,
    cifti_output: Optional[Literal["91k", "170k"]] = None,
    fd_spike_threshold: Optional[float] = None,
    aroma_melodic_dimensionality: Optional[int] = None,
    use_aroma: bool = False,
    dummy_scans: Optional[int] = None,
    head_motion: Optional[Literal[6, 9, 12]] = None,
    ignore: Optional[List[Literal["slicetiming", "fieldmaps"]]] = None,
) -> None:
    lines = []
    for t, (bids, logdir) in enumerate(zip(bidsdir, outdir)):
        if not logdir.exists():
            logdir.mkdir(parents=True)
        args: List[Any] = [
            "singularity",
            "run",
            "-e",
            "-B",
            f"{binddir}:{binddir}",
            f"docker://{container}",
            str(bids),
            str(logdir.resolve()),
            "participant",
            "-w",
            str(logdir.resolve() / "work"),
            "--fs-license-file",
            "/opt/freesurfer_license/license.txt",
            "--notrack",
            "--write-graph",
        ]
        if mem_mb:
            args.extend(["--mem_mb", mem_mb])
        if nthreads:
            args.extend(["--n-cpus", nthreads])
        if ignore:
            if "fieldmaps" in ignore:
                args.append("--ignore fieldmaps")
            if "slicetiming" in ignore:
                args.append("--ignore slicetiming")
        if head_motion:
            args.extend(["--bold2t1w-dof", head_motion])
        if dummy_scans:
            args.extend(["--dummy-scans", dummy_scans])
        if use_aroma:
            args.append("--use-aroma")
        if aroma_melodic_dimensionality:
            args.extend(
                ["--aroma-melodic-dimensionality", str(aroma_melodic_dimensionality)]
            )
        if fd_spike_threshold:
            args.extend(["--fd-spike-threshold", str(fd_spike_threshold)])
        if cifti_output:
            args.extend(["--cifti-output", cifti_output])
        if anat_only:
            args.append("--anat-only")
        if bids_filter_file:
            args.extend(["--bids-filter-file", str(bids_filter_file)])
        if fs_no_reconall:
            args.append("--fs-no-reconall")
        if skip_bids_validation:
            args.append("--skip-bids-validation")
        if fs_subjects_dir:
            args.extend(["--fs-subjects-dir", str(fs_subjects_dir[t])])

        # Note safety risk!!! (e.g., what if logdir were "out; rm -rf /" !?)
        # https://docs.python.org/3/library/shlex.html#shlex.quote
        line = shlex.join(args) + f" > {logdir}/{t}.out 2> {logdir}/{t}.err"
        lines.append(line)

    launchfile.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--bidsdir", nargs="+", type=pathlib.Path, required=True)
    parser.add_argument("--outdir", nargs="+", type=pathlib.Path, required=True)
    parser.add_argument("--binddir", type=pathlib.Path, required=True)
    parser.add_argument("--container", required=True)
    parser.add_argument(
        "--launchfile", default=pathlib.Path("launchfile"), type=pathlib.Path
    )
    parser.add_argument("--nthreads")
    parser.add_argument("--mem-mb")
    parser.add_argument("--skip-bids-validation", action="store_true")
    parser.add_argument("--fs-subjects-dir", nargs="*", type=pathlib.Path)
    parser.add_argument("--fs-no-reconall", action="store_true")
    parser.add_argument("--bids-filter-file", type=pathlib.Path)
    parser.add_argument("--anat-only", action="store_true")
    parser.add_argument("--cifti-output", choices=["91k", "170k"])
    parser.add_argument("--fd-spike-threshold", type=float)
    parser.add_argument("--aroma-melodic-dimensionality", type=int)
    parser.add_argument("--use-aroma", action="store_true")
    parser.add_argument("--dummy-scans", type=int)
    parser.add_argument("--head-motion", type=int, choices=[6, 9, 12])
    parser.add_argument("--ignore", action="append")

    args = parser.parse_args()
    main(**vars(args))
