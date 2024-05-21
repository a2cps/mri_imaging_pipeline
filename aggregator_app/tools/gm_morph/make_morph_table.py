import pandas as pd


"""
downloaded as supplementary material of

Bhatt, R. R., Haddad, E., Zhu, A. H., Thompson, P. M., Gupta, A., Mayer, E. A., & 
Jahanshad, N. (2024). Mapping brain structure variability in chronic pain: The 
role of widespreadness and pain type and its mediating relationship with 
suicide attempt. Biological psychiatry, 95(5), 473-481.
"""


d = pd.read_excel(
    "1-s2.0-S0006322323014592-mmc1.xlsx",
    sheet_name="Chronic Pain",
    skiprows=1,
    skipfooter=175,
    usecols=["Brain Region", "Cohen's D"],
).rename(columns={"Brain Region": "StructName", "Cohen's D": "effect_size"})
d["StructName"] = d["StructName"].str.replace(".", "-")
d["StructName"] = d["StructName"].str.replace("_area", "")
d["StructName"] = d["StructName"].str.replace("_and_", "&")
d["hemisphere"] = d["StructName"].str.extract(r"^([rl]h)(?=_)")
d["StructName"] = d["StructName"].str.replace("rh_", "")
d["StructName"] = d["StructName"].str.replace("lh_", "")
d["parc"] = "aparc.a2009s"

assert d.shape[0] == 148

d.to_csv("../../assets/morp-effect-size.tsv", sep="\t", index=False)

aparc = pd.read_csv("../assets/aparc.tsv", sep="\t")
effect_sizes = d


def f(x):
    d = {}
    d["gm_thickness_signature_bhatt"] = x["ThickAvg"] @ x["effect_size"]
    return pd.Series(d, index=["gm_thickness_signature_bhatt"])


aparc.query("parc == 'aparc.a2009s'").merge(
    effect_sizes, on=["hemisphere", "StructName", "parc"]
).groupby(["sub", "ses"]).apply(f, include_groups=False).to_csv(
    "test.tsv", sep="\t"
)
