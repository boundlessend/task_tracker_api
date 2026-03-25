import argparse
import subprocess
import sys


def run(*args: str) -> None:
    subprocess.check_call(list(args))


def install() -> None:
    run(sys.executable, "-m", "pip", "install", "--upgrade", "pip")
    run(sys.executable, "-m", "pip", "install", "-r", "requirements-dev.txt")


def start() -> None:
    run(sys.executable, "-m", "app")


def test() -> None:
    run(sys.executable, "-m", "pytest")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["install", "run", "test"])
    args = parser.parse_args()

    if args.command == "install":
        install()
    elif args.command == "run":
        start()
    elif args.command == "test":
        test()


if __name__ == "__main__":
    main()
