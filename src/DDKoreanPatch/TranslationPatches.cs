using HarmonyLib;
using TMPro;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace DDKoreanPatch
{
    /// <summary>
    /// 번역문을 실제 화면에 적용한다.
    ///
    /// UI는 TMP_Text.text 세터 한 곳만 잡으면 코드가 넣는 문자열이 모두 지나간다.
    /// 다만 프리팹에 구워진 채 한 번도 코드로 설정되지 않는 텍스트는 세터를 타지 않으므로
    /// 씬이 바뀔 때마다 훑어서 따로 갈아준다.
    ///
    /// TextAsset은 게임이 내용을 구분자로 쪼개 쓰기 때문에, 화면에 닿기 전에
    /// 원문 전체를 번역문 전체로 바꿔줘야 파싱 결과까지 한글이 된다.
    /// </summary>
    [HarmonyPatch]
    internal static class TranslationPatches
    {
        internal static void HookSceneSweep()
        {
            SceneManager.sceneLoaded += (scene, mode) => SweepScene();
            SweepScene();
        }

        /// <summary>
        /// 프리팹에 구워진 TMP 텍스트를 훑어 번역으로 교체한다.
        /// 교체는 세터를 거치므로 TextSetterPrefix가 다시 호출되지만,
        /// 번역문은 사전에 없으므로 그대로 통과해 무한 반복이 되지 않는다.
        /// </summary>
        internal static void SweepScene()
        {
            if (!Translator.HasUiText)
            {
                return;
            }

            int replaced = 0;
            foreach (TMP_Text label in Resources.FindObjectsOfTypeAll<TMP_Text>())
            {
                if (label == null)
                {
                    continue;
                }

                string original = label.text;
                if (string.IsNullOrEmpty(original))
                {
                    continue;
                }

                string translated = Translator.TranslateUi(original);
                if (!ReferenceEquals(translated, original) && translated != original)
                {
                    label.text = translated;
                    replaced++;
                }
            }

            if (replaced > 0)
            {
                Plugin.Log.LogInfo($"화면 텍스트 {replaced}개를 번역으로 교체했습니다.");
            }
        }

        /// <summary>
        /// 프리팹에 구워진 텍스트는 코드가 세터를 부르지 않으므로 세터 패치로는 잡히지 않는다.
        /// 런타임에 새로 만들어지는 UI(팝업, 창)도 씬 스윕 시점에는 존재하지 않는다.
        /// 그래서 텍스트 컴포넌트가 켜지는 순간마다 자기 자신을 번역하게 한다.
        /// </summary>
        [HarmonyPostfix]
        [HarmonyPatch(typeof(TextMeshProUGUI), "OnEnable")]
        [HarmonyPatch(typeof(TextMeshPro), "OnEnable")]
        private static void OnEnablePostfix(TMP_Text __instance)
        {
            if (!Translator.HasUiText || __instance == null)
            {
                return;
            }

            string original = __instance.text;
            if (string.IsNullOrEmpty(original))
            {
                return;
            }

            string translated = Translator.TranslateUi(original);
            if (translated != original)
            {
                AllowShrinkToFit(__instance);
                __instance.text = translated;
                Report();
            }
        }

        private static int onEnableReplacements;

        /// <summary>교체 건수를 이따금 한 줄로 알린다. 매 건 찍으면 로그가 넘친다.</summary>
        private static void Report()
        {
            onEnableReplacements++;
            if (onEnableReplacements <= 3 || onEnableReplacements % 50 == 0)
            {
                Plugin.Log.LogInfo($"활성화 시점 번역 교체 누적 {onEnableReplacements}건");
            }
        }

        [HarmonyPrefix]
        [HarmonyPatch(typeof(TMP_Text), "text", MethodType.Setter)]
        private static void TextSetterPrefix(TMP_Text __instance, ref string value)
        {
            string translated = Translator.TranslateUi(value);
            if (!ReferenceEquals(translated, value) && translated != value)
            {
                AllowShrinkToFit(__instance);
            }

            value = translated;
        }

        /// <summary>
        /// 자리에 넘칠 때만 글자가 조금 작아지도록 한다.
        ///
        /// 한글은 같은 글꼴 크기에서 라틴 글자보다 세 배 가까이 넓다.
        /// 영문 기준으로 잡힌 상자에 번역문을 넣으면 줄이 늘어나고,
        /// 말풍선처럼 옆에 다른 요소가 붙어 있는 자리에서는 그것을 덮는다.
        ///
        /// 문장을 억지로 줄이면 말이 부자연스러워지므로, 넘치는 경우에 한해
        /// 글자를 줄여 담는다. TMP는 필요할 때만 줄이고 들어가면 원래 크기를 쓴다.
        /// </summary>
        private static void AllowShrinkToFit(TMP_Text label)
        {
            if (label == null || !Plugin.ShrinkTextToFit.Value || label.enableAutoSizing)
            {
                return;
            }

            float size = label.fontSize;
            if (size <= 0f)
            {
                return;
            }

            label.enableAutoSizing = true;
            label.fontSizeMax = size;
            label.fontSizeMin = size * Plugin.ShrinkFloor.Value;
        }

        [HarmonyPostfix]
        [HarmonyPatch(typeof(TextAsset), "text", MethodType.Getter)]
        private static void TextAssetGetterPostfix(ref string __result)
        {
            __result = Translator.TranslateAsset(__result);
        }
    }
}
