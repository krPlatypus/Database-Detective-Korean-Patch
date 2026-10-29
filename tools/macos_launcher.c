#include <mach-o/dyld.h>
#include <limits.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

// Steam의 macOS 실행 경로가 셸 스크립트를 거부하는 경우를 위한 앱 진입점.
// 이 앱과 나란히 설치한 스크립트로 인수를 전달하며 게임 원본은 바꾸지 않는다.
int main(int argc, char **argv) {
    char raw[PATH_MAX], path[PATH_MAX], script[PATH_MAX];
    uint32_t size = sizeof(raw);
    if (_NSGetExecutablePath(raw, &size) || !realpath(raw, path)) return 1;
    // <게임 폴더>/DDKoreanPatch.app/Contents/MacOS/DDKoreanPatch
    for (int i = 0; i < 4; i++) {
        char *slash = strrchr(path, '/');
        if (!slash) return 1;
        *slash = '\0';
    }
    int length = snprintf(script, sizeof(script), "%s/run_korean_patch.command", path);
    if (length < 0 || (size_t)length >= sizeof(script)) return 1;
    if (chdir(path) || access(script, R_OK)) { perror("Korean patch launcher"); return 1; }
    char **args = calloc((size_t)argc + 2, sizeof(char *));
    if (!args) return 1;
    args[0] = "/bin/bash";
    args[1] = script;
    for (int i = 1; i < argc; i++) args[i + 1] = argv[i];
    execv(args[0], args);
    perror("Korean patch launcher");
    free(args);
    return 1;
}
