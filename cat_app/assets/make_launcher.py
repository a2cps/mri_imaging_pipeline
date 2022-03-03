import os
import argparse
from typing import Union, Optional

def main(
  bind_dir: Union[str, bytes, os.PathLike],
  container: str,
  batch: str,
  nifti: list,
  a1: Optional[str] = None,
  outdir: list = [],
  launchfile: Union[str, bytes, os.PathLike] = "launchfile"
  ) -> None:

  if not len(outdir) == len(nifti):
    outdir = [os.getcwd()] * len(nifti)
  with open(launchfile, "w") as f:
    for t, (t1w, logdir) in enumerate(zip(nifti, outdir)): 
      cmd = f'singularity exec -B {bind_dir}:{bind_dir} --cleanenv  {container} /bin/cat_standalone.sh -b {batch}'
      log = f"> {logdir}/{t}.out 2> {logdir}/{t}.err \n"
      if a1 == None or a1 == "":
        f.writelines(f'{cmd} -a1 8 {t1w} {log}')
      else:
        f.writelines(f'{cmd} -a1 {a1} {t1w} {log}')


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
  parser.add_argument('--a1', default=None)
  parser.add_argument('--outdir', nargs="+", default=None)

  args = parser.parse_args()
  main(
    bind_dir=args.BIND_DIR, 
    container=args.CONTAINER_IMAGE, 
    batch=args.BATCH, 
    nifti=args.NIFTI, 
    a1=args.a1,
    outdir=args.outdir, 
    launchfile=args.launchfile)
