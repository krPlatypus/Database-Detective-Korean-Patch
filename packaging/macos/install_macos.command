#!/bin/bash
# 완성된 macOS 배포 폴더에서 실행. SDK, Python, 관리자 권한 불필요.
set -euo pipefail
if [[ "$(uname -s)" != Darwin ]]; then
    echo 'macOS 전용 설치 파일입니다.' >&2
    exit 1
fi
if [[ $# -gt 1 ]]; then
    echo '사용법: bash install_macos.command [copOS.app이 있는 게임 폴더]' >&2
    exit 1
fi
payload="$(cd -- "$(dirname -- "$0")" && pwd -P)"
game_dir="${1:-$HOME/Library/Application Support/Steam/steamapps/common/Database Detective}"
if [[ ! -f "$game_dir/copOS.app/Contents/Resources/Data/Managed/Scripts.dll" ]]; then
    echo "macOS 게임을 찾을 수 없습니다: $game_dir/copOS.app" >&2
    exit 1
fi
game_dir="$(cd -- "$game_dir" && pwd -P)"
if [[ "$payload" == "$game_dir" ]]; then
    echo '배포 압축을 게임 폴더 밖에 풀고 설치 파일을 실행해 주세요.' >&2
    exit 1
fi
if pgrep -x copOS >/dev/null; then
    echo '게임을 종료한 다음 다시 설치해 주세요.' >&2
    exit 1
fi
for required in run_bepinex.sh libdoorstop.dylib run_korean_patch.command DDKoreanPatch.app/Contents/Info.plist DDKoreanPatch.app/Contents/MacOS/DDKoreanPatch BepInEx/core/BepInEx.dll BepInEx/core/BepInEx.Preloader.dll BepInEx/plugins/DDKoreanPatch/DDKoreanPatch.dll BepInEx/plugins/DDKoreanPatch/translation.json BepInEx/plugins/DDKoreanPatch/fonts/neodgm.ttf BepInEx/plugins/DDKoreanPatch/fonts/LICENSE.txt; do
    if [[ ! -f "$payload/$required" ]]; then
        echo "배포 파일이 불완전합니다: $required" >&2
        exit 1
    fi
done

# 교체할 파일만 백업한다. 다른 모드, config, 게임 앱과 세이브는 유지한다.
items=(BepInEx/core BepInEx/plugins/DDKoreanPatch libdoorstop.dylib run_bepinex.sh run_korean_patch.command DDKoreanPatch.app)
backup=""
for item in "${items[@]}"; do
    if [[ -e "$game_dir/$item" ]]; then
        if [[ -z "$backup" ]]; then
            mkdir -p "$game_dir/.ddkorean-backups"
            backup="$(mktemp -d "$game_dir/.ddkorean-backups/$(date +%Y%m%d-%H%M%S).XXXXXX")"
        fi
        mkdir -p "$backup/$(dirname "$item")"
        cp -pR "$game_dir/$item" "$backup/$item"
    fi
done
for item in "${items[@]}"; do
    mkdir -p "$game_dir/$(dirname "$item")"
    if [[ -d "$payload/$item" ]]; then
        mkdir -p "$game_dir/$item"
        cp -pR "$payload/$item/." "$game_dir/$item/"
    else
        cp -p "$payload/$item" "$game_dir/$item"
    fi
done
chmod u+x "$game_dir/run_bepinex.sh" "$game_dir/run_korean_patch.command" "$game_dir/DDKoreanPatch.app/Contents/MacOS/DDKoreanPatch"
echo 'macOS 한글패치 설치 완료.'
[[ -z "$backup" ]] || echo "교체 전 파일 백업: $backup"
echo 'Steam → 게임 속성 → 일반 → 시작 옵션에 아래 한 줄을 입력하세요:'
printf '"%s/DDKoreanPatch.app" %%command%%\n' "$game_dir"
echo '또는 게임 폴더의 DDKoreanPatch.app을 더블 클릭하세요.'
