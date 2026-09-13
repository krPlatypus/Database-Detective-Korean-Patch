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
    ///
    /// 이름이 겹치는 그림이 있다. victim은 1장의 지구 그림(512x512)과 2장의
    /// 샌드위치 무덤(650x563)이 같은 이름을 쓴다. 이름만 보면 한쪽 번역본이
    /// 다른 쪽에 얹힌다. 그래서 '이름@가로x세로.png'를 먼저 찾고, 없을 때만
    /// '이름.png'로 내려간다. 겹치지 않는 그림은 지금처럼 이름만 써도 된다.
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
        /// 크기까지 맞는 번역본을 먼저 찾고, 없으면 이름만으로 찾는다.
        /// </summary>
        internal static Sprite Get(Sprite original)
        {
            if (original == null)
            {
                return null;
            }

            Texture2D texture = original.texture;
            if (texture != null)
            {
                Sprite sized = Get($"{original.name}@{texture.width}x{texture.height}");
                if (sized != null)
                {
                    return sized;
                }
            }

            return Get(original.name);
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
