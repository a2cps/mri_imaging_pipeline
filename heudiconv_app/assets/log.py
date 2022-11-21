import argparse

from utils import print_and_post


def main(msg: str, post: bool = False) -> None:
    print_and_post(notification=msg, post=post)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("msg")
    parser.add_argument("--post", action=argparse.BooleanOptionalAction, default=False)

    args = parser.parse_args()
    main(msg=args.msg, post=args.post)
