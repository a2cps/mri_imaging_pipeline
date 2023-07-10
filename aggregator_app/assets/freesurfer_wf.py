import shutil
from pathlib import Path

import utils
import pandas as pd

import re

FSOUTPUTS = ("orig.mgz", "orig_nu.mgz", "T1.mgz")


def _get_int(line: str) -> int:
    return int(re.findall(r"\d+", line)[0])


def _get_float(line: str) -> float:
    return float(re.findall(r"\d+.\d+", line)[0])


def parse_aparc(f: Path) -> pd.DataFrame:
    d = pd.read_csv(
        f,
        delim_whitespace=True,
        comment="#",
        names=[
            "StructName",
            "NumVert",
            "SurfArea",
            "GrayVol",
            "ThickAvg",
            "ThickStd",
            "MeanCurv",
            "GausCurv",
            "FoldInd",
            "CurvInd",
        ],
    )
    return d


def _parse_aseg_header(f: Path) -> pd.DataFrame:
    dfs = []
    lines = f.read_text().splitlines()
    for line in lines:
        if "Measure BrainSeg, BrainSegVol" in line:
            dfs.append(pd.DataFrame({"BrainSegVol": [_get_float(line)]}))
        elif "Measure BrainSegNotVent, BrainSegVolNotVent" in line:
            dfs.append(pd.DataFrame({"BrainSegVolNotVent": [_get_float(line)]}))
        elif "Measure BrainSegNotVentSurf, BrainSegVolNotVentSurf" in line:
            dfs.append(
                pd.DataFrame({"BrainSegVolNotVentSurf": [_get_float(line)]})
            )
        elif "Measure Cortex, CortexVol" in line:
            dfs.append(pd.DataFrame({"CortexVol": [_get_float(line)]}))
        elif "Measure SupraTentorial, SupraTentorialVol" in line:
            dfs.append(pd.DataFrame({"SupraTentorialVol": [_get_float(line)]}))
        elif "Measure SupraTentorialNotVent, SupraTentorialVolNotVent" in line:
            dfs.append(
                pd.DataFrame({"SupraTentorialVolNotVent": [_get_float(line)]})
            )
        elif "Measure EstimatedTotalIntraCranialVol, eTIV" in line:
            dfs.append(pd.DataFrame({"eTIV": [_get_float(line)]}))
        elif "Measure VentricleChoroidVol, VentricleChoroidVol" in line:
            dfs.append(
                pd.DataFrame({"VentricleChoroidVol": [_get_float(line)]})
            )
        elif "Measure lhCortex, lhCortexVol" in line:
            dfs.append(pd.DataFrame({"lhCortexVol": [_get_float(line)]}))
        elif "Measure rhCortex, rhCortexVol" in line:
            dfs.append(pd.DataFrame({"rhCortexVol": [_get_float(line)]}))
        elif "Measure lhCerebralWhiteMatter, lhCerebralWhiteMatterVol" in line:
            dfs.append(
                pd.DataFrame({"lhCerebralWhiteMatterVol": [_get_float(line)]})
            )
        elif "Measure rhCerebralWhiteMatter, rhCerebralWhiteMatterVol" in line:
            dfs.append(
                pd.DataFrame({"rhCerebralWhiteMatterVol": [_get_float(line)]})
            )
        elif "Measure CerebralWhiteMatter, CerebralWhiteMatterVol" in line:
            dfs.append(
                pd.DataFrame({"CerebralWhiteMatterVol": [_get_float(line)]})
            )
        elif "Measure SubCortGray, SubCortGrayVol" in line:
            dfs.append(pd.DataFrame({"SubCortGrayVol": [_get_float(line)]}))
        elif "Measure TotalGray, TotalGrayVol" in line:
            dfs.append(pd.DataFrame({"TotalGrayVol": [_get_float(line)]}))
        elif (
            "Measure SupraTentorialNotVentVox, SupraTentorialVolNotVentVox"
            in line
        ):
            dfs.append(
                pd.DataFrame(
                    {"SupraTentorialVolNotVentVox": [_get_float(line)]}
                )
            )
        elif "Measure Mask, MaskVol" in line:
            dfs.append(pd.DataFrame({"MaskVol": [_get_float(line)]}))
        elif "BrainSegVol-to-eTIV, BrainSegVol-to-eTIV" in line:
            dfs.append(
                pd.DataFrame({"BrainSegVol-to-eTIV": [_get_float(line)]})
            )
        elif "MaskVol-to-eTIV" in line:
            dfs.append(pd.DataFrame({"Mask-to-eTIV": [_get_float(line)]}))
        elif "lhSurfaceHoles" in line:
            dfs.append(pd.DataFrame({"lhSurfaceHoles": [_get_int(line)]}))
        elif "rhSurfaceHoles" in line:
            dfs.append(pd.DataFrame({"rhSurfaceHoles": [_get_int(line)]}))
        elif "SurfaceHoles, SurfaceHoles" in line:
            dfs.append(pd.DataFrame({"SurfaceHoles": [_get_int(line)]}))

    return pd.concat(dfs, axis=1).reset_index(drop=True)


def _parse_aparc_header(f: Path) -> pd.DataFrame:
    dfs = []

    lines = f.read_text().splitlines()
    for line in lines:
        if "Measure Cortex, NumVert" in line:
            dfs.append(pd.DataFrame({"NumVert": [_get_int(line)]}))
        elif "Measure Cortex, WhiteSurfArea" in line:
            dfs.append(pd.DataFrame({"WhiteSurfArea": [_get_float(line)]}))
        elif "Measure Cortex, MeanThickness" in line:
            dfs.append(pd.DataFrame({"MeanThickness": [_get_float(line)]}))
    return pd.concat(dfs, axis=1).reset_index(drop=True)


def parse_all_headers(root: Path) -> pd.DataFrame:
    _aseg = []
    _aparc = []
    for subsesdir in root.glob("sub*"):
        sub = utils._get_sub(subsesdir)
        ses = utils._get_ses(subsesdir)
        _aseg.append(
            _parse_aseg_header(subsesdir / "stats" / "aseg.stats").assign(
                sub=sub, ses=ses
            )
        )
        _aparc.append(
            _parse_aparc_header(subsesdir / "stats" / "lh.aparc.stats").assign(
                sub=sub, ses=ses
            )
        )
    aseg = pd.concat(_aseg).reset_index(drop=True)
    aparc = pd.concat(_aparc).reset_index(drop=True)

    return pd.merge(aseg, aparc, on=["sub", "ses"]).reset_index(drop=True)


def parse_aseg(f: Path) -> pd.DataFrame:
    d = pd.read_csv(
        f,
        delim_whitespace=True,
        comment="#",
        names=[
            "Index",
            "SegId",
            "NVoxels",
            "Volume_mm3",
            "StructName",
            "normMean",
            "normStdDev",
            "normMin",
            "normMax",
            "normRange",
        ],
    )
    return d


def parse_all_aparc(root: Path) -> pd.DataFrame:
    aparc = []
    for subsesdir in root.glob("sub*"):
        sub = utils._get_sub(subsesdir)
        ses = utils._get_ses(subsesdir)
        for hemi in ["lh", "rh"]:
            aparc.append(
                parse_aparc(subsesdir / "stats" / f"{hemi}.aparc.stats").assign(
                    sub=sub, ses=ses, hemisphere=hemi, parc="aparc"
                )
            )
            aparc.append(
                parse_aparc(
                    subsesdir / "stats" / f"{hemi}.aparc.pial.stats"
                ).assign(sub=sub, ses=ses, hemisphere=hemi, parc="aparc.pial")
            )
            aparc.append(
                parse_aparc(
                    subsesdir / "stats" / f"{hemi}.BA_exvivo.stats"
                ).assign(sub=sub, ses=ses, hemisphere=hemi, parc="BA_exvivo")
            )
            aparc.append(
                parse_aparc(
                    subsesdir / "stats" / f"{hemi}.BA_exvivo.thresh.stats"
                ).assign(
                    sub=sub, ses=ses, hemisphere=hemi, parc="BA_exvivo.thresh"
                )
            )
            aparc.append(
                parse_aparc(
                    subsesdir / "stats" / f"{hemi}.aparc.DKTatlas.stats"
                ).assign(
                    sub=sub, ses=ses, hemisphere=hemi, parc="aparc.DKTatlas"
                )
            )
            aparc.append(
                parse_aparc(
                    subsesdir / "stats" / f"{hemi}.aparc.a2009s.stats"
                ).assign(sub=sub, ses=ses, hemisphere=hemi, parc="aparc.a2009s")
            )

    return pd.concat(aparc, ignore_index=True)


def parse_all_aseg(root: Path) -> pd.DataFrame:
    aseg = []
    for subsesdir in root.glob("sub*"):
        sub = utils._get_sub(subsesdir)
        ses = utils._get_ses(subsesdir)
        aseg.append(
            parse_aseg(subsesdir / "stats" / "aseg.stats").assign(
                sub=sub, ses=ses, seg="aseg"
            )
        )
        aseg.append(
            parse_aseg(subsesdir / "stats" / "wmparc.stats").assign(
                sub=sub, ses=ses, seg="wmparc"
            )
        )

    return pd.concat(aseg, ignore_index=True)


def main(outdir: Path, inroot: Path) -> None:
    if not outdir.exists():
        outdir.mkdir(parents=True)

    for src in inroot.glob("fmriprep/*/anat/freesurfer/sub*"):
        # folders renamed so that sessions do not collide
        shutil.copytree(
            src,
            outdir / f"sub-{utils._get_sub(src)}_ses-{utils._get_ses(src)}",
            copy_function=utils._copy_if_needed,
        )

    parse_all_aparc(outdir).to_csv(outdir / "aparc.tsv", index=False, sep="\t")
    parse_all_aseg(outdir).to_csv(outdir / "aseg.tsv", index=False, sep="\t")
    parse_all_headers(outdir).to_csv(
        outdir / "headers.tsv", index=False, sep="\t"
    )
