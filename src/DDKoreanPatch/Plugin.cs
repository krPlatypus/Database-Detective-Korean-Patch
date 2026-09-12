using BepInEx;
using BepInEx.Configuration;
using BepInEx.Logging;
using HarmonyLib;
using TMPro;
using UnityEngine;

namespace DDKoreanPatch
{
    /// <summary>
    /// Enter 키를 눌렀을 때 쿼리/메모장 입력 필드가 어떻게 반응할지.
    /// </summary>
    public enum EnterBehavior
    {
        /// <summary>Enter·Shift+Enter 모두 줄바꿈. 제출은 Ctrl+Enter (게임 원래 의도).</summary>
        Newline,

        /// <summary>Enter는 쿼리 제출, Shift+Enter는 줄바꿈 (SQL 콘솔 방식).</summary>
        Submit,
    }

    [BepInPlugin(PluginGuid, PluginName, PluginVersion)]
    public class Plugin : BaseUnityPlugin
    {
        public const string PluginGuid = "kr.spade.databasedetective.koreanpatch";
        public const string PluginName = "Database Detective Korean Patch";
        public const string PluginVersion = "0.1.0";

        internal static ManualLogSource Log;
        internal static ConfigEntry<EnterBehavior> EnterMode;
        internal static ConfigEntry<bool> Diagnostics;

        private void Awake()
        {
            Log = Logger;

            EnterMode = Config.Bind(
                "Input",
                "EnterBehavior",
                EnterBehavior.Newline,
                "쿼리창·메모장에서 Enter 키 동작.\n"
                + "Newline = Enter와 Shift+Enter 모두 줄바꿈, 제출은 Ctrl+Enter (기본값, 게임 원래 의도 복구)\n"
                + "Submit  = Enter는 쿼리 제출, Shift+Enter는 줄바꿈");

            Diagnostics = Config.Bind(
                "Debug",
                "VerboseInputLog",
                false,
                "입력 필드에 도달하는 키/문자를 로그로 남깁니다. 버그 원인 진단용.");

            new Harmony(PluginGuid).PatchAll(typeof(InputFieldPatches));

            Logger.LogInfo($"로드 완료. EnterBehavior={EnterMode.Value}, VerboseInputLog={Diagnostics.Value}");

            if (InputFieldPatches.ImeGuardPatched)
            {
                Logger.LogInfo("IME 가드 무력화 성공 - 단독 Enter가 KeyPressed까지 도달합니다.");
            }
            else
            {
                Logger.LogError(
                    "IME 가드를 찾지 못했습니다. TMP 버전이 예상과 다릅니다 - 단독 Enter가 계속 막힐 수 있습니다.");
            }
        }
    }
}
