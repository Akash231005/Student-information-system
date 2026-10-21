from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "SIS-System-Design-Submission.zip"
EXCLUDED_DIRS = {
    ".git", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache",
    "node_modules", ".mypy_cache",
}
ROOT_FILES = ["README.md", ".gitignore"]
ROOT_DIRS = [".github", "research", "design", "experiments", "deliverables", "scripts", "testing"]


def should_include(path: Path) -> bool:
    relative = path.relative_to(ROOT)
    if path == OUTPUT or any(part in EXCLUDED_DIRS for part in relative.parts):
        return False
    if path.name in {".env", "sis_dev.db"} or path.suffix in {".pyc", ".log"}:
        return False
    if relative.parts[0] == "references":
        return False
    if relative.parts[0] == "sis-app":
        if len(relative.parts) > 1 and relative.parts[1] == "deliverables":
            return False
        if "results" in relative.parts:
            if path.name == "README.md":
                return True
            return path.name.startswith("verified-")
    return path.is_file()


def collect_files() -> list[Path]:
    selected = [ROOT / name for name in ROOT_FILES if (ROOT / name).is_file()]
    for dirname in ROOT_DIRS:
        directory = ROOT / dirname
        if directory.exists():
            selected.extend(path for path in directory.rglob("*") if path.is_file())
    app = ROOT / "sis-app"
    if app.exists():
        selected.extend(path for path in app.rglob("*") if path.is_file())
    return sorted({path for path in selected if should_include(path)})


def main() -> None:
    files = collect_files()
    with ZipFile(OUTPUT, "w", compression=ZIP_DEFLATED, compresslevel=8) as archive:
        for path in files:
            archive.write(path, path.relative_to(ROOT))
    print(f"Created {OUTPUT}")
    print(f"Files included: {len(files)}")
    print(f"Archive size: {OUTPUT.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
