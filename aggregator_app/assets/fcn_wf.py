from pathlib import Path

import polars as pl
import statsmodels.formula.api as smf
import utils

REFERENCE = (
    ref
    if (ref := Path("/opt/tapis/hub-reference.parquet")).exists()
    else Path("hub-reference.parquet")
)


def get_coefs(degree: pl.Series, degree_right: pl.Series) -> float:
    d = pl.DataFrame({"degree": degree, "degree_right": degree_right})
    fit = smf.ols("degree_right ~ degree", data=d).fit()
    return fit.params.iloc[1]


def get_hub_disruption(inroot: Path, target_density: float = 0.1) -> None:
    reference = pl.scan_parquet(REFERENCE)
    groups = ["sub", "ses", "task", "run"]
    pl.scan_parquet(inroot / "connectivity").filter(
        pl.col("estimator") == "empirical",
        pl.col("atlas") == "schaefer_nrois-400_resolution-2_networks-7",
    ).with_columns(pl.col("source").cast(pl.UInt16)).with_columns(
        avg=pl.col("connectivity").gt(0).mean().over(groups),
        target_quant=pl.col("connectivity").quantile(1 - target_density).over(groups),
    ).with_columns(
        value=pl.when(pl.col("avg").lt(target_density))
        .then(pl.col("connectivity") > 0)
        .otherwise(pl.col("connectivity") > pl.col("target_quant"))
    ).group_by("source", *groups).agg(degree=pl.col("value").sum()).join(
        reference, how="left", on=["source"]
    ).with_columns(degree=pl.col("degree") - pl.col("degree_right")).group_by(
        groups
    ).agg(
        disruption_degree=pl.struct("degree", "degree_right").map_batches(
            lambda x: get_coefs(
                degree=x.struct.field("degree"),
                degree_right=x.struct.field("degree_right"),
            ),
            return_dtype=pl.Float64,
            returns_scalar=True,
        )
    ).sink_csv(inroot / "hub_disruption.tsv", separator="\t")


def make_toplevel(outdir: Path) -> None:
    get_hub_disruption(outdir)


def copy(outdir: Path, inroot: Path) -> None:
    if not outdir.exists():
        outdir.mkdir(parents=True)

    for src in inroot.glob("fcn/*"):
        for out in ["cleaned", "confounds", "connectivity", "timeseries"]:
            utils.mergetree_overwrite(src / out, outdir / out)
