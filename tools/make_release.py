"""배포용 zip을 만들고, 원하면 GitHub Release까지 올린다.

세 가지를 만든다.

  DDKoreanPatch-v<버전>.zip              전체판. BepInEx까지 들어 있어
                                        게임 폴더에 풀어 넣으면 끝난다.
  DDKoreanPatch-v<버전>-plugin-only.zip  갱신판. 이미 깐 사람이 번역만
                                        새로 받을 때 쓴다. 맥에서도 같다.
  DDKoreanPatch-v<버전>-macos.zip        맥 전체판. 맥용 BepInEx와 실행
                                        스크립트가 들어 있다.

맥용 BepInEx는 게임 폴더가 아니라 공식 배포본을 받아 담는다(sha256 확인).
윈도우에서도 그대로 만들 수 있다. 받은 파일은 release/_cache에 남겨 둔다.

BepInEx는 게임 폴더에 깔린 것을 그대로 담는다. 우리가 고친 것이 아니라
공식 배포본 그대로이므로, LGPL-2.1에 따라 출처와 라이선스를 NOTICE.txt에
적어 함께 넣는다.

쓰는 법:

  python tools/make_release.py 1.0.0            zip만 만든다
  python tools/make_release.py 1.0.0 --bump     Plugin.cs 버전도 맞춘다
  python tools/make_release.py 1.0.0 --publish  태그를 밀고 Release까지
  python tools/make_release.py 1.0.0 --no-macos 맥 전체판은 건너뛴다

--publish는 gh(GitHub CLI)가 있어야 한다. 없으면 zip은 그대로 두고
직접 올리는 방법을 알려 준다.
"""
import argparse
import datetime
import hashlib
import io
import os
import re
import shutil
import subprocess
import sys
import urllib.request
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, "dist")
PACKAGING = os.path.join(ROOT, "packaging")
OUT_DIR = os.path.join(ROOT, "release")
CSPROJ = os.path.join(ROOT, "src", "DDKoreanPatch", "DDKoreanPatch.csproj")
PLUGIN_CS = os.path.join(ROOT, "src", "DDKoreanPatch", "Plugin.cs")

PLUGIN_SUBDIR = "BepInEx/plugins/DDKoreanPatch"
MACOS_PACKAGING = os.path.join(PACKAGING, "macos")
CACHE_DIR = os.path.join(OUT_DIR, "_cache")

# 맥 전체판에 담을 공식 배포본. 바꿀 때는 sha256도 같이 고친다.
#
# BepInEx는 윈도우판과 같은 5.4.23.5의 맥 빌드다. core의 dll은 플랫폼마다
# 빌드가 달라 윈도우판 것을 그대로 쓰면 안 된다.
#
# libdoorstop.dylib만은 UnityDoorstop 4.6.0으로 바꿔 담는다. BepInEx에 든
# 4.5.0은 Unity 6.3 이상의 chained fixups를 읽지 못해
# "Failed to open current process PLT! ... unknown imports format 0"으로
# 아무것도 하지 않는다. 4.6.0에서 고쳐졌다 (UnityDoorstop#117).
MACOS_BEPINEX = (
    "https://github.com/BepInEx/BepInEx/releases/download/v5.4.23.5/"
    "BepInEx_macos_universal_5.4.23.5.zip",
    "01c2ae782eb016dfd6c345a18dbd2dcafffb3d9d318449d6486689f426b4a323")
MACOS_DOORSTOP = (
    "https://github.com/NeighTools/UnityDoorstop/releases/download/v4.6.0/"
    "doorstop_macos_release_4.6.0.zip",
    "8282e8ec37abc81bbf736d12c315fdb78b0418654fb57be9e40858649953ccb7")

# 맥 전체판의 로더 파일. 어디서 가져오는지는 stage_macos()를 보라.
MACOS_LOADER_FILES = ["run_bepinex.sh", "libdoorstop.dylib", ".doorstop_version", "changelog.txt"]

# 게임 폴더에서 그대로 가져올 BepInEx 파일. core는 .dll만 담는다.
# .xml은 개발용 문서 주석이라 있어도 동작이 달라지지 않고 용량만 는다.
LOADER_FILES = ["winhttp.dll", "doorstop_config.ini", ".doorstop_version", "changelog.txt"]

# 동봉할 글꼴. dist/fonts에는 쓰지 않는 글꼴도 들어 있어 짚어서 담는다.
FONTS = ["neodgm.ttf", "LICENSE.txt"]

VERSION_RE = re.compile(r'(PluginVersion\s*=\s*")([^"]+)(")')


def fail(message):
    print(f"\n  !! {message}")
    sys.exit(1)


def read_version():
    with io.open(PLUGIN_CS, encoding="utf-8") as f:
        found = VERSION_RE.search(f.read())
    return found.group(2) if found else None


def write_version(version):
    with io.open(PLUGIN_CS, encoding="utf-8") as f:
        source = f.read()
    with io.open(PLUGIN_CS, "w", encoding="utf-8") as f:
        f.write(VERSION_RE.sub(lambda m: m.group(1) + version + m.group(3), source))


def game_dir():
    """csproj에 적힌 게임 폴더. 여기저기 적지 않으려고 한곳에서 읽는다."""
    with io.open(CSPROJ, encoding="utf-8") as f:
        found = re.search(r"<GameDir>(.*?)</GameDir>", f.read())
    if not found:
        fail("csproj에서 GameDir을 찾지 못했습니다.")
    return found.group(1)


def build():
    print("  플러그인 빌드")
    result = subprocess.run(
        ["dotnet", "build", CSPROJ, "-c", "Release", "-v", "quiet", "--nologo"],
        cwd=ROOT, capture_output=True, text=True,
        encoding="utf-8", errors="replace")
    if result.returncode != 0:
        print(result.stdout[-3000:])
        print(result.stderr[-2000:])
        fail("빌드에 실패했습니다.")

    for folder in ("Release", "Debug"):
        candidate = os.path.join(ROOT, "src", "DDKoreanPatch", "bin", folder,
                                 "netstandard2.1", "DDKoreanPatch.dll")
        if os.path.exists(candidate):
            return candidate
    fail("빌드 결과에서 DDKoreanPatch.dll을 찾지 못했습니다.")


def check_bundle():
    """dist/ 가 최신인지 거칠게 본다. 번역만 고치고 묶는 것을 잊는 일이 잦다."""
    bundle = os.path.join(DIST, "translation.json")
    if not os.path.exists(bundle):
        fail("dist/translation.json이 없습니다. tools/build_translation.py를 먼저 돌리십시오.")

    newest = 0
    for folder in (os.path.join(ROOT, "translation"),):
        for base, _, files in os.walk(folder):
            for name in files:
                newest = max(newest, os.path.getmtime(os.path.join(base, name)))

    if newest > os.path.getmtime(bundle):
        print("  (!) translation/ 이 dist/translation.json 보다 새롭습니다.")
        print("      tools/build_translation.py 를 다시 돌리는 편이 좋습니다.")

    images = os.path.join(DIST, "images")
    count = len([n for n in os.listdir(images) if n.endswith(".png")]) if os.path.isdir(images) else 0
    if not count:
        fail("dist/images에 그림이 없습니다. tools/build_clue_images.py를 먼저 돌리십시오.")
    print(f"  번역 그림 {count}장")


def render(name, out_path, folder=PACKAGING, mac=False, **fields):
    with io.open(os.path.join(folder, name), encoding="utf-8") as f:
        text = f.read()
    for key, value in fields.items():
        text = text.replace("{" + key + "}", value)
    if mac:
        # 맥의 텍스트 편집기는 BOM 없는 LF가 자연스럽다.
        with io.open(out_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        return
    # 메모장에서 열어 보는 사람이 많아 CRLF로 내보낸다.
    with io.open(out_path, "w", encoding="utf-8-sig", newline="\r\n") as f:
        f.write(text)


def stage_plugin(root, dll):
    """플러그인 폴더(BepInEx/plugins/DDKoreanPatch)를 늘어놓는다. 윈도우·맥 공통."""
    plugin = os.path.join(root, *PLUGIN_SUBDIR.split("/"))
    os.makedirs(plugin)

    shutil.copy2(dll, os.path.join(plugin, "DDKoreanPatch.dll"))
    shutil.copy2(os.path.join(DIST, "translation.json"), plugin)
    shutil.copytree(os.path.join(DIST, "images"), os.path.join(plugin, "images"))

    os.makedirs(os.path.join(plugin, "fonts"))
    for name in FONTS:
        source = os.path.join(DIST, "fonts", name)
        if not os.path.exists(source):
            fail(f"동봉할 글꼴이 없습니다: dist/fonts/{name}")
        shutil.copy2(source, os.path.join(plugin, "fonts", name))

    sounds = os.path.join(DIST, "sounds")
    if os.path.isdir(sounds) and any(os.scandir(sounds)):
        shutil.copytree(sounds, os.path.join(plugin, "sounds"))


def stage(version, dll, full):
    """zip에 넣을 것을 임시 폴더에 그대로 늘어놓는다."""
    root = os.path.join(OUT_DIR, "_staging", "full" if full else "plugin")
    if os.path.exists(root):
        shutil.rmtree(root)

    stage_plugin(root, dll)

    if full:
        game = game_dir()
        for name in LOADER_FILES:
            source = os.path.join(game, name)
            if not os.path.exists(source):
                fail(f"게임 폴더에 {name}이 없습니다. BepInEx가 깔려 있어야 전체판을 만듭니다.")
            shutil.copy2(source, os.path.join(root, name))

        core_out = os.path.join(root, "BepInEx", "core")
        os.makedirs(core_out)
        core_in = os.path.join(game, "BepInEx", "core")
        for name in sorted(os.listdir(core_in)):
            if name.endswith(".dll"):
                shutil.copy2(os.path.join(core_in, name), os.path.join(core_out, name))

    note = "" if full else (
        "--------------------------------------------------------------------\n"
        " 이 파일은 갱신판입니다\n"
        "--------------------------------------------------------------------\n"
        "\n"
        " 번역만 새로 담은 것이라 BepInEx는 들어 있지 않습니다.\n"
        " 한글패치를 처음 까시는 것이라면 전체판을 받으십시오.\n"
        " 이미 까신 분은 이 파일을 게임 폴더에 덮어쓰면 됩니다.\n"
        " 설정(BepInEx\\config)은 건드리지 않습니다.\n"
        "\n")

    today = datetime.date.today().strftime("%Y-%m-%d")
    render("읽어주세요.txt", os.path.join(root, "읽어주세요.txt"),
           version=f"v{version}", date=today, update_note=note)
    render("NOTICE.txt", os.path.join(root, "NOTICE.txt"))
    return root


def fetch(url, sha256):
    """공식 배포본을 받아 release/_cache에 둔다. 해시가 다르면 멈춘다."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    path = os.path.join(CACHE_DIR, url.rsplit("/", 1)[1])
    if not os.path.exists(path):
        print(f"  받는 중 {os.path.basename(path)}")
        with urllib.request.urlopen(url) as response, open(path + ".part", "wb") as f:
            shutil.copyfileobj(response, f)
        os.replace(path + ".part", path)
    with open(path, "rb") as f:
        digest = hashlib.sha256(f.read()).hexdigest()
    if digest != sha256:
        os.remove(path)
        fail(f"{os.path.basename(path)}의 sha256이 다릅니다.\n     기대 {sha256}\n     실제 {digest}")
    return path


def unzip_member(zip_path, suffix):
    """zip 안에서 경로가 suffix로 끝나는 파일 하나를 꺼낸다."""
    with zipfile.ZipFile(zip_path) as zf:
        names = [n for n in zf.namelist() if n == suffix or n.endswith("/" + suffix)]
        if len(names) != 1:
            fail(f"{os.path.basename(zip_path)}에서 {suffix}를 찾지 못했습니다.")
        return zf.read(names[0])


def stage_macos(version, dll):
    """맥 전체판. 공식 BepInEx 맥 빌드 + Doorstop 4.6.0 + 고친 실행 스크립트."""
    root = os.path.join(OUT_DIR, "_staging", "macos")
    if os.path.exists(root):
        shutil.rmtree(root)

    stage_plugin(root, dll)

    bepinex = fetch(*MACOS_BEPINEX)
    doorstop = fetch(*MACOS_DOORSTOP)

    core_out = os.path.join(root, "BepInEx", "core")
    os.makedirs(core_out)
    with zipfile.ZipFile(bepinex) as zf:
        for name in zf.namelist():
            if name.startswith("BepInEx/core/") and name.endswith(".dll"):
                with open(os.path.join(core_out, name.rsplit("/", 1)[1]), "wb") as f:
                    f.write(zf.read(name))

    sources = {
        # 공식 run_bepinex.sh에서 실행 파일 이름과 Rosetta 실행만 고친 것.
        "run_bepinex.sh": lambda: open(os.path.join(MACOS_PACKAGING, "run_bepinex.sh"), "rb").read(),
        "libdoorstop.dylib": lambda: unzip_member(doorstop, "universal/libdoorstop.dylib"),
        ".doorstop_version": lambda: unzip_member(doorstop, "universal/.doorstop_version"),
        "changelog.txt": lambda: unzip_member(bepinex, "changelog.txt"),
    }
    for name in MACOS_LOADER_FILES:
        with open(os.path.join(root, name), "wb") as f:
            f.write(sources[name]())

    today = datetime.date.today().strftime("%Y-%m-%d")
    render("읽어주세요.txt", os.path.join(root, "읽어주세요.txt"), folder=MACOS_PACKAGING,
           mac=True, version=f"v{version}", date=today, update_note="")
    render("NOTICE.txt", os.path.join(root, "NOTICE.txt"), mac=True)
    return root


# zip 안에서 실행 권한을 줄 파일. 윈도우에서 묶으면 권한 비트가 없으므로 직접 적는다.
EXECUTABLES = {"run_bepinex.sh"}


def pack(root, zip_path):
    if os.path.exists(zip_path):
        os.remove(zip_path)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for base, _, files in os.walk(root):
            for name in sorted(files):
                path = os.path.join(base, name)
                info = zipfile.ZipInfo.from_file(path, os.path.relpath(path, root).replace("\\", "/"))
                info.compress_type = zipfile.ZIP_DEFLATED
                mode = 0o755 if name in EXECUTABLES else 0o644
                info.external_attr = (0o100000 | mode) << 16
                info.create_system = 3  # unix. 그래야 맥의 압축 풀기가 권한을 읽는다.
                with open(path, "rb") as f:
                    zf.writestr(info, f.read(), compresslevel=9)

    size = os.path.getsize(zip_path) / (1024 * 1024)
    with open(zip_path, "rb") as f:
        digest = hashlib.sha256(f.read()).hexdigest()
    print(f"  {os.path.basename(zip_path)}  ({size:.1f} MB)")
    print(f"     sha256 {digest}")
    return digest


def find_gh():
    """gh를 찾는다. 갓 깐 직후에는 PATH에 아직 안 잡혀 있을 수 있다."""
    found = shutil.which("gh")
    if found:
        return found
    for candidate in (
        r"C:\Program Files\GitHub CLI\gh.exe",
        r"C:\Program Files (x86)\GitHub CLI\gh.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Links\gh.exe"),
    ):
        if os.path.exists(candidate):
            return candidate
    return None


def git(*args, check=True):
    result = subprocess.run(["git"] + list(args), cwd=ROOT, capture_output=True, text=True,
                            encoding="utf-8", errors="replace")
    if check and result.returncode != 0:
        fail(f"git {' '.join(args)} 실패:\n{result.stderr.strip()}")
    return result.stdout.strip()


def publish(version, zips, digests):
    tag = f"v{version}"

    if git("status", "--porcelain"):
        fail("고치다 만 것이 남아 있습니다. 커밋하고 다시 하십시오.")

    gh = find_gh()
    if gh is None:
        print("\n  gh(GitHub CLI)가 없어 Release는 만들지 못했습니다.")
        print("  설치: winget install --id GitHub.cli")
        print(f"  또는 아래에서 {tag} 태그로 직접 올리십시오.")
        print("  https://github.com/krPlatypus/Database-Detective-Korean-Patch/releases/new")
        return

    if git("tag", "-l", tag):
        print(f"  태그 {tag}가 이미 있습니다. 그대로 씁니다.")
    else:
        git("tag", "-a", tag, "-m", f"Database Detective 한글패치 {tag}")
    git("push", "origin", "main")
    git("push", "origin", tag)

    # 본문은 매번 다시 쓴다. 다시 묶으면 sha256이 달라지므로 남겨 두면 어긋난다.
    notes = os.path.join(OUT_DIR, f"notes-{tag}.md")
    write_notes(notes, version, zips, digests)

    # 태그를 밀면 워크플로가 먼저 초안을 만들어 둘 수 있다. 있으면 파일만 얹는다.
    exists = subprocess.run([gh, "release", "view", tag], cwd=ROOT,
                            capture_output=True, text=True,
                            encoding="utf-8", errors="replace").returncode == 0

    if exists:
        print(f"  Release {tag}가 이미 있어 파일만 올립니다")
        command = [gh, "release", "upload", tag] + zips + ["--clobber"]
    else:
        print(f"  Release {tag} 만드는 중")
        command = ([gh, "release", "create", tag] + zips
                   + ["--title", f"한글패치 {tag}", "--notes-file", notes])

    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                            encoding="utf-8", errors="replace")
    if result.returncode != 0:
        print(result.stderr.strip())
        fail("Release에 올리지 못했습니다. 위 메시지를 보십시오.")
    print(f"  {result.stdout.strip()}")

    if exists:
        # 파일만 얹으면 본문에 적힌 sha256이 옛것으로 남는다. 본문도 새로 쓴다.
        subprocess.run([gh, "release", "edit", tag, "--notes-file", notes],
                       cwd=ROOT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")

    print(f"\n  https://github.com/krPlatypus/Database-Detective-Korean-Patch/releases/tag/{tag}")


def write_notes(path, version, zips, digests):
    """CHANGELOG.md에서 이 버전 대목만 떼어 Release 본문을 만든다."""
    changelog = os.path.join(ROOT, "CHANGELOG.md")
    body = ""
    if os.path.exists(changelog):
        with io.open(changelog, encoding="utf-8") as f:
            text = f.read()
        found = re.search(r"^## v" + re.escape(version) + r".*?$(.*?)(?=^## |\Z)",
                          text, re.M | re.S)
        if found:
            body = found.group(1).strip()

    lines = [body, "", "## 받는 곳", ""]
    for zip_path, digest in zip(zips, digests):
        name = os.path.basename(zip_path)
        if "plugin-only" in name:
            kind = "갱신판 (이미 까신 분, 윈도우·맥 공통)"
        elif "macos" in name:
            kind = "맥 전체판 (macOS에서 처음 까시는 분)"
        else:
            kind = "전체판 (처음 까시는 분)"
        lines.append(f"- **{kind}** — `{name}`")
        lines.append(f"  - sha256 `{digest}`")
    lines += ["", "압축을 풀어 게임 폴더(copOS.exe가 있는 곳)에 덮어쓰면 됩니다.",
              "맥은 copOS.app이 있는 곳에 넣고 스팀 실행 옵션을 하나 적어야 합니다.",
              "자세한 것은 압축 파일 안의 `읽어주세요.txt`를 보십시오."]

    with io.open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("version", help="예: 1.0.0")
    parser.add_argument("--bump", action="store_true",
                        help="Plugin.cs의 PluginVersion을 이 버전으로 고친다")
    parser.add_argument("--publish", action="store_true",
                        help="태그를 밀고 GitHub Release까지 만든다")
    parser.add_argument("--no-macos", action="store_true",
                        help="맥 전체판을 만들지 않는다")
    args = parser.parse_args()

    if not re.fullmatch(r"\d+\.\d+\.\d+", args.version):
        fail("버전은 1.0.0 꼴로 적으십시오.")

    current = read_version()
    if current != args.version:
        if not args.bump:
            fail(f"Plugin.cs의 버전은 {current}인데 {args.version}으로 묶으려 합니다.\n"
                 f"     --bump를 붙이면 Plugin.cs를 고쳐 줍니다.")
        write_version(args.version)
        print(f"  Plugin.cs 버전 {current} -> {args.version}")

    os.makedirs(OUT_DIR, exist_ok=True)
    check_bundle()
    dll = build()

    zips, digests = [], []
    for full in (True, False):
        suffix = "" if full else "-plugin-only"
        root = stage(args.version, dll, full)
        path = os.path.join(OUT_DIR, f"DDKoreanPatch-v{args.version}{suffix}.zip")
        digests.append(pack(root, path))
        zips.append(path)

    if not args.no_macos:
        root = stage_macos(args.version, dll)
        path = os.path.join(OUT_DIR, f"DDKoreanPatch-v{args.version}-macos.zip")
        digests.append(pack(root, path))
        zips.append(path)

    shutil.rmtree(os.path.join(OUT_DIR, "_staging"), ignore_errors=True)

    if args.publish:
        publish(args.version, zips, digests)
    else:
        print(f"\n  -> {OUT_DIR}")
        print("  올리려면 --publish를 붙여 다시 돌리십시오.")


if __name__ == "__main__":
    main()
