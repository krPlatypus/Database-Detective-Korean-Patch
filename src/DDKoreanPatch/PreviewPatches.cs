using System;
using System.IO;
using HarmonyLib;
using UnityEngine;

namespace DDKoreanPatch
{
    /// <summary>
    /// 아직 못 간 장의 화면을 미리 열어 번역을 확인하기 위한 장치.
    ///
    /// 번역은 게임 곳곳의 웹사이트와 대사에 걸쳐 있는데, 그 대부분은 뒷장에
    /// 나온다. 끝까지 플레이하지 않으면 번역이 화면에서 어떻게 보이는지,
    /// 특히 긴 글이 상자를 넘치지 않는지 확인할 길이 없다.
    ///
    /// 게임에는 이미 사건을 오가는 길이 있다. 조수에게 '시간 여행.'을 고르면
    /// 되는데, 목록이 Save.GetMaxLevelUnlocked()까지만 나온다. 그 값만 올려
    /// 주면 게임이 원래 하던 대로 사건을 오간다. 사건별 테이블도 게임이
    /// 알아서 갈무리한다.
    ///
    /// 켜 두는 동안에는 사건을 풀어도 진행도가 오르지 않는다. LevelManager가
    /// '현재 장이 열린 최대 장 이상이면 기록한다'로 판단하는데, 올려 둔 값
    /// 때문에 그 조건이 서지 않기 때문이다. 이것은 부작용이 아니라 노리는
    /// 바다. 미리 8장을 들여다본 것이 저장 파일에 진짜 진행으로 남으면
    /// 이야기를 건너뛴 셈이 되기 때문이다.
    ///
    /// 그래도 저장 파일은 건드리게 되므로, 켤 때 사본을 하나 떠 둔다.
    /// </summary>
    [HarmonyPatch]
    internal static class PreviewPatches
    {
        // Save.GetMaxLevelUnlocked가 스스로 9로 자른다. 그 위는 의미가 없다.
        private const int LastCase = 9;

        private const string BackupSuffix = ".backup";

        internal static void BackUpSave()
        {
            try
            {
                string path = Path.Combine(Application.persistentDataPath, "SQLGame.save");
                if (!File.Exists(path))
                {
                    Plugin.Log.LogInfo("저장 파일이 아직 없어 사본을 두지 않았습니다.");
                    return;
                }

                string backup = path + BackupSuffix;
                if (File.Exists(backup))
                {
                    Plugin.Log.LogInfo($"저장 파일 사본이 이미 있습니다: {backup}");
                    return;
                }

                File.Copy(path, backup);
                Plugin.Log.LogWarning($"미리보기를 켜서 저장 파일 사본을 떴습니다: {backup}");
            }
            catch (Exception e)
            {
                Plugin.Log.LogError("저장 파일 사본을 뜨지 못했습니다: " + e.Message);
            }
        }

        [HarmonyPostfix]
        [HarmonyPatch(typeof(Save), nameof(Save.GetMaxLevelUnlocked))]
        private static void GetMaxLevelUnlockedPostfix(ref int __result)
        {
            if (Plugin.PreviewAllChapters.Value)
            {
                __result = LastCase;
            }
        }
    }
}
