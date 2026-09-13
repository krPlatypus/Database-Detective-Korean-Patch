using System;
using System.Collections.Generic;
using HarmonyLib;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

namespace DDKoreanPatch
{
    /// <summary>
    /// broker.com/traders 화면을 다듬는다. 두 가지를 한다.
    ///
    /// 1. 주소가 없는 회사는 '웹사이트' 줄을 통째로 감춘다.
    ///    CSV에 실린 회사 32곳은 주소 칸이 비어 있다. 게임은 값 자리에
    ///    '<i>None provided</i>'를 넣고 버튼만 꺼 두는데, 그 글상자가 라벨과
    ///    떨어진 자리에 있어 화면에는 라벨만 덩그러니 남는다.
    ///
    /// 2. 라벨을 값의 기준선에 맞춘다.
    ///    이 화면의 글상자는 모두 위 맞춤이고, 라벨과 값은 글자 크기가 두 배
    ///    넘게 차이 난다(40 대 80). 위를 맞추면 큰 글자가 아래로 더 뻗어
    ///    라벨이 높이 뜬 것처럼 보인다. 원문은 'TRADER\nNAME' 두 줄이라 그
    ///    차이가 가려졌는데, 한글은 '중개인' 한 줄이라 드러난다.
    ///
    ///    눈금으로 박지 않고 TMP에게 첫 줄 기준선을 물어 그만큼만 내린다.
    ///    글꼴이나 글자 크기가 달라져도 따라간다.
    /// </summary>
    [HarmonyPatch]
    internal static class BrokerPagePatches
    {
        private const string NameTitle = "Trader Name Title";
        private const string SiteTitle = "Website Title";

        // 처음 본 자리. 여러 번 맞춰도 같은 결과가 나오도록 기준을 붙잡아 둔다.
        private static readonly Dictionary<RectTransform, float> origin =
            new Dictionary<RectTransform, float>();

        [HarmonyPostfix]
        [HarmonyPatch(typeof(broker_search), nameof(broker_search.Search), new[] { typeof(string) })]
        private static void SearchPostfix(broker_search __instance)
        {
            if (!Plugin.EnableTranslation.Value)
            {
                return;
            }

            try
            {
                Tidy(__instance);
            }
            catch (Exception e)
            {
                Plugin.Log.LogWarning("중개인 화면을 정리하지 못했다: " + e.Message);
            }
        }

        private static void Tidy(broker_search page)
        {
            Traverse box = Traverse.Create(page);
            GameObject website = box.Field("website").GetValue<GameObject>();
            TextMeshProUGUI firm = box.Field("firm").GetValue<TextMeshProUGUI>();
            TextMeshProUGUI bio = box.Field("bio").GetValue<TextMeshProUGUI>();
            if (website == null || firm == null || bio == null)
            {
                return;
            }

            Transform row = website.transform.parent;
            TextMeshProUGUI nameTitle = Label(row, NameTitle);
            TextMeshProUGUI siteTitle = Label(row, SiteTitle);

            // 주소가 있고 없고는 게임이 버튼을 켜고 끄는 것으로 이미 구분해 두었다.
            Button link = website.GetComponent<Button>();
            bool hasWebsite = link != null && link.interactable;
            website.SetActive(hasWebsite);
            if (siteTitle != null)
            {
                siteTitle.gameObject.SetActive(hasWebsite);
            }

            AlignToBaseline(nameTitle, firm);

            if (hasWebsite)
            {
                // 주소는 라벨 바로 아래에 붙어 있다. 라벨을 옮긴 만큼 같이 옮겨
                // 둘 사이 간격을 지킨다.
                RectTransform value = website.GetComponent<RectTransform>();
                float before = Origin(siteTitle == null ? null : siteTitle.rectTransform);
                AlignToBaseline(siteTitle, bio);
                if (siteTitle != null && value != null)
                {
                    float moved = siteTitle.rectTransform.anchoredPosition.y - before;
                    Vector2 place = value.anchoredPosition;
                    value.anchoredPosition = new Vector2(place.x, Origin(value) + moved);
                }
            }
        }

        /// <summary>
        /// 라벨의 첫 줄 기준선을 값의 첫 줄 기준선에 맞춘다.
        /// </summary>
        private static void AlignToBaseline(TMP_Text label, TMP_Text value)
        {
            if (label == null || value == null || !label.gameObject.activeInHierarchy)
            {
                return;
            }

            float labelBase = FirstBaseline(label);
            float valueBase = FirstBaseline(value);
            if (float.IsNaN(labelBase) || float.IsNaN(valueBase))
            {
                return;
            }

            RectTransform rect = label.rectTransform;
            float target = value.rectTransform.anchoredPosition.y + valueBase - labelBase;
            Origin(rect);   // 처음 자리를 기억해 둔다
            rect.anchoredPosition = new Vector2(rect.anchoredPosition.x, target);
        }

        /// <summary>
        /// 글상자 안에서 첫 줄 기준선이 놓인 높이. 상자의 가운데를 0으로 본다.
        /// </summary>
        private static float FirstBaseline(TMP_Text text)
        {
            text.ForceMeshUpdate();
            TMP_TextInfo info = text.textInfo;
            if (info == null || info.lineCount == 0)
            {
                return float.NaN;
            }

            return info.lineInfo[0].baseline;
        }

        private static float Origin(RectTransform rect)
        {
            if (rect == null)
            {
                return 0f;
            }

            if (!origin.TryGetValue(rect, out float first))
            {
                first = rect.anchoredPosition.y;
                origin[rect] = first;
            }

            return first;
        }

        private static TextMeshProUGUI Label(Transform row, string name)
        {
            Transform found = row == null ? null : row.Find(name);
            return found == null ? null : found.GetComponent<TextMeshProUGUI>();
        }
    }
}
