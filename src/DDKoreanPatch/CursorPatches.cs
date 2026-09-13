using HarmonyLib;
using UnityEngine;

namespace DDKoreanPatch
{
    /// <summary>
    /// 조수 위에 마우스를 올렸을 때 나오는 HELP 커서를 한글본으로 바꾼다.
    ///
    /// 이 HELP는 화면 문자열이 아니라 32x32 커서 그림이다(UI/Cursor/ask).
    /// TMP를 거치지 않으니 번역 사전으로는 닿지 않아 그림을 갈아 끼운다.
    ///
    /// CursorManager는 Start에서 커서들을 한 번 읽어 정적 필드에 담아 두고,
    /// 그 뒤로는 담아 둔 것만 쓴다. 그러니 Start 뒤에 필드 하나만 바꿔 두면
    /// 커서를 세우는 쪽은 건드릴 필요가 없다.
    /// </summary>
    [HarmonyPatch]
    internal static class CursorPatches
    {
        private const string ImageName = "cursor-ask";

        [HarmonyPostfix]
        [HarmonyPatch(typeof(CursorManager), "Start")]
        private static void StartPostfix()
        {
            Texture2D ask = TranslatedImages.GetTexture(ImageName);
            if (ask == null)
            {
                return;
            }

            // 커서로 쓰려면 밉맵이 없어야 하는데, TranslatedImages가 만드는
            // 텍스처가 이미 그 조건이다. 점 보간으로 두어 도트가 뭉개지지 않게 한다.
            ask.filterMode = FilterMode.Point;

            Traverse field = Traverse.Create(typeof(CursorManager)).Field("ask");
            if (!field.FieldExists())
            {
                Plugin.Log.LogWarning("커서 필드를 찾지 못해 HELP 커서를 두었습니다.");
                return;
            }

            field.SetValue(ask);
        }
    }
}
