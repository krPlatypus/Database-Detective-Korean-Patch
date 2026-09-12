using System.Collections.Generic;
using TMPro;
using UnityEngine;
using UnityEngine.SceneManagement;

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

        internal static void Install()
        {
            if (Asset == null && !TryCreateAsset())
            {
                return;
            }

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

            Asset = TMP_FontAsset.CreateFontAsset(family, style, Plugin.FontPointSize.Value);

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

            // DynamicOS 폰트는 글리프를 필요할 때 OS에서 가져온다.
            // 기본 오버로드는 이미 불러온 글자만 보므로 tryAddCharacter로 실제 공급 가능 여부를 묻는다.
            bool hasHangul = Asset.HasCharacter('한', false, true)
                             && Asset.HasCharacter('글', false, true);
            if (hasHangul)
            {
                Plugin.Log.LogInfo($"한글 폰트 준비 완료: {family} {style}");
            }
            else
            {
                Plugin.Log.LogWarning(
                    $"'{family} {style}' 폰트를 불러왔지만 한글 글리프가 없습니다. 다른 폰트를 지정하세요.");
            }

            return true;
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
