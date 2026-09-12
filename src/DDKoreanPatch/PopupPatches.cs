using HarmonyLib;
using TMPro;
using UnityEngine;
using UnityEngine.InputSystem;

namespace DDKoreanPatch
{
    /// <summary>
    /// 알림·오류 팝업을 Esc나 Enter로 닫을 수 있게 한다.
    ///
    /// 원래는 창 오른쪽 위 X를 눌러야만 닫힌다. 쿼리를 고치는 동안 오류 팝업이
    /// 반복해서 뜨는 흐름이라 마우스로 매번 닫는 것이 번거롭다.
    ///
    /// NotificationHandler가 만들어 준 팝업에만 동작을 붙인다.
    /// 모든 패널을 대상으로 삼으면 본 게임 창까지 닫히므로 범위를 좁힌다.
    /// </summary>
    [HarmonyPatch]
    internal static class PopupPatches
    {
        [HarmonyPostfix]
        [HarmonyPatch(typeof(NotificationHandler), nameof(NotificationHandler.CreateNotificationPanel),
            new[] { typeof(string), typeof(bool) })]
        private static void CreateNotificationPanelPostfix(GameObject __result)
        {
            if (__result == null || !Plugin.ClosePopupWithKey.Value)
            {
                return;
            }

            if (__result.GetComponent<PopupKeyCloser>() == null)
            {
                __result.AddComponent<PopupKeyCloser>();
            }
        }
    }

    /// <summary>
    /// 팝업에 붙어 Esc/Enter를 기다렸다가 닫는다.
    /// </summary>
    internal class PopupKeyCloser : MonoBehaviour
    {
        private Panel panel;

        private void Awake()
        {
            panel = GetComponent<Panel>();
        }

        private void Update()
        {
            if (panel == null || panel.IsClosing())
            {
                return;
            }

            Keyboard keyboard = Keyboard.current;
            if (keyboard == null)
            {
                return;
            }

            bool pressed = keyboard.escapeKey.wasPressedThisFrame
                           || keyboard.enterKey.wasPressedThisFrame
                           || keyboard.numpadEnterKey.wasPressedThisFrame;

            if (!pressed || IsTypingSomewhere())
            {
                return;
            }

            panel.ClosePanel();
        }

        /// <summary>
        /// 어딘가에 글을 쓰는 중이면 Enter는 그쪽 몫이다.
        /// 쿼리창에 커서를 둔 채로 팝업이 떠 있는 경우가 있어 확인이 필요하다.
        /// </summary>
        private static bool IsTypingSomewhere()
        {
            foreach (TMP_InputField field in Resources.FindObjectsOfTypeAll<TMP_InputField>())
            {
                if (field != null && field.isFocused)
                {
                    return true;
                }
            }

            return false;
        }
    }
}
