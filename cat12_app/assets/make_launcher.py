import os
import argparse
from typing import Union

def main(
  bind_dir: Union[str, bytes, os.PathLike],
  container: str,
  batch: str,
  nifti: list,
  launchfile: Union[str, bytes, os.PathLike] = "launchfile"
  ) -> None:

  with open(launchfile, "w") as f:
    for t, t1w in enumerate(nifti):      
      f.writelines(f'singularity exec -B {bind_dir}:{bind_dir} --cleanenv  {container} /bin/cat_standalone.sh -b {batch} {t1w} > {t}.out 2> {t}.err \n')    

  return


if __name__ == '__main__':

  """
  python make_launcher.py /corral-secure/projects/A2CPS cat12.sif batch.m T1w.nii.gz second_T1w.nii.gz
  """

  parser = argparse.ArgumentParser(description='write lines of launcher script for running ')
  parser.add_argument('BIND_DIR')
  parser.add_argument('CONTAINER_IMAGE')
  parser.add_argument('BATCH')
  parser.add_argument('NIFTI', nargs="+", help="list of anatomical files to parse, separated by spaces")
  parser.add_argument('--launchfile', default="launchfile")

  args = parser.parse_args()
  main(args.BIND_DIR, args.CONTAINER_IMAGE, args.BATCH, args.NIFTI, args.launchfile)
