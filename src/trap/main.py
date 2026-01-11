"""Main entrypoint for Trap."""

import argparse
from pathlib import Path


def main() -> None:
    """Run the application."""
    parser = argparse.ArgumentParser(description="Trap")
    parser.add_argument("--input", "-i", type=Path, help="Input file path")
    args = parser.parse_args()

    if args.input:
        if not args.input.exists():
            print(f"Error: File not found: {args.input}")
            return
        content = args.input.read_text()
        print(f"Read {len(content)} characters from {args.input}")
        print(content)
    else:
        print("Hello from Trap!")


if __name__ == "__main__":
    main()
