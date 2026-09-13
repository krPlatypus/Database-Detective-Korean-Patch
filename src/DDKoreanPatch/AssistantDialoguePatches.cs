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
    /// 줄 수에 들어가지 않으므로 상자 높이가 모자라 글자가 잘리고, 그 아래
    /// 질문 버튼은 원래 줄 수만큼만 내려와 글자와 겹친다.
    ///
    /// 글자 수 대신 TMP에게 직접 물어 다시 잰다. GetPreferredValues는 렌더링에
    /// 쓰는 그 글꼴로 재므로 한글 대체 글꼴과 크기 보정까지 그대로 반영된다.
    /// 원본이 세로를 '줄 수 x 30px'로 잡았으니, 잰 높이를 같은 자리에 넣으면
    /// 나머지 계산(아이콘, 버튼 높이)은 원본 그대로 둘 수 있다.
    ///
    /// 원문 그대로인 말풍선은 건드리지 않는다. 원본 계산이 라틴 글자에는
    /// 맞게 되어 있고, 값을 다시 잡아 봐야 얻을 것이 없다.
    /// </summary>
    [HarmonyPatch]
    internal static class AssistantDialoguePatches
    {
        // AssistantDialogue의 private static 상수들. 원본 계산을 그대로 잇기 위해 읽어 둔다.
        private static bool constantsRead;
        private static float minWidth = 300f;
        private static float maxWidth = 480f;
        private static float defaultHeight = 110f;
        private static float lineHeight = 30f;
        private static float iconHeight = 90f;
        private static float helpButtonHeight = 38f;
        private static float questionsY = -75f;

        // 말풍선 너비에서 글자가 쓸 수 없는 부분(테두리, 여백).
        // 첫 호출 때 실제 두 사각형의 차이로 알아내고, 값이 수상하면 이 기본값을 쓴다.
        private const float FallbackPadding = 40f;
        private static float padding = -1f;

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

            // 가로: 줄바꿈 없이 가장 넓은 줄에 맞춘다. 원본과 같은 범위 안에 가둔다.
            float widest = 0f;
            foreach (string line in text.Split('\n'))
            {
                widest = Mathf.Max(widest, label.GetPreferredValues(line, 0f, 0f).x);
            }

            float pad = Padding(bubble, label);
            float width = Mathf.Clamp(widest + pad, minWidth, maxWidth);
            bubble.SetSizeWithCurrentAnchors(
                RectTransform.Axis.Horizontal, width + (promptsDisabled ? -80f : 0f));

            // 세로: 그 너비에서 실제로 차지하는 높이를 TMP에게 묻는다.
            // 원본의 '줄 수 x 줄 높이' 자리에 이 값을 그대로 넣는다.
            float textHeight = label.GetPreferredValues(text, width - pad, 0f).y;
            textHeight = Mathf.Max(textHeight, lineHeight);

            bubble.SetSizeWithCurrentAnchors(RectTransform.Axis.Vertical,
                defaultHeight
                + textHeight
                + (promptsDisabled ? -lineHeight : 0f)
                + (iconDisplayed ? iconHeight : 0f)
                + (prompts.activeSelf ? buttonCount * helpButtonHeight : 0f));

            RectTransform promptBox = prompts.GetComponent<RectTransform>();
            promptBox.anchoredPosition =
                new Vector2(promptBox.anchoredPosition.x, questionsY - textHeight);
        }

        /// <summary>
        /// 말풍선 너비에서 글자 영역을 뺀 나머지.
        ///
        /// Resize가 방금 말풍선 크기를 바꿨어도 자식 사각형은 다음 레이아웃까지
        /// 옛 값을 들고 있을 수 있다. 그래서 한 번 그럴듯한 값이 나오면 붙잡아 둔다.
        /// </summary>
        private static float Padding(RectTransform bubble, TMP_Text label)
        {
            if (padding >= 0f)
            {
                return padding;
            }

            float gap = bubble.rect.width - label.rectTransform.rect.width;
            if (gap > 0f && gap < 200f)
            {
                padding = gap;
                return padding;
            }

            return FallbackPadding;
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
