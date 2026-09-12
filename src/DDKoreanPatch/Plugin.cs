using BepInEx;
using BepInEx.Configuration;
using BepInEx.Logging;
using HarmonyLib;

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
        public const string PluginVersion = "0.2.0";

        internal static ManualLogSource Log;

        internal static ConfigEntry<EnterBehavior> EnterMode;
        internal static ConfigEntry<bool> Diagnostics;

        internal static ConfigEntry<bool> EnableTranslation;
        internal static ConfigEntry<bool> ClosePopupWithKey;
        internal static ConfigEntry<bool> EnableClueImageToggle;
        internal static ConfigEntry<bool> EnableKoreanFont;
        internal static ConfigEntry<string> FontFamily;
        internal static ConfigEntry<string> FontStyle;
        internal static ConfigEntry<int> FontPointSize;

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

            EnableKoreanFont = Config.Bind(
                "Font",
                "EnableKoreanFont",
                true,
                "게임 폰트에 한글 폴백을 걸어 한글이 두부(□)로 보이지 않게 합니다.");

            FontFamily = Config.Bind(
                "Font",
                "FontFamily",
                "Malgun Gothic",
                "한글 글리프를 가져올 OS 폰트 이름. 예: Malgun Gothic(맑은 고딕), Gulim(굴림), Batang(바탕).\n"
                + "굴림은 게임의 Windows 95풍 UI와 잘 어울립니다.");

            FontStyle = Config.Bind(
                "Font",
                "FontStyle",
                "Regular",
                "폰트 스타일. 보통 Regular 또는 Bold.");

            FontPointSize = Config.Bind(
                "Font",
                "FontPointSize",
                90,
                "폰트 샘플링 크기. 키우면 선명해지지만 메모리를 더 씁니다.");

            EnableTranslation = Config.Bind(
                "Translation",
                "EnableTranslation",
                true,
                "translation.json의 한글 번역을 화면에 적용합니다.");

            ClosePopupWithKey = Config.Bind(
                "Input",
                "ClosePopupWithKey",
                true,
                "알림·오류 팝업을 Esc나 Enter로 닫습니다. 원래는 X 버튼으로만 닫힙니다.");

            EnableClueImageToggle = Config.Bind(
                "Translation",
                "EnableClueImageToggle",
                true,
                "사진 단서 창에 원본/번역본 전환 버튼을 답니다. "
                + "플러그인 폴더의 images/ 아래에 원본과 같은 이름으로 PNG를 두면 번역본으로 인식합니다. "
                + "번역본이 없는 단서에는 버튼이 나오지 않습니다.");

            string pluginDirectory = System.IO.Path.GetDirectoryName(Info.Location);

            Harmony harmony = new Harmony(PluginGuid);
            harmony.PatchAll(typeof(InputFieldPatches));
            harmony.PatchAll(typeof(PopupPatches));

            if (EnableClueImageToggle.Value)
            {
                TranslatedImages.Initialize(pluginDirectory);
                harmony.PatchAll(typeof(ClueImagePatches));
            }

            if (EnableTranslation.Value)
            {
                Translator.Load(pluginDirectory);
                harmony.PatchAll(typeof(TranslationPatches));
            }

            Logger.LogInfo($"로드 완료. EnterBehavior={EnterMode.Value}");
        }

        /// <summary>
        /// 폰트 설치는 첫 Update까지 미룬다.
        ///
        /// BepInEx는 플러그인을 Application의 정적 생성자 안에서 AddComponent로 붙인다.
        /// 그 시점에는 Unity 플레이어 루프가 아직 돌지 않아 Awake에서 StartCoroutine을
        /// 부르면 네이티브 크래시가 난다. Update는 정상적인 플레이어 루프에서 호출되므로
        /// 여기서 처리하는 것이 안전하고, TMP의 FontEngine도 이때는 초기화되어 있다.
        /// </summary>
        private void Update()
        {
            if (fontInstallAttempted)
            {
                return;
            }

            fontInstallAttempted = true;

            if (!EnableKoreanFont.Value)
            {
                return;
            }

            try
            {
                KoreanFont.Install();
            }
            catch (System.Exception e)
            {
                Logger.LogError($"한글 폰트 설치 실패: {e}");
            }

            if (EnableTranslation.Value)
            {
                try
                {
                    TranslationPatches.HookSceneSweep();
                }
                catch (System.Exception e)
                {
                    Logger.LogError($"번역 적용 실패: {e}");
                }
            }
        }

        private bool fontInstallAttempted;
    }
}
