using HarmonyLib;
using TMPro;
using UnityEngine;

namespace DDKoreanPatch
{
    /// <summary>
    /// 쿼리창·메모장의 줄바꿈 입력 복구.
    ///
    /// 원인:
    ///  - Shift+Enter는 TMP_InputField.KeyPressed 안에서 '\v'(수직 탭)로 변환되는데,
    ///    IsValidChar가 "c &lt; ' '"에 걸어 거부하므로 Append까지 도달하지 못한다.
    ///  - 게임쪽 QueryInputUtils.ValidateInput의 ILLEGAL_CHARS에도 '\r', '\v'가 들어 있어
    ///    Append에 도달하더라도 한 번 더 차단된다.
    ///
    /// 두 경우 모두 문자가 Append에 닿기 전/직후에 '\n'으로 정규화하면 해결된다.
    /// '\n'은 IsValidChar와 ILLEGAL_CHARS 양쪽을 모두 통과한다.
    /// </summary>
    [HarmonyPatch]
    internal static class InputFieldPatches
    {
        private const char CarriageReturn = '\r';
        private const char VerticalTab = '\v';   // TMP가 Shift+Enter에 부여하는 문자
        private const char LineFeed = '\n';

        private static bool IsMultiline(TMP_InputField field)
        {
            return field != null && field.lineType == TMP_InputField.LineType.MultiLineNewline;
        }

        /// <summary>
        /// '\v'가 Append까지 도달하도록 허용한다. 실제 삽입은 AppendPrefix에서 '\n'으로 바뀐다.
        /// 여러 줄 입력 필드에만 적용해 한 줄짜리 필드의 동작은 건드리지 않는다.
        /// </summary>
        [HarmonyPostfix]
        [HarmonyPatch(typeof(TMP_InputField), "IsValidChar")]
        private static void IsValidCharPostfix(TMP_InputField __instance, char c, ref bool __result)
        {
            if (!__result && c == VerticalTab && IsMultiline(__instance))
            {
                __result = true;
            }
        }

        /// <summary>
        /// Append에 도달한 줄바꿈 계열 문자를 '\n'으로 정규화한다.
        /// Submit 모드에서는 단독 Enter를 쿼리 제출로 돌린다 (Shift+Enter는 항상 줄바꿈).
        /// </summary>
        [HarmonyPrefix]
        [HarmonyPatch(typeof(TMP_InputField), "Append", typeof(char))]
        private static bool AppendPrefix(TMP_InputField __instance, ref char input)
        {
            if (!IsMultiline(__instance))
            {
                return true;
            }

            bool isShiftEnter = input == VerticalTab;
            bool isPlainEnter = input == CarriageReturn || input == LineFeed;

            if (!isShiftEnter && !isPlainEnter)
            {
                return true;
            }

            if (Plugin.Diagnostics.Value)
            {
                Plugin.Log.LogInfo(
                    $"[Append] field={__instance.name} char=0x{(int)input:X2} " +
                    $"shiftEnter={isShiftEnter} mode={Plugin.EnterMode.Value}");
            }

            if (isPlainEnter && Plugin.EnterMode.Value == EnterBehavior.Submit)
            {
                QueryButton button = __instance.GetComponentInParent<QueryButton>();
                if (button != null)
                {
                    button.QueryButtonPressed();
                    return false;   // 제출했으므로 줄바꿈은 넣지 않는다
                }
                // 메모장 등 쿼리 버튼이 없는 필드는 그대로 줄바꿈시킨다
            }

            input = LineFeed;
            return true;
        }

        /// <summary>
        /// 진단용. Enter 계열 입력이 TMP에 실제로 어떤 형태로 도달하는지 기록한다.
        /// </summary>
        [HarmonyPrefix]
        [HarmonyPatch(typeof(TMP_InputField), "KeyPressed")]
        private static void KeyPressedPrefix(TMP_InputField __instance, Event evt)
        {
            if (!Plugin.Diagnostics.Value || evt == null)
            {
                return;
            }

            bool enterish = evt.keyCode == KeyCode.Return
                            || evt.keyCode == KeyCode.KeypadEnter
                            || evt.character == CarriageReturn
                            || evt.character == LineFeed
                            || evt.character == VerticalTab;

            if (!enterish)
            {
                return;
            }

            TMP_TextInfo info = __instance.textComponent != null ? __instance.textComponent.textInfo : null;
            Plugin.Log.LogInfo(
                $"[KeyPressed] field={__instance.name} keyCode={evt.keyCode} char=0x{(int)evt.character:X2} " +
                $"mods={evt.modifiers} lineType={__instance.lineType} " +
                $"lineLimit={__instance.lineLimit} lineCount={(info != null ? info.lineCount : -1)} " +
                $"len={__instance.text.Length}/{__instance.characterLimit}");
        }
    }
}
