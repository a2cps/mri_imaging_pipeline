import argparse

from nilearn import image


def main(img: str) -> None:
    # keep as str because load_img can't handle Path
    full = image.load_img(img)
    assert len(full.shape) == 4
    final = image.index_img(full, full.shape[-1] - 1)
    final.to_filename(img)


if __name__ == "__main__":

    """
    python index_img T1w.nii.gz
    """

    parser = argparse.ArgumentParser()
    parser.add_argument("img")
    args = parser.parse_args()
    main(img=args.img)
