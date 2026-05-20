import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lk_constitution.parser import Parser


def main() -> None:
    parser = Parser()
    constitution = parser.parse()
    folder = parser.write(constitution)
    print(f"Written to {folder}")


if __name__ == "__main__":
    main()
