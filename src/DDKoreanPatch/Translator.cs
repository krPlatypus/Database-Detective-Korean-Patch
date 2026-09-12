using System;
using System.Collections.Generic;
using System.IO;
using System.Text.RegularExpressions;
using Newtonsoft.Json;

namespace DDKoreanPatch
{
    /// <summary>
    /// 번역문 보관과 조회.
    ///
    /// UI는 원문 문자열을 그대로 키로 쓴다.
    /// TextAsset은 이름이 겹치는 것이 있어(correct, wrong 등) 내용 전체를 키로 쓴다.
    /// </summary>
    internal static class Translator
    {
        private static Dictionary<string, string> ui = new Dictionary<string, string>();
        private static Dictionary<string, string> textAssets = new Dictionary<string, string>();
        private static List<Pattern> patterns = new List<Pattern>();

        /// <summary>
        /// 값이 끼워 넣어진 채로 만들어지는 문장을 위한 정규식 규칙.
        /// 예: 파서 오류는 "Cannot find table named: " + 이름 + "..." 처럼
        /// 문자열을 이어 붙여 만들기 때문에 정확 일치 사전으로는 잡히지 않는다.
        /// </summary>
        private class Pattern
        {
            public string match { get; set; }
            public string replace { get; set; }

            [JsonIgnore]
            public Regex Compiled;
        }

        internal static bool HasUiText => ui.Count > 0;
        internal static bool HasTextAssets => textAssets.Count > 0;

        private class Bundle
        {
            public Dictionary<string, string> ui { get; set; }
            public Dictionary<string, string> textAssets { get; set; }
            public List<Pattern> patterns { get; set; }
        }

        internal static void Load(string pluginDirectory)
        {
            string path = Path.Combine(pluginDirectory, "translation.json");
            if (!File.Exists(path))
            {
                Plugin.Log.LogWarning($"번역 파일이 없습니다: {path}");
                return;
            }

            try
            {
                Bundle bundle = JsonConvert.DeserializeObject<Bundle>(File.ReadAllText(path));
                ui = bundle?.ui ?? new Dictionary<string, string>();
                textAssets = bundle?.textAssets ?? new Dictionary<string, string>();
                patterns = bundle?.patterns ?? new List<Pattern>();

                foreach (Pattern pattern in patterns)
                {
                    pattern.Compiled = new Regex(pattern.match, RegexOptions.Compiled | RegexOptions.Singleline);
                }

                Plugin.Log.LogInfo(
                    $"번역 로드: UI {ui.Count}개, TextAsset {textAssets.Count}개, 패턴 {patterns.Count}개");
            }
            catch (Exception e)
            {
                Plugin.Log.LogError($"번역 파일을 읽지 못했습니다: {e.Message}");
            }
        }

        /// <summary>UI 문자열 조회. 번역이 없으면 원문을 그대로 돌려준다.</summary>
        internal static string TranslateUi(string source)
        {
            if (string.IsNullOrEmpty(source) || ui.Count == 0)
            {
                return source;
            }

            if (ui.TryGetValue(source, out string exact))
            {
                return exact;
            }

            // 앞뒤 공백만 다른 경우도 잡아준다. 공백은 원래대로 돌려놓는다.
            string trimmed = source.Trim();
            if (trimmed.Length != source.Length && ui.TryGetValue(trimmed, out string inner))
            {
                int start = source.IndexOf(trimmed, StringComparison.Ordinal);
                return source.Substring(0, start) + inner + source.Substring(start + trimmed.Length);
            }

            // 값이 끼워 넣어진 문장은 정규식으로 잡는다.
            foreach (Pattern pattern in patterns)
            {
                if (pattern.Compiled != null && pattern.Compiled.IsMatch(source))
                {
                    return pattern.Compiled.Replace(source, pattern.replace);
                }
            }

            return source;
        }

        /// <summary>TextAsset 내용 조회. 번역이 없으면 원문을 그대로 돌려준다.</summary>
        internal static string TranslateAsset(string source)
        {
            if (string.IsNullOrEmpty(source) || textAssets.Count == 0)
            {
                return source;
            }

            return textAssets.TryGetValue(source, out string translated) ? translated : source;
        }
    }
}
