import re
import typing
from pathlib import Path

import polars as pl
import utils
from biomarkers import utils as bu

FSOUTPUTS = ("orig.mgz", "orig_nu.mgz", "T1.mgz")

MORPH_EFFECT_SIZE = (
    Path("/opt/tapis/morph-effect-size.tsv")
    if Path("/opt/tapis/morph-effect-size.tsv").exists()
    else Path("morph-effect-size.tsv")
)


def _get_int(line: str) -> int:
    return int(re.findall(r"\d+", line)[0])


def _get_float(line: str) -> float:
    return float(re.findall(r"\d+.\d+", line)[0])


def parse_fs_stats(
    f: Path, columns: typing.Mapping[str, type[pl.DataType]]
) -> pl.DataFrame:
    return (
        pl.read_csv(f, comment_prefix="#", has_header=False)
        .with_columns(
            pl.col("column_1")
            .str.strip_chars_start(" ")
            .str.strip_chars_end(" ")
            .str.replace_all(r"\s+", " ")
            .str.split(" ")
            .list.to_struct(fields=list(columns.keys()))
            .struct.unnest()
        )
        .drop("column_1")
        .cast(columns)  # type: ignore
    )


def parse_aparc(f: Path) -> pl.DataFrame:
    return parse_fs_stats(
        f,
        columns={
            "StructName": pl.Utf8,
            "NumVert": pl.UInt32,
            "SurfArea": pl.UInt32,
            "GrayVol": pl.UInt32,
            "ThickAvg": pl.Float64,
            "ThickStd": pl.Float64,
            "MeanCurv": pl.Float64,
            "GausCurv": pl.Float64,
            "FoldInd": pl.Int32,
            "CurvInd": pl.Float64,
        },
    )


def _parse_aseg_header(f: Path) -> pl.DataFrame:
    dfs = []
    lines = f.read_text().splitlines()
    for line in lines:
        if "Measure BrainSeg, BrainSegVol" in line:
            dfs.append(pl.DataFrame({"BrainSegVol": [_get_float(line)]}))
        elif "Measure BrainSegNotVent, BrainSegVolNotVent" in line:
            dfs.append(pl.DataFrame({"BrainSegVolNotVent": [_get_float(line)]}))
        elif "Measure BrainSegNotVentSurf, BrainSegVolNotVentSurf" in line:
            dfs.append(pl.DataFrame({"BrainSegVolNotVentSurf": [_get_float(line)]}))
        elif "Measure Cortex, CortexVol" in line:
            dfs.append(pl.DataFrame({"CortexVol": [_get_float(line)]}))
        elif "Measure SupraTentorial, SupraTentorialVol" in line:
            dfs.append(pl.DataFrame({"SupraTentorialVol": [_get_float(line)]}))
        elif "Measure SupraTentorialNotVent, SupraTentorialVolNotVent" in line:
            dfs.append(pl.DataFrame({"SupraTentorialVolNotVent": [_get_float(line)]}))
        elif "Measure EstimatedTotalIntraCranialVol, eTIV" in line:
            dfs.append(pl.DataFrame({"eTIV": [_get_float(line)]}))
        elif "Measure VentricleChoroidVol, VentricleChoroidVol" in line:
            dfs.append(pl.DataFrame({"VentricleChoroidVol": [_get_float(line)]}))
        elif "Measure lhCortex, lhCortexVol" in line:
            dfs.append(pl.DataFrame({"lhCortexVol": [_get_float(line)]}))
        elif "Measure rhCortex, rhCortexVol" in line:
            dfs.append(pl.DataFrame({"rhCortexVol": [_get_float(line)]}))
        elif "Measure lhCerebralWhiteMatter, lhCerebralWhiteMatterVol" in line:
            dfs.append(pl.DataFrame({"lhCerebralWhiteMatterVol": [_get_float(line)]}))
        elif "Measure rhCerebralWhiteMatter, rhCerebralWhiteMatterVol" in line:
            dfs.append(pl.DataFrame({"rhCerebralWhiteMatterVol": [_get_float(line)]}))
        elif "Measure CerebralWhiteMatter, CerebralWhiteMatterVol" in line:
            dfs.append(pl.DataFrame({"CerebralWhiteMatterVol": [_get_float(line)]}))
        elif "Measure SubCortGray, SubCortGrayVol" in line:
            dfs.append(pl.DataFrame({"SubCortGrayVol": [_get_float(line)]}))
        elif "Measure TotalGray, TotalGrayVol" in line:
            dfs.append(pl.DataFrame({"TotalGrayVol": [_get_float(line)]}))
        elif "Measure SupraTentorialNotVentVox, SupraTentorialVolNotVentVox" in line:
            dfs.append(
                pl.DataFrame({"SupraTentorialVolNotVentVox": [_get_float(line)]})
            )
        elif "Measure Mask, MaskVol" in line:
            dfs.append(pl.DataFrame({"MaskVol": [_get_float(line)]}))
        elif "BrainSegVol-to-eTIV, BrainSegVol-to-eTIV" in line:
            dfs.append(pl.DataFrame({"BrainSegVol-to-eTIV": [_get_float(line)]}))
        elif "MaskVol-to-eTIV" in line:
            dfs.append(pl.DataFrame({"Mask-to-eTIV": [_get_float(line)]}))
        elif "lhSurfaceHoles" in line:
            dfs.append(pl.DataFrame({"lhSurfaceHoles": [_get_int(line)]}))
        elif "rhSurfaceHoles" in line:
            dfs.append(pl.DataFrame({"rhSurfaceHoles": [_get_int(line)]}))
        elif "SurfaceHoles, SurfaceHoles" in line:
            dfs.append(pl.DataFrame({"SurfaceHoles": [_get_int(line)]}))

    return pl.concat(dfs, how="horizontal")


def _parse_aparc_header(f: Path) -> pl.DataFrame:
    dfs = []

    lines = f.read_text().splitlines()
    for line in lines:
        if "Measure Cortex, NumVert" in line:
            dfs.append(pl.DataFrame({"NumVert": [_get_int(line)]}))
        elif "Measure Cortex, WhiteSurfArea" in line:
            dfs.append(pl.DataFrame({"WhiteSurfArea": [_get_float(line)]}))
        elif "Measure Cortex, MeanThickness" in line:
            dfs.append(pl.DataFrame({"MeanThickness": [_get_float(line)]}))
    return pl.concat(dfs, how="horizontal")


def parse_all_headers(root: Path) -> pl.DataFrame:
    _aseg: list[pl.DataFrame] = []
    _aparc: list[pl.DataFrame] = []
    for subsesdir in root.glob("sub*"):
        sub = int(bu.get_sub_from_sublong(subsesdir))
        ses = bu.get_ses_from_sublong(subsesdir)
        _aseg.append(
            _parse_aseg_header(subsesdir / "stats" / "aseg.stats").with_columns(
                sub=sub, ses=pl.lit(ses)
            )
        )
        _aparc.append(
            _parse_aparc_header(subsesdir / "stats" / "lh.aparc.stats").with_columns(
                sub=sub, ses=pl.lit(ses)
            )
        )
    aseg = pl.concat(_aseg)
    aparc = pl.concat(_aparc)

    return aseg.join(aparc, on=["sub", "ses"])


def parse_aseg(f: Path) -> pl.DataFrame:
    return parse_fs_stats(
        f,
        columns={
            "Index": pl.UInt32,
            "SegId": pl.UInt32,
            "NVoxels": pl.UInt32,
            "Volume_mm3": pl.Float64,
            "StructName": pl.Utf8,
            "normMean": pl.Float64,
            "normStdDev": pl.Float64,
            "normMin": pl.Float64,
            "normMax": pl.Float64,
            "normRange": pl.Float64,
        },
    )


def parse_all_aparc(root: Path) -> pl.DataFrame:
    aparc: list[pl.DataFrame] = []
    for subsesdir in root.glob("sub*"):
        sub = int(bu.get_sub_from_sublong(subsesdir))
        ses = bu.get_ses_from_sublong(subsesdir)
        for hemi in ["lh", "rh"]:
            aparc.append(
                parse_aparc(subsesdir / "stats" / f"{hemi}.aparc.stats").with_columns(
                    sub=sub,
                    ses=pl.lit(ses),
                    hemisphere=pl.lit(hemi),
                    parc=pl.lit("aparc"),
                )
            )
            aparc.append(
                parse_aparc(
                    subsesdir / "stats" / f"{hemi}.aparc.pial.stats"
                ).with_columns(
                    sub=sub,
                    ses=pl.lit(ses),
                    hemisphere=pl.lit(hemi),
                    parc=pl.lit("aparc.pial"),
                )
            )
            aparc.append(
                parse_aparc(
                    subsesdir / "stats" / f"{hemi}.BA_exvivo.stats"
                ).with_columns(
                    sub=sub,
                    ses=pl.lit(ses),
                    hemisphere=pl.lit(hemi),
                    parc=pl.lit("BA_exvivo"),
                )
            )
            aparc.append(
                parse_aparc(
                    subsesdir / "stats" / f"{hemi}.BA_exvivo.thresh.stats"
                ).with_columns(
                    sub=sub,
                    ses=pl.lit(ses),
                    hemisphere=pl.lit(hemi),
                    parc=pl.lit("BA_exvivo.thresh"),
                )
            )
            aparc.append(
                parse_aparc(
                    subsesdir / "stats" / f"{hemi}.aparc.DKTatlas.stats"
                ).with_columns(
                    sub=sub,
                    ses=pl.lit(ses),
                    hemisphere=pl.lit(hemi),
                    parc=pl.lit("aparc.DKTatlas"),
                )
            )
            aparc.append(
                parse_aparc(
                    subsesdir / "stats" / f"{hemi}.aparc.a2009s.stats"
                ).with_columns(
                    sub=sub,
                    ses=pl.lit(ses),
                    hemisphere=pl.lit(hemi),
                    parc=pl.lit("aparc.a2009s"),
                )
            )

    return pl.concat(aparc)


def parse_all_aseg(root: Path) -> pl.DataFrame:
    aseg: list[pl.DataFrame] = []
    for subsesdir in root.glob("sub*"):
        sub = int(bu.get_sub_from_sublong(subsesdir))
        ses = bu.get_ses_from_sublong(subsesdir)
        aseg.append(
            parse_aseg(subsesdir / "stats" / "aseg.stats").with_columns(
                sub=sub, ses=pl.lit(ses), seg=pl.lit("aseg")
            )
        )
        aseg.append(
            parse_aseg(subsesdir / "stats" / "wmparc.stats").with_columns(
                sub=sub, ses=pl.lit(ses), seg=pl.lit("wmparc")
            )
        )

    return pl.concat(aseg)


def get_gm_morph(aparc: pl.DataFrame) -> pl.DataFrame:
    effect_sizes = pl.read_csv(MORPH_EFFECT_SIZE, separator="\t")
    return (
        aparc.filter(pl.col("parc") == "aparc.a2009s")
        .join(effect_sizes, on=["hemisphere", "StructName", "parc"])
        .group_by(["sub", "ses"])
        .agg(surf_area_signature_bhatt=pl.col("SurfArea").dot("effect_size"))
    )


def copy(outdir: Path, inroot: Path) -> None:
    bu.mkdir_recursive(outdir)

    for src in inroot.glob("fmriprep/*/fmriprep/sourcedata/freesurfer/sub*"):
        # folders renamed so that sessions do not collide
        utils.mergetree_overwrite(
            src,
            outdir
            / f"sub-{bu.get_sub_from_sublong(src)}_ses-{bu.get_ses_from_sublong(src)}",
        )


def make_toplevel(outdir: Path) -> None:
    bu.mkdir_recursive(outdir)
    aparc = parse_all_aparc(outdir)

    # note that we must keep index to preserve sub,ses cols
    # which end up in multindex
    get_gm_morph(aparc).write_csv(outdir / "gm_morph.tsv", separator="\t")

    aparc.write_csv(outdir / "aparc.tsv", separator="\t")
    parse_all_aseg(outdir).write_csv(outdir / "aseg.tsv", separator="\t")
    parse_all_headers(outdir).write_csv(outdir / "headers.tsv", separator="\t")
