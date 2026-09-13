using System.Linq;
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
        internal static ConfigEntry<bool> ShrinkTextToFit;
        internal static ConfigEntry<float> ShrinkFloor;
        internal static ConfigEntry<bool> FitAssistantBubble;

        internal static ConfigEntry<bool> PreviewAllChapters;

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
        internal static ConfigEntry<float> FontScale;
        internal static ConfigEntry<float> FontBaselineOffset;
        internal static ConfigEntry<bool> ModernHangulLineBreaking;

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

            FontScale = Config.Bind(
                "Font",
                "FontScale",
                0.95f,
                new ConfigDescription(
                    "한글 글자 크기 보정. 글꼴마다 네모칸 안에서 글자가 차지하는 비율이 달라, "
                    + "같은 크기를 줘도 한글이 영문보다 커 보입니다. 1보다 작게 두면 한글이 작아집니다. "
                    + "영문과 나란히 놓고 높이가 비슷해 보이는 값을 찾으세요. 글꼴을 바꾸면 다시 맞춰야 합니다.",
                    new AcceptableValueRange<float>(0.5f, 1.5f)));

            FontBaselineOffset = Config.Bind(
                "Font",
                "FontBaselineOffset",
                0.09f,
                new ConfigDescription(
                    "한글 세로 위치 보정. 양수면 위로 올라갑니다. 네모칸 높이 대비 비율입니다. "
                    + "영문과 한 줄에 섞였을 때 밑선이 어긋나 보이면 조정하세요. "
                    + "FontScale을 바꾸면 이 값도 다시 맞춰야 합니다.",
                    new AcceptableValueRange<float>(-0.5f, 0.5f)));

            ModernHangulLineBreaking = Config.Bind(
                "Font",
                "ModernHangulLineBreaking",
                true,
                "한글을 어절 단위로 끊습니다. 끄면 TMP가 한글을 중국어, 일본어처럼 보고 "
                + "글자 아무 데서나 줄을 끊어 단어 한가운데가 잘립니다.");

            EnableTranslation = Config.Bind(
                "Translation",
                "EnableTranslation",
                true,
                "translation.json의 한글 번역을 화면에 적용합니다.");

            ShrinkTextToFit = Config.Bind(
                "Translation",
                "ShrinkTextToFit",
                true,
                "번역문이 자리에 넘칠 때만 글자를 조금 줄여 담습니다. "
                + "한글은 같은 크기에서 라틴 글자보다 세 배 가까이 넓어, "
                + "영문 기준으로 잡힌 상자에서는 줄이 늘어나 옆 요소를 덮습니다. "
                + "끄면 원래 크기를 유지하되 넘칠 수 있습니다.");

            ShrinkFloor = Config.Bind(
                "Translation",
                "ShrinkFloor",
                0.72f,
                new ConfigDescription(
                    "글자를 줄일 수 있는 최소 비율. 0.72면 원래 크기의 72%까지만 줄입니다. "
                    + "너무 낮게 두면 읽기 어려워집니다.",
                    new AcceptableValueRange<float>(0.4f, 1f)));

            FitAssistantBubble = Config.Bind(
                "Translation",
                "FitAssistantBubble",
                true,
                "조수 말풍선의 크기를 번역문의 실제 너비에 맞춰 다시 잡습니다. "
                + "게임은 말풍선을 글자 수로 재는데, 한글은 라틴 글자보다 넓어 "
                + "상자가 좁게 잡히고 글자가 잘리거나 질문 버튼과 겹칩니다.");

            PreviewAllChapters = Config.Bind(
                "Preview",
                "PreviewAllChapters",
                false,
                "번역 확인용입니다. 조수에게 '시간 여행.'을 고르면 나오는 사건 목록에 "
                + "모든 사건이 뜨게 해, 아직 못 간 장의 화면을 미리 볼 수 있습니다. "
                + "켜 두는 동안에는 사건을 풀어도 진행도가 오르지 않습니다. "
                + "미리 본 것이 진짜 진행으로 남지 않게 하려는 것이니, "
                + "확인이 끝나면 다시 꺼 주세요. 켤 때 저장 파일 사본을 "
                + "SQLGame.save.backup으로 떠 둡니다.");

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

            if (PreviewAllChapters.Value)
            {
                PreviewPatches.BackUpSave();
                harmony.PatchAll(typeof(PreviewPatches));
            }

            if (EnableTypingSound.Value)
            {
                harmony.PatchAll(typeof(TypingSoundPatches));
            }

            if (EnableClueImageToggle.Value)
            {
                TranslatedImages.Initialize(PluginDirectory);
                harmony.PatchAll(typeof(ClueImagePatches));
                harmony.PatchAll(typeof(ManualPatches));
                harmony.PatchAll(typeof(CursorPatches));
            }

            if (EnableTranslation.Value)
            {
                Translator.Load(PluginDirectory);
                harmony.PatchAll(typeof(TranslationPatches));
                harmony.PatchAll(typeof(AssistantDialoguePatches));
            }

            // 패치 클래스는 위에서 하나씩 등록한다. 새 클래스를 만들고 등록을
            // 빠뜨리면 아무 일도 일어나지 않고 오류도 남지 않으므로, 실제로
            // 몇 개를 갈아 끼웠는지 남겨 둔다.
            int patched = harmony.GetPatchedMethods().Count();
            Logger.LogInfo($"로드 완료. 메서드 {patched}개 패치. EnterBehavior={EnterMode.Value}");
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
