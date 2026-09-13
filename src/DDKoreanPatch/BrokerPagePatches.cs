using System;
using HarmonyLib;
using TMPro;
using UnityEngine;

namespace DDKoreanPatch
{
    /// <summary>
    /// broker.com/traders의 웹사이트 칸을 제자리에 놓는다.
    ///
    /// 이 화면은 두 줄이다. 위는 '중개인 - 회사 이름', 아래는 '웹사이트 - 주소'.
    /// 그런데 주소를 담은 글상자만 라벨보다 왼쪽 아래에 떨어져 있고 오른쪽 정렬이라,
    /// 글이 짧으면 눈에 띄지 않는다. CSV에 실린 회사 32곳은 주소 칸이 비어 있어
    /// 늘 '없음'만 들어가는데, 한글은 영문보다 짧아 더 눈에 띄지 않는다.
    /// 라벨만 덩그러니 남고 값이 없는 것처럼 보인다.
    ///
    /// 위 줄은 멀쩡하므로 그 배치를 그대로 가져다 쓴다. 회사 이름이 '중개인'에서
    /// 떨어진 만큼 주소도 '웹사이트'에서 떨어뜨리고, 높이는 라벨에 맞춘다.
    /// 값을 눈금으로 박지 않고 옆 줄에서 재므로, 창 크기나 글꼴이 달라져도 따라간다.
    /// </summary>
    [HarmonyPatch]
    internal static class BrokerPagePatches
    {
        private const string NameTitle = "Trader Name Title";
        private const string SiteTitle = "Website Title";

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
                Align(__instance);
            }
            catch (Exception e)
            {
                Plugin.Log.LogWarning("중개인 화면을 정리하지 못했다: " + e.Message);
            }
        }

        private static void Align(broker_search page)
        {
            Traverse box = Traverse.Create(page);
            GameObject website = box.Field("website").GetValue<GameObject>();
            TextMeshProUGUI firm = box.Field("firm").GetValue<TextMeshProUGUI>();
            if (website == null || firm == null)
            {
                return;
            }

            Transform row = website.transform.parent;
            RectTransform nameTitle = Find(row, NameTitle);
            RectTransform siteTitle = Find(row, SiteTitle);
            if (nameTitle == null || siteTitle == null)
            {
                return;
            }

            // 위 줄에서 '라벨 -> 값'의 간격을 읽어 아래 줄에 그대로 쓴다.
            float gap = firm.rectTransform.anchoredPosition.x - nameTitle.anchoredPosition.x;
            Vector2 place = new Vector2(siteTitle.anchoredPosition.x + gap,
                                        siteTitle.anchoredPosition.y);

            RectTransform value = website.GetComponent<RectTransform>();
            if (value == null || value.anchoredPosition == place)
            {
                return;
            }

            value.anchoredPosition = place;

            // 오른쪽 정렬이라 짧은 값이 라벨 쪽으로 붙어 버린다. 회사 이름과 같이
            // 왼쪽에서 시작하게 맞춘다.
            TextMeshProUGUI label = website.GetComponent<TextMeshProUGUI>();
            if (label != null)
            {
                label.alignment = firm.alignment;
            }
        }

        private static RectTransform Find(Transform row, string name)
        {
            Transform found = row == null ? null : row.Find(name);
            return found == null ? null : found as RectTransform;
        }
    }
}
