using System.Collections.Generic;
using System.Reflection;
using System.Reflection.Emit;
using HarmonyLib;
using TMPro;
using UnityEngine;

namespace DDKoreanPatch
{
    /// <summary>
    /// 쿼리창·메모장의 줄바꿈 입력 복구.
    ///
    /// 1) 단독 Enter가 아예 먹히지 않는 문제 (주 원인)
    ///    TMP_InputField.OnUpdateSelected에 IME 가드가 있다.
    ///
    ///        if (m_IsCompositionActive && compositionLength == 0
    ///            && evt.character == '\0' && evt.modifiers == EventModifiers.None)
    ///            continue;   // KeyPressed 호출 자체를 건너뜀
    ///
    ///    한국어 IME가 올라와 있으면 m_IsCompositionActive가 참이 되고,
    ///    단독 Enter는 modifiers == None이라 네 조건이 모두 맞아 통째로 버려진다.
    ///    Ctrl+Enter는 modifiers == Control이라 빠져나가므로 제출만 동작했다.
    ///
    /// 2) Shift+Enter가 줄바꿈되지 않는 문제
    ///    KeyPressed가 Shift+Enter를 '\v'(수직 탭)로 바꾸는데
    ///    IsValidChar의 "c &lt; ' '" 검사에 걸려 Append까지 가지 못한다.
    ///    게임쪽 QueryInputUtils.ValidateInput의 ILLEGAL_CHARS에도 '\r', '\v'가 있다.
    /// </summary>
    [HarmonyPatch]
    internal static class InputFieldPatches
    {
        private const char CarriageReturn = '\r';
        private const char VerticalTab = '\v';   // TMP가 Shift+Enter에 부여하는 문자
        private const char LineFeed = '\n';

        /// <summary>Transpiler가 실제로 가드를 찾아 고쳤는지. Awake에서 확인용.</summary>
        internal static bool ImeGuardPatched;

        private static bool IsMultiline(TMP_InputField field)
        {
            return field != null && field.lineType == TMP_InputField.LineType.MultiLineNewline;
        }

        /// <summary>
        /// IME 가드의 m_IsCompositionActive 읽기를 상수 false로 바꿔 가드를 무력화한다.
        ///
        /// 이 메서드 안에는 m_IsCompositionActive 읽기가 두 군데 있다.
        /// 첫 번째가 문제의 가드이고, 두 번째(flag || (m_IsCompositionActive &amp;&amp; compositionLength &gt; 0))는
        /// 조합 중 라벨 갱신에 필요하므로 건드리지 않는다.
        ///
        /// 가드에는 compositionLength == 0 조건이 함께 걸려 있으므로,
        /// 실제로 조합이 진행 중일 때(length &gt; 0)의 동작은 원래도 이 가드를 타지 않았다.
        /// 따라서 바뀌는 범위는 "조합 세션은 열려 있으나 조합 중인 글자가 없고,
        /// 문자 없는 키를 수정자 없이 누른" 경우 뿐이다. 정확히 지금 깨진 경우다.
        /// </summary>
        [HarmonyTranspiler]
        [HarmonyPatch(typeof(TMP_InputField), "OnUpdateSelected")]
        private static IEnumerable<CodeInstruction> OnUpdateSelectedTranspiler(
            IEnumerable<CodeInstruction> instructions)
        {
            FieldInfo compositionActive =
                AccessTools.Field(typeof(TMP_InputField), "m_IsCompositionActive");

            List<CodeInstruction> result = new List<CodeInstruction>();
            bool done = false;

            foreach (CodeInstruction instruction in instructions)
            {
                if (!done
                    && instruction.opcode == OpCodes.Ldfld
                    && ReferenceEquals(instruction.operand, compositionActive))
                {
                    // 스택에 올라와 있는 this를 버리고 false를 대신 올린다.
                    // 명령을 제자리에서 바꾸므로 분기 라벨과 예외 블록은 그대로 유지된다.
                    instruction.opcode = OpCodes.Pop;
                    instruction.operand = null;
                    result.Add(instruction);
                    result.Add(new CodeInstruction(OpCodes.Ldc_I4_0));
                    done = true;
                    continue;
                }

                result.Add(instruction);
            }

            ImeGuardPatched = done;
            return result;
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

        /// <summary>
        /// 진단용. IME 조합 상태가 바뀔 때만 기록한다 (매 프레임 호출되므로).
        /// </summary>
        [HarmonyPrefix]
        [HarmonyPatch(typeof(TMP_InputField), "OnUpdateSelected")]
        private static void OnUpdateSelectedPrefix(TMP_InputField __instance)
        {
            if (!Plugin.Diagnostics.Value)
            {
                return;
            }

            bool active = (bool)AccessTools
                .Field(typeof(TMP_InputField), "m_IsCompositionActive")
                .GetValue(__instance);
            int length = (int)AccessTools
                .Property(typeof(TMP_InputField), "compositionLength")
                .GetValue(__instance, null);

            string state = $"{__instance.name}|{active}|{length}";
            if (state == lastCompositionState)
            {
                return;
            }

            lastCompositionState = state;
            Plugin.Log.LogInfo(
                $"[IME] field={__instance.name} compositionActive={active} compositionLength={length}");
        }

        private static string lastCompositionState;
    }
}
