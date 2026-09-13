using System;
using HarmonyLib;
using UnityEngine;
using UnityEngine.UI;

namespace DDKoreanPatch
{
    /// <summary>
    /// broker.com/traders에서 주소가 없는 회사는 '웹사이트' 줄을 통째로 감춘다.
    ///
    /// CSV에 실린 회사 32곳은 주소 칸이 비어 있다. 게임은 이때 값 자리에
    /// '<i>None provided</i>'를 넣고 버튼만 꺼 두는데, 그 글상자가 라벨과
    /// 떨어진 자리에 있어 화면에서는 라벨만 덩그러니 남는다.
    /// 없는 항목이면 줄을 아예 내보내지 않는 편이 낫다.
    ///
    /// 주소가 있고 없고는 게임이 버튼을 켜고 끄는 것으로 이미 구분해 두었으니
    /// 그 값을 그대로 읽는다.
    /// </summary>
    [HarmonyPatch]
    internal static class BrokerPagePatches
    {
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
                HideEmptyWebsite(__instance);
            }
            catch (Exception e)
            {
                Plugin.Log.LogWarning("중개인 화면을 정리하지 못했다: " + e.Message);
            }
        }

        private static void HideEmptyWebsite(broker_search page)
        {
            GameObject website = Traverse.Create(page).Field("website").GetValue<GameObject>();
            if (website == null)
            {
                return;
            }

            Button link = website.GetComponent<Button>();
            if (link == null)
            {
                return;
            }

            bool hasWebsite = link.interactable;
            website.SetActive(hasWebsite);

            Transform title = website.transform.parent == null
                ? null
                : website.transform.parent.Find(SiteTitle);
            if (title != null)
            {
                title.gameObject.SetActive(hasWebsite);
            }
        }
    }
}
