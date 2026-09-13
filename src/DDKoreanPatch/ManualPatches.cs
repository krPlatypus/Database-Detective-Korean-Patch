using HarmonyLib;
using UnityEngine;
using UnityEngine.UI;

namespace DDKoreanPatch
{
    /// <summary>
    /// 사용 설명서 페이지를 번역본 그림으로 갈아 끼운다.
    ///
    /// 설명서 본문은 게임 안에 글로 들어 있지 않고 쪽마다 그려진 그림이다.
    /// 그래서 글자를 바꾸는 길이 없고 그림 자체를 바꿔야 한다.
    ///
    /// 단서 창과 달리 코드가 그림을 넣어 주는 길목이 없다. 쪽 그림이 프리팹에
    /// 박힌 채로 켜지고 꺼질 뿐이다. 그래서 장을 펼치는 순간을 잡아
    /// 그 안의 그림들을 훑어 바꾼다.
    /// </summary>
    [HarmonyPatch]
    internal static class ManualPatches
    {
        [HarmonyPostfix]
        [HarmonyPatch(typeof(ChapterButton), nameof(ChapterButton.LaunchChapter))]
        private static void LaunchChapterPostfix(ChapterButton __instance)
        {
            if (__instance != null)
            {
                Swap(__instance.transform.root);
            }
        }

        /// <summary>
        /// 아래에 딸린 그림 중 번역본이 있는 것을 갈아 끼운다.
        /// 꺼져 있는 것까지 훑어야 한다. 장을 펼칠 때 아직 켜지지 않은 쪽이 있다.
        /// </summary>
        internal static void Swap(Transform root)
        {
            if (root == null)
            {
                return;
            }

            int changed = 0;
            foreach (Image image in root.GetComponentsInChildren<Image>(true))
            {
                Sprite current = image != null ? image.sprite : null;
                if (current == null)
                {
                    continue;
                }

                Sprite translated = TranslatedImages.Get(current.name);
                if (translated != null && translated != current)
                {
                    image.sprite = translated;
                    changed++;
                }
            }

            if (changed > 0)
            {
                Plugin.Log.LogInfo($"설명서 쪽 그림 {changed}장을 번역본으로 바꿨습니다.");
            }
        }
    }
}
