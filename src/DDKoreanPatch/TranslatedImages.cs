using System.Collections.Generic;
using System.IO;
using UnityEngine;

namespace DDKoreanPatch
{
    /// <summary>
    /// 번역된 단서 이미지를 파일에서 읽어 스프라이트로 만들어 둔다.
    ///
    /// 플러그인 폴더의 images/ 아래에 원본 스프라이트와 같은 이름으로 PNG를 두면
    /// 그 단서에 번역본이 있는 것으로 본다. 없으면 전환 버튼도 나오지 않는다.
    /// 덕분에 28장을 다 만들지 않고 몇 장만 먼저 넣어도 문제가 없다.
    /// </summary>
    internal static class TranslatedImages
    {
        private static string imageDirectory;
        private static readonly Dictionary<string, Sprite> cache = new Dictionary<string, Sprite>();

        internal static void Initialize(string pluginDirectory)
        {
            imageDirectory = Path.Combine(pluginDirectory, "images");

            if (!Directory.Exists(imageDirectory))
            {
                Plugin.Log.LogInfo("번역 이미지 폴더가 없습니다. 단서 이미지는 원본만 표시됩니다.");
                return;
            }

            int count = Directory.GetFiles(imageDirectory, "*.png").Length;
            Plugin.Log.LogInfo($"번역 이미지 {count}개를 찾았습니다: {imageDirectory}");
        }

        internal static bool Has(string spriteName)
        {
            return Get(spriteName) != null;
        }

        /// <summary>
        /// 번역본 스프라이트를 돌려준다. 없으면 null.
        /// 원본과 같은 크기로 만들어 두어야 화면에서 자리가 어긋나지 않는다.
        /// </summary>
        internal static Sprite Get(string spriteName)
        {
            if (string.IsNullOrEmpty(spriteName) || imageDirectory == null)
            {
                return null;
            }

            if (cache.TryGetValue(spriteName, out Sprite cached))
            {
                return cached;
            }

            string path = Path.Combine(imageDirectory, spriteName + ".png");
            Sprite sprite = null;

            if (File.Exists(path))
            {
                try
                {
                    Texture2D texture = new Texture2D(2, 2, TextureFormat.RGBA32, false);
                    if (texture.LoadImage(File.ReadAllBytes(path)))
                    {
                        texture.name = spriteName + " (번역본)";
                        texture.wrapMode = TextureWrapMode.Clamp;
                        Object.DontDestroyOnLoad(texture);

                        sprite = Sprite.Create(
                            texture,
                            new Rect(0f, 0f, texture.width, texture.height),
                            new Vector2(0.5f, 0.5f),
                            100f);
                        sprite.name = spriteName;
                        Object.DontDestroyOnLoad(sprite);
                    }
                    else
                    {
                        Plugin.Log.LogWarning($"이미지를 해석하지 못했습니다: {path}");
                    }
                }
                catch (System.Exception e)
                {
                    Plugin.Log.LogError($"이미지를 읽지 못했습니다 {path}: {e.Message}");
                }
            }

            cache[spriteName] = sprite;
            return sprite;
        }

        /// <summary>
        /// 같은 PNG를 스프라이트가 아니라 텍스처로 받는다.
        /// 마우스 커서처럼 스프라이트를 받지 않는 자리에 쓴다.
        /// </summary>
        internal static Texture2D GetTexture(string name)
        {
            return Get(name)?.texture;
        }
    }
}
