#!/bin/sh
# Database Detective 한글패치 - macOS 설치 마무리
#
# 압축을 게임 폴더에 푼 뒤 이 파일을 한 번 실행하면 된다.
#   1. 인터넷에서 받은 파일에 붙는 격리 표시를 뗀다.
#   2. run_bepinex.sh에 실행 권한을 준다.
#   3. 스팀 실행 옵션에 run_bepinex.sh를 적는다.
#      이게 없으면 스팀이 게임을 바로 켜서 패치가 들어가지 않는다(영어로 나온다).
#
# 스팀은 꺼질 때 설정 파일을 덮어쓰므로, 켜져 있으면 잠시 끄고 고친 뒤 다시 켠다.

APP_ID=3950130
GAME_DIR=$(cd "$(dirname "$0")" && pwd -P)
STEAM_DIR="$HOME/Library/Application Support/Steam"

fail() {
    echo ""
    echo "  !! $1"
    echo ""
    exit 1
}

echo ""
echo "  Database Detective 한글패치 설치 (macOS)"
echo "  게임 폴더: $GAME_DIR"
echo ""

[ -d "$GAME_DIR/copOS.app" ] || fail "copOS.app이 없습니다. 이 파일을 게임 폴더(copOS.app이 있는 곳)에 넣고 실행하십시오."
[ -f "$GAME_DIR/run_bepinex.sh" ] || fail "run_bepinex.sh가 없습니다. 압축 파일 안의 것을 전부 게임 폴더에 넣으십시오."

xattr -dr com.apple.quarantine "$GAME_DIR" 2>/dev/null
chmod +x "$GAME_DIR/run_bepinex.sh"
echo "  [1/2] 격리 표시 제거, 실행 권한 부여"

configs=$(ls "$STEAM_DIR"/userdata/*/config/localconfig.vdf 2>/dev/null)
[ -n "$configs" ] || fail "스팀 설정 파일을 찾지 못했습니다. 스팀에 한 번 로그인한 뒤 다시 실행하십시오."

steam_was_running=""
if pgrep -x steam_osx >/dev/null 2>&1; then
    steam_was_running=1
    echo "        스팀 설정을 고치려고 스팀을 잠시 끕니다..."
    osascript -e 'quit app "Steam"' >/dev/null 2>&1
    i=0
    while pgrep -x steam_osx >/dev/null 2>&1; do
        i=$((i+1))
        [ $i -gt 60 ] && fail "스팀이 꺼지지 않습니다. 스팀을 직접 끄고 다시 실행하십시오."
        sleep 1
    done
fi

launch="\"$GAME_DIR/run_bepinex.sh\" %command%"

echo "$configs" | while IFS= read -r config; do
    cp "$config" "$config.koreanpatch.bak"
    LAUNCH="$launch" APP_ID="$APP_ID" perl - "$config" <<'PERLEOF' || echo "        (!) 고치지 못함: $config"
use strict; use warnings;
my $path = $ARGV[0];
open(my $in, '<:raw', $path) or die; local $/; my $s = <$in>; close $in;

# 따옴표 안의 중괄호는 건너뛰며 짝이 맞는 닫는 중괄호 위치를 찾는다.
sub block_end {
    my ($str, $open) = @_;
    my ($depth, $q) = (0, 0);
    for (my $i = $open; $i < length $str; $i++) {
        my $c = substr($str, $i, 1);
        if ($q) { if ($c eq '\\') { $i++; } elsif ($c eq '"') { $q = 0; } next; }
        if ($c eq '"') { $q = 1; }
        elsif ($c eq '{') { $depth++; }
        elsif ($c eq '}') { $depth--; return $i if $depth == 0; }
    }
    die "unbalanced\n";
}

(my $value = $ENV{LAUNCH}) =~ s/(["\\])/\\$1/g;
my $id = $ENV{APP_ID};

$s =~ /"apps"\s*\{/g or die "no apps\n";
my $apps_open = pos($s) - 1;
my $apps_end = block_end($s, $apps_open);
my ($indent) = substr($s, 0, $apps_open) =~ /\n(\t*)"apps"\s*$/;
$indent //= "";

my $app = substr($s, $apps_open, $apps_end - $apps_open);
if ($app =~ /\n\t*"$id"\s*\{/g) {
    my $open = $apps_open + pos($app) - 1;
    my $end = block_end($s, $open);
    my $body = substr($s, $open, $end - $open);
    if ($body =~ s/("LaunchOptions"\s*)"(?:[^"\\]|\\.)*"/$1"$value"/) {
        substr($s, $open, $end - $open) = $body;
    } else {
        substr($s, $open + 1, 0) = "\n$indent\t\t\"LaunchOptions\"\t\t\"$value\"";
    }
} else {
    substr($s, $apps_open + 1, 0) =
        "\n$indent\t\"$id\"\n$indent\t{\n$indent\t\t\"LaunchOptions\"\t\t\"$value\"\n$indent\t}";
}

open(my $out, '>:raw', $path) or die; print $out $s; close $out;
PERLEOF
done
echo "  [2/2] 스팀 실행 옵션 설정"
echo "        $launch"

if [ -n "$steam_was_running" ]; then
    open -a Steam
    echo ""
    echo "  스팀을 다시 켰습니다."
fi

echo ""
echo "  끝났습니다. 스팀에서 게임을 켜면 한글로 나옵니다."
echo ""
