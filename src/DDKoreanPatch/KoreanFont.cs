using System.Collections.Generic;
using System.IO;
using TMPro;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.TextCore;
using UnityEngine.TextCore.LowLevel;

namespace DDKoreanPatch
{
    /// <summary>
    /// 한글 글리프 공급.
    ///
    /// 게임에 들어 있는 폰트(W95FA, LiberationSans, Anton 등)는 전부 라틴 전용이라
    /// 한글을 넣으면 두부(□)로 보인다. 한글을 담은 폰트 에셋을 만들어
    /// 모든 폰트의 폴백으로 걸어두면, 라틴 글자는 원래 폰트 모양 그대로 두고
    /// 한글만 폴백에서 가져다 쓴다.
    ///
    /// 폰트는 OS에 설치된 것을 DynamicOS 모드로 참조한다.
    /// 글리프를 그때그때 OS에서 가져오므로 폰트 파일을 패치에 동봉할 필요가 없고,
    /// 따라서 폰트 재배포 라이선스 문제가 생기지 않는다.
    /// </summary>
    internal static class KoreanFont
    {
        private const string FallbackAssetName = "DDKoreanPatch Korean Fallback";

        internal static TMP_FontAsset Asset { get; private set; }

        /// <summary>플러그인 폴더의 fonts/ 경로. 동봉 폰트를 여기서 찾는다.</summary>
        private static string fontDirectory;

        internal static void Install(string pluginDirectory)
        {
            fontDirectory = Path.Combine(pluginDirectory, "fonts");
            Install();
        }

        internal static void Install()
        {
            if (Asset == null && !TryCreateAsset())
            {
                return;
            }

            ApplyHangulLineBreaking();
            ApplyFallbacks();
            SceneManager.sceneLoaded += OnSceneLoaded;
        }

        private static void OnSceneLoaded(Scene scene, LoadSceneMode mode)
        {
            // 씬마다 새로 올라오는 폰트 에셋에도 폴백을 다시 걸어준다.
            ApplyFallbacks();
        }

        private static bool TryCreateAsset()
        {
            string family = Plugin.FontFamily.Value;
            string style = Plugin.FontStyle.Value;
            string description;

            // 동봉 폰트가 있으면 그쪽을 먼저 쓴다.
            // OS에 없는 글꼴(예: 픽셀 글꼴)을 쓰려면 이 길밖에 없다.
            string bundled = BundledFontPath();
            if (bundled != null)
            {
                Asset = TMP_FontAsset.CreateFontAsset(
                    bundled,
                    0,
                    Plugin.FontPointSize.Value,
                    Plugin.FontAtlasPadding.Value,
                    GlyphRenderMode.SDFAA,
                    1024,
                    1024);
                description = Path.GetFileName(bundled);

                if (Asset == null)
                {
                    Plugin.Log.LogWarning(
                        $"동봉 폰트를 불러오지 못했습니다: {bundled}. OS 폰트로 넘어갑니다.");
                }
            }
            else
            {
                description = null;
            }

            if (Asset == null)
            {
                Asset = TMP_FontAsset.CreateFontAsset(family, style, Plugin.FontPointSize.Value);
                description = $"{family} {style}";
            }

            if (Asset == null)
            {
                Plugin.Log.LogError(
                    $"한글 폰트를 만들지 못했습니다. OS에 '{family} {style}' 폰트가 있는지 확인하세요. "
                    + "설정 파일의 FontFamily/FontStyle로 다른 폰트를 지정할 수 있습니다.");
                return false;
            }

            Asset.name = FallbackAssetName;
            Asset.hideFlags = HideFlags.HideAndDontSave;
            Object.DontDestroyOnLoad(Asset);
            ApplyScale();

            // 글리프를 필요할 때 가져오는 방식이라, 기본 오버로드는 아직 안 불러온 글자를
            // 없다고 보고한다. tryAddCharacter로 실제 공급 가능 여부를 묻는다.
            bool hasHangul = Asset.HasCharacter('한', false, true)
                             && Asset.HasCharacter('글', false, true);
            if (hasHangul)
            {
                Plugin.Log.LogInfo($"한글 폰트 준비 완료: {description}");
            }
            else
            {
                Plugin.Log.LogWarning(
                    $"'{description}' 폰트를 불러왔지만 한글 글리프가 없습니다. 다른 폰트를 지정하세요.");
            }

            return true;
        }

        /// <summary>
        /// 폴백 글꼴의 글자 크기를 원래 글꼴에 맞춘다.
        ///
        /// TMP는 글자 크기를 이렇게 잡는다.
        ///     크기 = 글꼴크기 / faceInfo.pointSize * faceInfo.scale
        ///
        /// 글꼴마다 네모칸(em) 안에서 글자가 차지하는 비율이 다르다.
        /// 한글 글꼴은 네모칸을 거의 꽉 채우는 반면 라틴 글꼴은 대문자 높이가
        /// 네모칸의 70% 안팎이라, 같은 글꼴크기를 줘도 한글이 눈에 띄게 커 보인다.
        /// scale을 낮춰 눈으로 보이는 크기를 맞춘다.
        /// </summary>
        /// <summary>
        /// 한글을 어절 단위로 끊게 한다.
        ///
        /// TMP는 이 설정이 꺼져 있으면 한글을 중국어, 일본어와 같이 보고
        /// 글자 아무 데서나 줄을 끊는다. 그래서 "자동으로"가 "자 / 동으로"처럼
        /// 단어 한가운데서 잘린다. 한글은 띄어쓰기를 쓰므로 그 방식이 맞지 않는다.
        /// </summary>
        private static void ApplyHangulLineBreaking()
        {
            if (!Plugin.ModernHangulLineBreaking.Value)
            {
                return;
            }

            try
            {
                TMP_Settings.useModernHangulLineBreakingRules = true;
                Plugin.Log.LogInfo("한글을 어절 단위로 끊도록 설정했습니다.");
            }
            catch (System.Exception e)
            {
                Plugin.Log.LogWarning($"한글 줄바꿈 규칙을 켜지 못했습니다: {e.Message}");
            }
        }

        private static void ApplyScale()
        {
            if (Asset == null)
            {
                return;
            }

            FaceInfo info = Asset.faceInfo;
            info.scale = Plugin.FontScale.Value;

            // 세로 위치도 맞춘다. TMP는 글자의 y 좌표를 이렇게 잡는다.
            //     y = faceInfo.baseline * 글자배율 * 배수 * faceInfo.scale - 줄간격 + 기준선
            // 양수면 위로 올라간다. 네모칸 대비 비율로 받아 글꼴 크기가 바뀌어도
            // 같은 비율로 따라가게 한다.
            info.baseline = Plugin.FontBaselineOffset.Value * info.pointSize;

            Asset.faceInfo = info;

            Plugin.Log.LogInfo(
                $"글자 크기 보정 {info.scale:0.##}, 세로 위치 보정 {Plugin.FontBaselineOffset.Value:0.###}");
        }

        /// <summary>
        /// 동봉 폰트 파일 경로. 설정에 적힌 파일이 fonts/ 아래에 있을 때만 돌려준다.
        ///
        /// OS에 없는 글꼴을 쓰려면 파일에서 직접 읽는 수밖에 없다.
        /// 옛 윈도우의 각진 한글 느낌은 비트맵 글리프에서 나오는데, 요즘 렌더링은
        /// 외곽선을 부드럽게 그려내므로 그 느낌이 나지 않는다.
        /// 외곽선 자체가 계단 모양인 픽셀 글꼴을 쓰면 그 결이 살아남는다.
        /// </summary>
        private static string BundledFontPath()
        {
            string fileName = Plugin.FontFile.Value?.Trim();
            if (string.IsNullOrEmpty(fileName) || fontDirectory == null)
            {
                return null;
            }

            string path = Path.Combine(fontDirectory, fileName);
            return File.Exists(path) ? path : null;
        }

        /// <summary>
        /// 전역 폴백과 개별 폰트 에셋 폴백 양쪽에 등록한다.
        /// 전역 폴백만으로 충분한 경우가 많지만, 폰트에 자체 폴백 목록이 걸려 있으면
        /// 그쪽이 먼저 소진되므로 개별 등록도 함께 해둔다.
        /// </summary>
        private static void ApplyFallbacks()
        {
            if (Asset == null)
            {
                return;
            }

            RegisterGlobalFallback();

            int count = 0;
            foreach (TMP_FontAsset font in Resources.FindObjectsOfTypeAll<TMP_FontAsset>())
            {
                if (font == null || font == Asset)
                {
                    continue;
                }

                if (font.fallbackFontAssetTable == null)
                {
                    font.fallbackFontAssetTable = new List<TMP_FontAsset>();
                }

                if (!font.fallbackFontAssetTable.Contains(Asset))
                {
                    font.fallbackFontAssetTable.Add(Asset);
                    count++;
                }
            }

            if (count > 0)
            {
                Plugin.Log.LogInfo($"폰트 에셋 {count}개에 한글 폴백을 걸었습니다.");
            }
        }

        private static void RegisterGlobalFallback()
        {
            try
            {
                List<TMP_FontAsset> global = TMP_Settings.fallbackFontAssets;
                if (global == null)
                {
                    global = new List<TMP_FontAsset>();
                    TMP_Settings.fallbackFontAssets = global;
                }

                if (!global.Contains(Asset))
                {
                    global.Add(Asset);
                    Plugin.Log.LogInfo("TMP 전역 폴백에 한글 폰트를 등록했습니다.");
                }
            }
            catch (System.Exception e)
            {
                // TMP_Settings가 아직 없을 수 있다. 개별 폰트 폴백만으로도 동작한다.
                Plugin.Log.LogWarning($"TMP 전역 폴백 등록을 건너뜁니다: {e.Message}");
            }
        }
    }
}
