"""타건음 음원을 게임에 쓰기 좋은 형태로 손본다.

sounds/ 의 원본을 읽어 dist/sounds/ 로 내보낸다. 세 가지를 한다.

  1. 앞 무음 잘라내기
     녹음 파일은 앞에 무음이 붙어 있는 경우가 많다. 이 프로젝트의 원본은
     0.15~0.23초나 됐는데, 그대로 쓰면 키를 치고 그만큼 늦게 소리가 난다.
     실제로 소리가 시작하는 지점부터 쓰도록 자른다.

  2. 길이 줄이고 끝을 부드럽게
     꼬리가 길면 빠르게 칠 때 소리가 겹쳐 뭉갠다. 여운만 남기고 끊되,
     뚝 끊기면 딱 소리가 나므로 끝부분을 서서히 줄인다.

  3. 무압축 WAV 모노로 변환
     MP3는 재생할 때마다 풀어야 해서 손해다. 짧은 효과음은 그냥 PCM이 낫다.
     화면 UI 소리라 방향감이 필요 없으니 모노로 충분하고 메모리도 절반이다.
     파일별 음량 차이도 맞춰 둔다.

ffmpeg이 필요하다. PATH에 있으면 그것을 쓰고, 없으면 FFMPEG 환경변수를 본다.
"""
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_DIR = os.path.join(ROOT, "sounds")
OUT_DIR = os.path.join(ROOT, "dist", "sounds")

AUDIO_EXTENSIONS = (".mp3", ".wav", ".ogg", ".aiff", ".aif", ".flac", ".m4a")

SILENCE_THRESHOLD = "-50dB"   # 이보다 작으면 무음으로 본다
MAX_LENGTH = 0.40             # 초. 이보다 길면 자른다
FADE = 0.06                   # 초. 끝을 줄이는 구간
TARGET_PEAK_DB = -3.0         # 파일 간 음량을 맞출 기준


def find_ffmpeg():
    found = shutil.which("ffmpeg")
    if found:
        return found
    env = os.environ.get("FFMPEG")
    if env and os.path.exists(env):
        return env
    return None


def run(ffmpeg, args):
    return subprocess.run([ffmpeg, "-hide_banner", "-nostats", "-y"] + args,
                          capture_output=True, text=True, encoding="utf-8", errors="replace")


def measure_peak(ffmpeg, path):
    """파일의 최대 음량을 dBFS로 돌려준다."""
    result = run(ffmpeg, ["-i", path, "-af", "volumedetect", "-f", "null", "-"])
    match = re.search(r"max_volume:\s*(-?[0-9.]+) dB", result.stderr or "")
    return float(match.group(1)) if match else 0.0


def build(ffmpeg, source, target):
    # 앞 무음을 떼어 낸 중간 결과를 먼저 만든다. 음량 측정을 잘라낸 뒤에 해야
    # 무음 구간이 결과를 왜곡하지 않는다.
    trimmed = target + ".trim.wav"
    result = run(ffmpeg, [
        "-i", source,
        "-af", f"silenceremove=start_periods=1:start_threshold={SILENCE_THRESHOLD}:detection=peak",
        "-ac", "1", "-ar", "44100", "-c:a", "pcm_s16le",
        trimmed,
    ])
    if not os.path.exists(trimmed):
        return f"앞 무음 제거 실패: {result.stderr.strip().splitlines()[-1] if result.stderr else '알 수 없음'}"

    peak = measure_peak(ffmpeg, trimmed)
    gain = TARGET_PEAK_DB - peak

    fade_start = max(0.0, MAX_LENGTH - FADE)
    result = run(ffmpeg, [
        "-i", trimmed,
        "-af", f"atrim=0:{MAX_LENGTH},asetpts=N/SR/TB,"
               f"afade=t=out:st={fade_start:.3f}:d={FADE},"
               f"volume={gain:.2f}dB",
        "-ac", "1", "-ar", "44100", "-c:a", "pcm_s16le",
        target,
    ])
    os.remove(trimmed)

    if not os.path.exists(target):
        return f"변환 실패: {result.stderr.strip().splitlines()[-1] if result.stderr else '알 수 없음'}"
    return None


def main():
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        print("ffmpeg을 찾지 못했습니다. PATH에 넣거나 FFMPEG 환경변수로 경로를 지정하세요.")
        sys.exit(1)

    if not os.path.isdir(SOURCE_DIR):
        print(f"원본 폴더가 없습니다: {SOURCE_DIR}")
        sys.exit(1)

    made, failed = 0, []
    for folder, _, files in os.walk(SOURCE_DIR):
        for name in sorted(files):
            if not name.lower().endswith(AUDIO_EXTENSIONS):
                continue

            source = os.path.join(folder, name)
            relative = os.path.relpath(folder, SOURCE_DIR)
            out_folder = os.path.join(OUT_DIR, relative) if relative != "." else OUT_DIR
            os.makedirs(out_folder, exist_ok=True)

            target = os.path.join(out_folder, os.path.splitext(name)[0] + ".wav")
            error = build(ffmpeg, source, target)
            if error:
                failed.append(f"{name}: {error}")
            else:
                made += 1
                size = os.path.getsize(target) / 1024
                print(f"  {name}  ->  {os.path.basename(target)}  ({size:.0f} KB)")

    print(f"\n  {made}개 생성 -> {OUT_DIR}")
    for message in failed:
        print(f"  {message}")


if __name__ == "__main__":
    main()
