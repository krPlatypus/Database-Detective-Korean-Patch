#!/bin/bash
# Finder 더블 클릭과 Steam의 %command% 양쪽에서 사용한다.
set -euo pipefail
game_dir="$(cd -- "$(dirname -- "$0")" && pwd -P)"
cd "$game_dir"

for required in run_bepinex.sh libdoorstop.dylib BepInEx/core/BepInEx.Preloader.dll BepInEx/plugins/DDKoreanPatch/DDKoreanPatch.dll; do
    if [[ ! -f "$required" ]]; then
        echo "한글패치 파일이 없습니다: $game_dir/$required" >&2
        exit 1
    fi
done
if [[ ! -d copOS.app ]]; then
    echo '이 실행 파일을 copOS.app과 같은 폴더에 넣어 주세요.' >&2
    exit 1
fi

# 인수 없이 실행하거나 게임 옵션만 넘기면 macOS 앱을 직접 지정한다.
# Steam이 실행 파일을 넘겼다면 그 경로와 모든 인수를 그대로 전달한다.
if [[ $# -eq 0 || "$1" == -* ]]; then
    set -- "$game_dir/copOS.app" "$@"
fi
export SteamAppId="${SteamAppId:-3950130}"
export SteamGameId="${SteamGameId:-3950130}"
exec /bin/sh "$game_dir/run_bepinex.sh" "$@"
