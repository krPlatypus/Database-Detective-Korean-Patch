"""공식 macOS 로더·v1.0.1 그림/폰트/음원과 현재 번역·소스로 macOS 배포판을 만든다.

python3 tools/make_macos_release.py [--game-dir GAME] [--dotnet DOTNET]
게임 파일은 참조만 하며 압축에 포함하지 않는다. 게임 폴더에 설치하지 않는다.
텍스트는 설치된 게임 원문과 translation/을 대조하여 다시 빌드한다 (UnityPy 필요).
"""
import argparse
import hashlib
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parent.parent
RELEASE = ROOT / "release"
DEFAULT_GAME = Path.home() / "Library/Application Support/Steam/steamapps/common/Database Detective"
DOWNLOADS = (
    ("BepInEx_macos_universal_5.4.23.6.zip",
     "https://github.com/BepInEx/BepInEx/releases/download/v5.4.23.6/",
     "2e711e21f6570da964fce4654b1976500dbe043f61778bce0008500078564638"),
    ("DDKoreanPatch-v1.0.1-plugin-only.zip",
     "https://github.com/krPlatypus/Database-Detective-Korean-Patch/releases/download/v1.0.1/",
     "54b2bf400788705f883fd56fe743e98473c35dcbe02ba82c8026f5b80a255257"),
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def download(name, base_url, expected):
    cache = RELEASE / "downloads"
    cache.mkdir(parents=True, exist_ok=True)
    path = cache / name
    if not path.exists():
        partial = path.with_suffix(".part")
        try:
            subprocess.run(["curl", "--fail", "--location", "--silent", "--show-error",
                            "--retry", "3", base_url + name, "--output", str(partial)], check=True)
            if digest(partial) != expected:
                raise ValueError(f"SHA-256 불일치: {name}")
            partial.replace(path)
        finally:
            partial.unlink(missing_ok=True)
    if digest(path) != expected:
        raise ValueError(f"SHA-256 불일치: {path}. 이 캐시를 삭제한 뒤 다시 받으세요.")
    return path


def extract(archive, target, plugin_only=False):
    with zipfile.ZipFile(archive) as zf:
        for entry in zf.infolist():
            path = Path(entry.filename)
            if path.is_absolute() or ".." in path.parts:
                raise ValueError(f"안전하지 않은 ZIP 경로: {entry.filename}")
            if plugin_only and not entry.filename.startswith("BepInEx/plugins/DDKoreanPatch/"):
                continue
            zf.extract(entry, target)


def build_launcher(stage):
    app = stage / "DDKoreanPatch.app"
    executable = app / "Contents/MacOS/DDKoreanPatch"
    executable.parent.mkdir(parents=True)
    subprocess.run([
        "xcrun", "clang", "-arch", "arm64", "-arch", "x86_64",
        "-mmacosx-version-min=12.0", "-Wall", "-Wextra", "-Werror",
        str(ROOT / "tools/macos_launcher.c"), "-o", str(executable),
    ], check=True)
    (app / "Contents/Info.plist").write_bytes(plistlib.dumps({
        "CFBundleExecutable": "DDKoreanPatch",
        "CFBundleIdentifier": "kr.spade.databasedetective.koreanlauncher",
        "CFBundleName": "Database Detective Korean Patch",
        "CFBundlePackageType": "APPL",
        "CFBundleVersion": "1",
        "CFBundleShortVersionString": "1.0.1",
        "LSMinimumSystemVersion": "12.0",
        "LSUIElement": True,
    }))
    subprocess.run(["codesign", "--force", "--sign", "-", str(app)], check=True)
    subprocess.run(["codesign", "--verify", str(app)], check=True)


def build_current_translation(game):
    import common
    from extract_text import extract_text_assets
    from build_translation import build

    common.DATA_DIR = str(game / "copOS.app/Contents/Resources/Data")
    originals, _ = extract_text_assets()
    return Path(build(original_records=originals))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-dir", type=Path, default=DEFAULT_GAME)
    parser.add_argument("--dotnet", default="dotnet", help=".NET SDK 실행 파일")
    args = parser.parse_args()
    if sys.platform != "darwin" or not shutil.which("xcrun"):
        parser.error("앱 실행기를 빌드하려면 macOS와 Xcode Command Line Tools가 필요합니다.")
    managed = args.game_dir.expanduser().resolve() / "copOS.app/Contents/Resources/Data/Managed"
    if not (managed / "Scripts.dll").is_file():
        parser.error(f"macOS 게임의 Managed 폴더가 없습니다: {managed}")
    if not shutil.which(args.dotnet):
        parser.error(".NET SDK가 필요합니다. dotnet을 설치하거나 --dotnet 경로를 지정하세요.")

    archives = [download(*entry) for entry in DOWNLOADS]
    translation = build_current_translation(args.game_dir.expanduser().resolve())
    RELEASE.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="macos-build-", dir=RELEASE) as temp:
        stage = Path(temp)
        extract(archives[0], stage)
        extract(archives[1], stage, plugin_only=True)
        shutil.copy2(translation, stage / "BepInEx/plugins/DDKoreanPatch/translation.json")
        subprocess.run([
            args.dotnet, "build", str(ROOT / "src/DDKoreanPatch/DDKoreanPatch.csproj"),
            "-c", "Release", "--nologo",
            f"-p:ManagedDir={managed}", f"-p:BepInExCore={stage / 'BepInEx/core'}",
        ], cwd=ROOT, check=True)
        dll = ROOT / "src/DDKoreanPatch/bin/Release/netstandard2.1/DDKoreanPatch.dll"
        shutil.copy2(dll, stage / "BepInEx/plugins/DDKoreanPatch/DDKoreanPatch.dll")
        for source in (ROOT / "packaging/macos").iterdir():
            if source.is_file():
                shutil.copy2(source, stage / source.name)
        shutil.copy2(ROOT / "packaging/NOTICE.txt", stage / "NOTICE.txt")
        for name in ("run_bepinex.sh", "run_korean_patch.command", "install_macos.command"):
            (stage / name).chmod(0o755)
        build_launcher(stage)

        output = RELEASE / "DDKoreanPatch-v1.0.1-macos.zip"
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zf:
            for path in sorted(stage.rglob("*")):
                if path.is_file():
                    zf.write(path, path.relative_to(stage))
        checksum = digest(output)
        output.with_suffix(".zip.sha256").write_text(f"{checksum}  {output.name}\n", encoding="utf-8")
        print(f"macOS 배포판: {output}\nSHA-256: {checksum}")


if __name__ == "__main__":
    main()
