using System;
using HarmonyLib;
using TMPro;
using UnityEngine;

namespace DDKoreanPatch
{
    /// <summary>
    /// 조수 말풍선의 크기를 번역문의 실제 너비에 맞춘다.
    ///
    /// AssistantDialogue.Resize는 말풍선을 글자 수로 잰다. 가로는 가장 긴 줄의
    /// 글자 수 x 15px, 세로는 줄바꿈 문자로 센 줄 수 x 30px이다. 라틴 글자
    /// 기준이라 한글에는 맞지 않는다. 한글은 같은 크기에서 두 배 넘게 넓어
    /// 상자는 좁게 잡히고, TMP가 알아서 줄을 접는다. 접힌 줄은 원본이 센
    /// 줄 수에 들어가지 않으므로 상자 높이가 모자라고, 그 아래 질문 버튼도
    /// 원래 줄 수만큼만 내려와 본문 마지막 줄을 덮는다.
    ///
    /// 글자 수 대신 TMP에게 직접 물어 다시 잰다. 원본이 세로를
    /// '줄 수 x 30px'로 잡았으니, 잰 높이를 같은 자리에 넣으면 나머지
    /// 계산(아이콘, 버튼 높이)은 원본 그대로 둘 수 있다.
    ///
    /// 원문 그대로인 말풍선은 건드리지 않는다. 원본 계산이 라틴 글자에는
    /// 맞게 되어 있고, 값을 다시 잡아 봐야 얻을 것이 없다.
    /// </summary>
    [HarmonyPatch]
    internal static class AssistantDialoguePatches
    {
        /// <summary>
        /// 잴 때 주는 여유 치수.
        ///
        /// TMP는 이 값이 0이면 "그 안에 넣으라"는 뜻으로 받아들인다. 가로 0을
        /// 주면 글자마다 줄을 접어 가장 넓은 글자 하나의 너비를 돌려주고,
        /// 세로 0을 주면 자동 크기 조절이 켜진 글상자를 최소 크기까지 줄인다.
        /// 재려던 값이 아니므로, 제한하지 않을 축에는 이 큰 값을 준다.
        /// </summary>
        private const float Unbounded = 32767f;

        // AssistantDialogue의 private static 상수들. 원본 계산을 그대로 잇기 위해 읽어 둔다.
        private static bool constantsRead;
        private static float minWidth = 300f;
        private static float maxWidth = 480f;
        private static float defaultHeight = 110f;
        private static float lineHeight = 30f;
        private static float iconHeight = 90f;
        private static float helpButtonHeight = 38f;
        private static float questionsY = -75f;

        [HarmonyPostfix]
        [HarmonyPatch(typeof(AssistantDialogue), "Resize")]
        private static void ResizePostfix(AssistantDialogue __instance)
        {
            if (!Plugin.FitAssistantBubble.Value)
            {
                return;
            }

            try
            {
                Refit(__instance);
            }
            catch (Exception e)
            {
                Plugin.Log.LogWarning("말풍선 크기를 다시 잡지 못했다: " + e.Message);
            }
        }

        private static void Refit(AssistantDialogue dialogue)
        {
            Traverse box = Traverse.Create(dialogue);
            TextMeshProUGUI label = box.Field("dialogueText").GetValue<TextMeshProUGUI>();
            RectTransform bubble = box.Field("bubble").GetValue<RectTransform>();
            GameObject prompts = box.Field("questionPrompts").GetValue<GameObject>();
            if (label == null || bubble == null || prompts == null)
            {
                return;
            }

            string text = label.text;
            if (!TranslationPatches.ContainsHangul(text))
            {
                return;
            }

            ReadConstants();

            bool promptsDisabled = box.Field("promptsDisabled").GetValue<bool>();
            bool iconDisplayed = box.Field("isIconDisplayed").GetValue<bool>();
            int buttonCount = box.Field("questionButtonCount").GetValue<int>();

            float pad = Padding(bubble, label);

            // 재는 동안에는 자동 크기 조절을 끈다. 켜 두면 TMP가 주어진 자리에
            // 맞추려고 글자를 줄인 결과를 돌려줘, 원래 크기로는 얼마가 필요한지
            // 알 수 없다. 알아야 하는 건 줄이기 전의 치수다.
            bool autoSizing = label.enableAutoSizing;
            label.enableAutoSizing = false;
            float natural, height;
            try
            {
                // 가로: 줄을 접지 않았을 때 가장 넓은 줄. 원본과 같은 범위에 가둔다.
                natural = label.GetPreferredValues(Unbounded, Unbounded).x;
                float width = Mathf.Clamp(natural + pad, minWidth, maxWidth);
                bubble.SetSizeWithCurrentAnchors(
                    RectTransform.Axis.Horizontal, width + (promptsDisabled ? -80f : 0f));

                // 세로: 그 너비로 접었을 때 실제로 차지하는 높이.
                height = label.GetPreferredValues(width - pad, Unbounded).y;
            }
            finally
            {
                label.enableAutoSizing = autoSizing;
            }

            height = Mathf.Max(height, lineHeight);

            bubble.SetSizeWithCurrentAnchors(RectTransform.Axis.Vertical,
                defaultHeight
                + height
                + (promptsDisabled ? -lineHeight : 0f)
                + (iconDisplayed ? iconHeight : 0f)
                + (prompts.activeSelf ? buttonCount * helpButtonHeight : 0f));

            RectTransform promptBox = prompts.GetComponent<RectTransform>();
            promptBox.anchoredPosition =
                new Vector2(promptBox.anchoredPosition.x, questionsY - height);
        }

        /// <summary>
        /// 말풍선 너비에서 글자가 쓸 수 없는 부분.
        ///
        /// 글상자가 말풍선에 가로로 붙어 늘어나는 경우에는 좌우 여백이 그대로
        /// 답이고, 이 값은 크기가 바뀌어도 변하지 않는다. Resize가 방금 말풍선을
        /// 늘렸어도 자식 사각형은 다음 레이아웃까지 옛 값을 들고 있으므로,
        /// 두 사각형의 차이를 재는 것보다 이쪽이 믿을 만하다.
        /// </summary>
        private static float Padding(RectTransform bubble, TMP_Text label)
        {
            RectTransform rect = label.rectTransform;
            if (rect.anchorMin.x == 0f && rect.anchorMax.x == 1f)
            {
                return Mathf.Max(0f, rect.offsetMin.x - rect.offsetMax.x);
            }

            return Mathf.Max(0f, bubble.rect.width - rect.rect.width);
        }

        private static void ReadConstants()
        {
            if (constantsRead)
            {
                return;
            }

            constantsRead = true;
            Read("MIN_WIDTH", ref minWidth);
            Read("MAX_WIDTH", ref maxWidth);
            Read("DEFAULT_HEIGHT", ref defaultHeight);
            Read("TEXT_LINE_HEIGHT", ref lineHeight);
            Read("ICON_HEIGHT", ref iconHeight);
            Read("HELP_BUTTON_HEIGHT", ref helpButtonHeight);
            Read("DEFAULT_QUESTIONS_Y_AXIS", ref questionsY);
        }

        private static void Read(string name, ref float target)
        {
            Traverse field = Traverse.Create(typeof(AssistantDialogue)).Field(name);
            if (field.FieldExists())
            {
                target = field.GetValue<int>();
            }
        }
    }
}
