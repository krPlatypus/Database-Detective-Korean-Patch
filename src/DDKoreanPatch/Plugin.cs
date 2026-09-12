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
        internal static string PluginDirectory;

        internal static ConfigEntry<EnterBehavior> EnterMode;
        internal static ConfigEntry<bool> Diagnostics;

        internal static ConfigEntry<bool> EnableTranslation;
        internal static ConfigEntry<bool> ClosePopupWithKey;
        internal static ConfigEntry<bool> EnableTypingSound;
        internal static ConfigEntry<float> TypingVolume;
        internal static ConfigEntry<string> TypingClip;
        internal static ConfigEntry<bool> EnableClueImageToggle;
        internal static ConfigEntry<bool> EnableKoreanFont;
        internal static ConfigEntry<string> FontFamily;
        internal static ConfigEntry<string> FontStyle;
        internal static ConfigEntry<int> FontPointSize;
        internal static ConfigEntry<string> FontFile;
        internal static ConfigEntry<int> FontAtlasPadding;

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
                64,
                "폰트 샘플링 크기. 키우면 선명해지지만 메모리를 더 씁니다. "
                + "픽셀 글꼴은 원래 크기의 배수로 두어야 계단이 고르게 나옵니다(neodgm은 16의 배수).");

            FontFile = Config.Bind(
                "Font",
                "FontFile",
                "neodgm.ttf",
                "플러그인의 fonts/ 폴더에 있는 폰트 파일 이름. 있으면 FontFamily보다 먼저 씁니다. "
                + "기본값 neodgm.ttf(Neo둥근모)는 옛 윈도우의 각진 한글 느낌을 내는 픽셀 글꼴입니다. "
                + "비워 두면 OS에 설치된 FontFamily 폰트를 씁니다.");

            FontAtlasPadding = Config.Bind(
                "Font",
                "FontAtlasPadding",
                4,
                "글자 외곽에 두는 여백. 픽셀 글꼴은 작게 둘수록 모서리가 덜 뭉갭니다. 보통 글꼴은 9가 무난합니다.");

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

            PluginDirectory = System.IO.Path.GetDirectoryName(Info.Location);

            EnableTypingSound = Config.Bind(
                "Sound",
                "EnableTypingSound",
                true,
                "글자를 칠 때마다 짧은 타건음을 냅니다. 게임에 이미 들어 있는 클릭 소리를 빌려 씁니다.");

            TypingVolume = Config.Bind(
                "Sound",
                "TypingVolume",
                0.22f,
                new ConfigDescription(
                    "타건음 크기. 거슬리지 않을 만큼 작게 두는 것이 기본값입니다. "
                    + "게임 설정의 효과음 볼륨도 함께 적용됩니다.",
                    new AcceptableValueRange<float>(0f, 1f)));

            TypingClip = Config.Bind(
                "Sound",
                "TypingClip",
                "click down",
                "타건음으로 쓸 게임 내 소리 이름. 기본값은 0.08초짜리 짧고 마른 소리입니다. "
                + "다른 후보: click down 2, pen down 1, mouse-click-290204, button-press-382713. "
                + "이름에 pop이나 bubble이 들어간 소리는 뽀잉 하고 튀어서 타건음에 맞지 않습니다.");

            Harmony harmony = new Harmony(PluginGuid);
            harmony.PatchAll(typeof(InputFieldPatches));
            harmony.PatchAll(typeof(PopupPatches));

            if (EnableTypingSound.Value)
            {
                harmony.PatchAll(typeof(TypingSoundPatches));
            }

            if (EnableClueImageToggle.Value)
            {
                TranslatedImages.Initialize(PluginDirectory);
                harmony.PatchAll(typeof(ClueImagePatches));
            }

            if (EnableTranslation.Value)
            {
                Translator.Load(PluginDirectory);
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
                KoreanFont.Install(PluginDirectory);
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

            // sounds/ 폴더의 음원 읽기는 시간이 걸려 코루틴으로 돌린다.
            // Awake가 아니라 여기서 시작해야 한다. BepInEx가 플러그인을 붙이는 시점에는
            // 플레이어 루프가 아직 돌지 않아 StartCoroutine이 네이티브 크래시를 낸다.
            if (EnableTypingSound.Value)
            {
                try
                {
                    StartCoroutine(TypingSound.LoadExternal(PluginDirectory));
                }
                catch (System.Exception e)
                {
                    Logger.LogError($"타자음 음원 읽기 실패: {e}");
                }
            }
        }

        private bool fontInstallAttempted;
    }
}
