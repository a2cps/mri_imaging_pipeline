from pathlib import Path

import polars as pl
import statsmodels.formula.api as smf
import utils
from biomarkers.flows import dwi_biomarker1

REFERENCE = (
    ref
    if (ref := Path("/opt/tapis/hub-reference.parquet")).exists()
    else Path("hub-reference.parquet")
)


def get_coefs(d: pl.DataFrame) -> pl.DataFrame:
    fit = smf.ols("degree_right ~ degree", data=d).fit()
    return (
        d.select("sub", "ses", "task", "run")
        .unique()
        .with_columns(disruption_degree=fit.params.iloc[1])
    )


def get_hub_disruption(inroot: Path, target_density: float = 0.1) -> None:
    reference = pl.scan_parquet(REFERENCE)
    pl.scan_parquet(inroot / "connectivity").filter(
        pl.col("estimator") == "empirical",
        pl.col("atlas") == "schaefer_nrois-400_resolution-2_networks-7",
    ).drop("atlas", "estimator").with_columns(
        pl.col("source").cast(pl.UInt16)
    ).group_by("sub", "ses", "task", "run").map_groups(
        lambda d: dwi_biomarker1.threshold_proportional_bin(
            d, target_density, "connectivity"
        ),
        schema={
            "source": pl.UInt16,
            "target": pl.UInt16,
            "connectivity": pl.Boolean,
            "sub": pl.Int64,
            "ses": pl.Utf8,
            "task": pl.Utf8,
            "run": pl.Int64,
        },
    ).group_by("source", "sub", "ses", "task", "run").agg(
        degree=pl.col("connectivity").sum()
    ).join(reference, how="left", on=["source"]).with_columns(
        degree=pl.col("degree") - pl.col("degree_right")
    ).group_by("sub", "ses", "task", "run").map_groups(
        get_coefs,
        schema={
            "sub": pl.UInt16,
            "ses": pl.Utf8,
            "disruption_degree": pl.Float64,
            "task": pl.Utf8,
            "run": pl.Int64,
        },
    ).collect().write_csv(inroot / "hub_disruption.tsv", separator="\t")


def make_toplevel(outdir: Path) -> None:
    get_hub_disruption(outdir)


def copy(outdir: Path, inroot: Path) -> None:
    if not outdir.exists():
        outdir.mkdir(parents=True)

    for src in inroot.glob("fcn/*"):
        for out in ["cleaned", "confounds", "connectivity", "timeseries"]:
            utils.mergetree_overwrite(src / out, outdir / out)
