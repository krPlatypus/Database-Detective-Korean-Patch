using System.Collections.Generic;
using System.Reflection;
using System.Reflection.Emit;
using HarmonyLib;

namespace DDKoreanPatch
{
    /// <summary>
    /// 원본은 화면에 표시된 메시지 제목으로 음악과 마지막 사건의 진행을 판정한다.
    /// 제목은 번역하되 이 두 메서드의 비교는 원문과 번역문을 모두 인정한다.
    /// MessageSpawner의 원문 제목/리소스 경로는 바꾸지 않는다.
    /// </summary>
    [HarmonyPatch]
    internal static class MessageTitlePatches
    {
        internal static bool MatchesTitle(string displayed, string source)
        {
            return displayed == source || displayed == Translator.TranslateUi(source);
        }

        [HarmonyTargetMethods]
        private static IEnumerable<MethodBase> TargetMethods()
        {
            yield return typeof(AudioMessageManager).GetMethod(nameof(AudioMessageManager.PlayAudio));
            yield return typeof(AudioMessageManager).GetMethod("StopAudioAction",
                BindingFlags.Instance | BindingFlags.NonPublic);
        }

        [HarmonyTranspiler]
        private static IEnumerable<CodeInstruction> CompareTitles(IEnumerable<CodeInstruction> instructions)
        {
            var equality = typeof(string).GetMethod("op_Equality");
            var matches = typeof(MessageTitlePatches).GetMethod(nameof(MatchesTitle),
                BindingFlags.Static | BindingFlags.NonPublic);
            foreach (CodeInstruction instruction in instructions)
            {
                if (instruction.opcode == OpCodes.Call && Equals(instruction.operand, equality))
                {
                    instruction.operand = matches;
                }
                yield return instruction;
            }
        }
    }
}
