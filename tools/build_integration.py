from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parent.parent

SOURCE = ROOT / "windhager_tools"

TARGET = (
    ROOT
    / "custom_components"
    / "windhager_infowin"
    / "vendor"
    / "windhager_tools"
)


def fix_imports():

    for file in TARGET.glob("*.py"):

        text = file.read_text(encoding="utf-8")

        text = text.replace(
            "from windhager_tools.",
            "from .",
        )

        text = text.replace(
            "import windhager_tools.",
            "import .",
        )

        file.write_text(
            text,
            encoding="utf-8",
        )


def main():

    if TARGET.exists():

        shutil.rmtree(TARGET)

    shutil.copytree(
        SOURCE,
        TARGET,
    )

    fix_imports()

    print("Bibliothek kopiert.")
    print("Imports angepasst.")
    print(TARGET)


if __name__ == "__main__":

    main()