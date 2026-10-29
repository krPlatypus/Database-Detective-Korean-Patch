using HarmonyLib;

namespace DDKoreanPatch
{
    /// <summary>
    /// 첫 메시지를 들은 뒤 튜토리얼 도중 종료한 저장에서 조수 안내를 재개한다.
    /// </summary>
    [HarmonyPatch]
    internal static class AssistantStartupPatches
    {
        [HarmonyPostfix]
        [HarmonyPatch(typeof(CreateTables), nameof(CreateTables.PlayIntroCall))]
        private static void PlayIntroCallPostfix(ref bool __result)
        {
            // 원본은 튜토리얼이 미완료면 메시지 알림부터 다시 띄운다.
            // 하지만 TutorialSpawner는 0Messages 기록이 있으면 조수를 부르지 않는다.
            // 이미 들은 메시지는 건너뛰어 CreateTables.Awake의 기존 튜토리얼
            // 분기로 진입한다. 조수 끄기 설정과 튜토리얼 완료 여부는 원본이 처리한다.
            if (__result && Save.HasPlayedIntro() && Save.IsIconClicked("0Messages"))
            {
                __result = false;
                Plugin.Log.LogInfo("첫 메시지 이후 중단된 조수 튜토리얼을 재개합니다.");
            }
        }
    }
}
