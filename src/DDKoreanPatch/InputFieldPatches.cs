using HarmonyLib;
using TMPro;
using UnityEngine;
using UnityEngine.EventSystems;

namespace DDKoreanPatch
{
    /// <summary>
    /// 쿼리창·메모장에서 Enter/Shift+Enter가 줄바꿈되지 않던 문제 수정.
    ///
    /// 주 원인: TMP_InputField.OnSubmit이 lineType을 보지 않는다.
    ///
    ///     public virtual void OnSubmit(BaseEventData eventData)
    ///     {
    ///         if (IsActive() &amp;&amp; IsInteractable())
    ///         {
    ///             if (!isFocused) m_ShouldActivateNextUpdate = true;
    ///             SendOnSubmit();
    ///             DeactivateInputField();   // 여러 줄 필드인데도 포커스를 뺀다
    ///             eventData?.Use();
    ///         }
    ///     }
    ///
    /// EventSystem이 Enter를 submit으로 잡아 이 핸들러를 먼저 호출하므로 필드가 비활성화되고,
    /// 그 뒤 OnUpdateSelected가 "if (!isFocused) return;"에서 빠져나가
    /// Return 이벤트가 큐에서 꺼내지지도 않는다. 그래서 줄바꿈이 되지 않고 캐럿만 사라졌다.
    /// 이 필드들은 m_OnSubmit에 리스너가 없어 SendOnSubmit()도 아무 일을 하지 않는다.
    ///
    /// 부차 원인: Shift+Enter는 KeyPressed에서 '\v'(수직 탭)로 바뀌는데
    /// IsValidChar의 "c &lt; ' '" 검사에 걸려 Append까지 도달하지 못한다.
    /// 게임쪽 QueryInputUtils.ValidateInput의 ILLEGAL_CHARS에도 '\r', '\v'가 들어 있다.
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
        /// 여러 줄 입력 필드에서는 EventSystem의 submit을 무시한다.
        /// 포커스가 유지되어야 Return 이벤트가 OnUpdateSelected까지 흘러가 줄바꿈이 된다.
        ///
        /// Submit 모드의 쿼리 제출은 AppendPrefix 한 곳에서만 처리한다.
        /// 여기서도 제출하면 두 번 제출된다.
        /// </summary>
        [HarmonyPrefix]
        [HarmonyPatch(typeof(TMP_InputField), "OnSubmit")]
        private static bool OnSubmitPrefix(TMP_InputField __instance, BaseEventData eventData)
        {
            if (!IsMultiline(__instance))
            {
                return true;
            }

            if (Plugin.Diagnostics.Value)
            {
                Plugin.Log.LogInfo($"[OnSubmit] field={__instance.name} - 여러 줄 필드이므로 무시");
            }

            return false;
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
        /// '\n'은 IsValidChar와 게임쪽 ILLEGAL_CHARS를 모두 통과한다.
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
        /// 진단용. 입력 필드에 도달하는 키 이벤트를 전부 기록한다.
        /// </summary>
        [HarmonyPrefix]
        [HarmonyPatch(typeof(TMP_InputField), "KeyPressed")]
        private static void KeyPressedPrefix(TMP_InputField __instance, Event evt)
        {
            if (!Plugin.Diagnostics.Value || evt == null)
            {
                return;
            }

            Plugin.Log.LogInfo(
                $"[KeyPressed] field={__instance.name} keyCode={evt.keyCode} " +
                $"char=0x{(int)evt.character:X2} mods={evt.modifiers} " +
                $"lineType={__instance.lineType} len={__instance.text.Length}/{__instance.characterLimit}");
        }
    }
}
