import argparse
from pathlib import Path
import pandas as pd


def main(output_df: Path, in_df: Path, site: str) -> None:
    sub_df = pd.read_csv(in_df, sep='\t', dtype={'age': pd.Int16Dtype(), 'sex': str, 'group': str})
    sub_df['site'] = site

    if output_df.exists():
      participants_df = (
        pd.read_csv(output_df, sep='\t', dtype={'age': pd.Int16Dtype(), 'sex': str, 'group': str})
        .merge(sub_df, how="outer"))
    else:
      participants_df = sub_df

    participants_df.to_csv(output_df, sep="\t", index=False, na_rep="n/a")

    return


if __name__ == '__main__':

  parser = argparse.ArgumentParser(description='')

  parser.add_argument(
    'output_df', 
    help="participants.tsv file that needs updating",
    type=Path)
  parser.add_argument(
    'sub_df', 
    type=Path,
    help="participants.tsv file of new participant being added")
  parser.add_argument(
    'site', 
    help="site at which the new participant was scanned", 
    type=str,
    choices=["NS","UC","UI","UM","WS"])

  args = parser.parse_args()
  main(args.output_df, args.sub_df, args.site)
