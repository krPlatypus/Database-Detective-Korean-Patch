using HarmonyLib;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

namespace DDKoreanPatch
{
    /// <summary>
    /// 사진 단서 창에 원본/번역본 전환 버튼을 붙인다.
    ///
    /// 단서 이미지에 박힌 글자 중 이름, ID 번호, 날짜, 주소 같은 값은
    /// 플레이어가 그대로 SQL에 적어 넣는 데이터다. 번역본에서 그 값이 한 글자라도
    /// 어긋나면 사건을 풀 수 없게 된다. 원본을 항상 한 번의 클릭 거리에 두어
    /// 그 위험을 없앤다.
    ///
    /// CluePopup.SetImage가 모든 사진 단서가 지나는 길목이라 여기 한 곳만 잡는다.
    /// </summary>
    [HarmonyPatch]
    internal static class ClueImagePatches
    {
        [HarmonyPostfix]
        [HarmonyPatch(typeof(CluePopup), nameof(CluePopup.SetImage))]
        private static void SetImagePostfix(CluePopup __instance, Sprite image)
        {
            if (!Plugin.EnableClueImageToggle.Value || __instance == null || image == null)
            {
                return;
            }

            Sprite translated = TranslatedImages.Get(image.name);
            if (translated == null)
            {
                return;   // 번역본이 없는 단서는 버튼도 만들지 않는다
            }

            Transform imageTransform = __instance.transform.Find(CluePopup.IMAGE_PATH);
            if (imageTransform == null)
            {
                return;
            }

            ClueImageToggle toggle = __instance.GetComponentInChildren<ClueImageToggle>(true);
            if (toggle == null)
            {
                toggle = ClueImageToggle.Build(imageTransform);
            }

            toggle.Bind(imageTransform.GetComponent<Image>(), image, translated);
        }
    }

    /// <summary>
    /// 단서 그림 위에 얹히는 반투명 전환 버튼.
    /// </summary>
    internal class ClueImageToggle : MonoBehaviour
    {
        private const float Inset = 14f;
        private const float Width = 78f;
        private const float Height = 30f;

        /// <summary>
        /// 마지막 선택을 기억한다. 단서를 열 때마다 다시 누르게 하지 않는다.
        /// </summary>
        private static bool preferTranslated = true;

        private Image target;
        private Sprite original;
        private Sprite translated;
        private TextMeshProUGUI label;

        internal static ClueImageToggle Build(Transform imageTransform)
        {
            GameObject root = new GameObject("한글 전환 버튼", typeof(RectTransform));
            root.transform.SetParent(imageTransform, false);

            RectTransform rect = root.GetComponent<RectTransform>();
            rect.anchorMin = new Vector2(1f, 1f);      // 그림의 오른쪽 위
            rect.anchorMax = new Vector2(1f, 1f);
            rect.pivot = new Vector2(1f, 1f);
            rect.anchoredPosition = new Vector2(-Inset, -Inset);
            rect.sizeDelta = new Vector2(Width, Height);

            Image background = root.AddComponent<Image>();
            background.color = new Color(0f, 0f, 0f, 0.55f);   // 그림을 가리지 않게 반투명

            GameObject textObject = new GameObject("Label", typeof(RectTransform));
            textObject.transform.SetParent(root.transform, false);
            RectTransform textRect = textObject.GetComponent<RectTransform>();
            textRect.anchorMin = Vector2.zero;
            textRect.anchorMax = Vector2.one;
            textRect.offsetMin = Vector2.zero;
            textRect.offsetMax = Vector2.zero;

            TextMeshProUGUI label = textObject.AddComponent<TextMeshProUGUI>();
            label.alignment = TextAlignmentOptions.Center;
            label.fontSize = 15f;
            label.color = Color.white;
            label.raycastTarget = false;

            ClueImageToggle toggle = root.AddComponent<ClueImageToggle>();
            toggle.label = label;

            Button button = root.AddComponent<Button>();
            button.targetGraphic = background;
            button.onClick.AddListener(toggle.Toggle);

            root.transform.SetAsLastSibling();   // 그림 위에 오도록
            return toggle;
        }

        internal void Bind(Image targetImage, Sprite originalSprite, Sprite translatedSprite)
        {
            target = targetImage;
            original = originalSprite;
            translated = translatedSprite;

            Apply(preferTranslated);
            transform.SetAsLastSibling();
        }

        private void Toggle()
        {
            preferTranslated = !preferTranslated;
            Apply(preferTranslated);
        }

        private void Apply(bool showTranslated)
        {
            if (target == null)
            {
                return;
            }

            target.sprite = showTranslated ? translated : original;

            // 누르면 무엇이 나오는지를 적는다. 지금 상태가 아니라 갈 곳을 보여준다.
            if (label != null)
            {
                label.text = showTranslated ? "원본" : "한글";
            }
        }
    }
}
