using System.Collections;
using System.Collections.Generic;
using System.IO;
using HarmonyLib;
using TMPro;
using UnityEngine;
using UnityEngine.Networking;

namespace DDKoreanPatch
{
    /// <summary>
    /// 글자를 칠 때마다 짧은 타건음을 낸다.
    ///
    /// 소리는 게임에 이미 들어 있는 클릭 계열 클립을 빌려 쓴다.
    /// 새로 만들어 넣으면 게임의 다른 소리와 음색이 겉돈다.
    ///
    /// 믹서 그룹도 게임 효과음에서 가져온다. 그래야 설정의 효과음 볼륨이
    /// 이 소리에도 함께 적용된다. 직접 재생하면 음소거를 해도 이 소리만 남는다.
    /// </summary>
    internal static class TypingSound
    {
        private static AudioSource source;
        private static AudioClip clip;
        private static bool foundPreferred;
        private static float lastSearched = float.NegativeInfinity;
        private static float lastPlayed;

        /// <summary>
        /// 설정한 소리가 아직 메모리에 없을 때 대신 쓸 것들. 앞에서부터 찾는다.
        /// 게임에는 click이 이름에 들어간 소리가 여럿인데 그중 pop 계열은
        /// 뽀잉 하고 튀는 소리라 타건음으로 쓰면 전혀 다른 느낌이 난다.
        /// 짧고 꼬리 없는 것만 고른다.
        /// </summary>
        private static readonly string[] Fallbacks =
        {
            "click down", "click down 2", "pen down 1",
            "mouse-click-290204", "click up", "click up 2",
        };

        /// <summary>
        /// 키를 꾹 누르고 있을 때 소리가 기관총처럼 겹치지 않게 최소 간격을 둔다.
        /// </summary>
        private const float MinimumInterval = 0.03f;

        /// <summary>
        /// sounds/ 폴더에서 읽어 온 소리들. 있으면 게임 내 소리보다 우선한다.
        /// 여러 개면 번갈아 써서 사람이 치는 느낌을 낸다.
        /// </summary>
        private static readonly List<AudioClip> external = new List<AudioClip>();
        private static int lastExternalIndex = -1;

        internal static void Play()
        {
            if (!Plugin.EnableTypingSound.Value)
            {
                return;
            }

            if (Time.unscaledTime - lastPlayed < MinimumInterval)
            {
                return;
            }

            AudioClip chosen = PickExternal();
            if (chosen == null)
            {
                if (!EnsureReady())
                {
                    return;
                }

                chosen = clip;
            }
            else if (source == null && !EnsureSource())
            {
                return;
            }

            lastPlayed = Time.unscaledTime;

            // 같은 소리가 그대로 반복되면 기계처럼 들린다. 음높이를 조금씩 흔든다.
            source.pitch = Random.Range(0.94f, 1.06f);
            source.PlayOneShot(chosen, Plugin.TypingVolume.Value);
        }

        /// <summary>바로 앞에 쓴 소리는 피해서 고른다. 같은 소리가 연달아 나면 티가 난다.</summary>
        private static AudioClip PickExternal()
        {
            if (external.Count == 0)
            {
                return null;
            }

            if (external.Count == 1)
            {
                return external[0];
            }

            int index = Random.Range(0, external.Count);
            if (index == lastExternalIndex)
            {
                index = (index + 1) % external.Count;
            }

            lastExternalIndex = index;
            return external[index];
        }

        private static bool EnsureReady()
        {
            // 지정한 소리를 아직 못 찾았으면 이따금 다시 찾는다.
            // 소리는 쓰이는 시점에 메모리로 올라오므로, 처음 타건할 때는
            // 없다가 나중에 생기는 경우가 있다. 한 번 실패했다고 포기하면
            // 대신 잡은 소리를 끝까지 쓰게 된다.
            if (!foundPreferred && Time.unscaledTime - lastSearched >= 1f)
            {
                lastSearched = Time.unscaledTime;
                Search();
            }

            return clip != null && EnsureSource();
        }

        private static bool EnsureSource()
        {
            if (source != null)
            {
                return true;
            }

            GameObject holder = new GameObject("DDKoreanPatch 타자음");
            Object.DontDestroyOnLoad(holder);
            holder.hideFlags = HideFlags.HideAndDontSave;

            source = holder.AddComponent<AudioSource>();
            source.playOnAwake = false;
            source.spatialBlend = 0f;            // 화면 UI 소리라 방향감이 없어야 한다
            source.outputAudioMixerGroup = BorrowMixerGroup();
            return true;
        }

        /// <summary>
        /// 플러그인 폴더의 sounds/ 아래에 있는 음원을 읽어 들인다.
        ///
        /// 게임 자산에는 진짜 키보드 소리가 없고 마우스·펜 계열만 있다.
        /// 직접 넣은 음원이 있으면 그쪽이 훨씬 낫다.
        /// 읽기는 시간이 걸리므로 코루틴으로 돌리고, 끝날 때까지는 게임 내 소리를 쓴다.
        /// </summary>
        internal static IEnumerator LoadExternal(string pluginDirectory)
        {
            string root = Path.Combine(pluginDirectory, "sounds");
            if (!Directory.Exists(root))
            {
                yield break;
            }

            foreach (string path in Directory.GetFiles(root, "*.*", SearchOption.AllDirectories))
            {
                AudioType type = TypeOf(path);
                if (type == AudioType.UNKNOWN)
                {
                    continue;
                }

                using (UnityWebRequest request =
                       UnityWebRequestMultimedia.GetAudioClip("file:///" + path.Replace('\\', '/'), type))
                {
                    yield return request.SendWebRequest();

                    if (request.result != UnityWebRequest.Result.Success)
                    {
                        Plugin.Log.LogWarning($"소리를 읽지 못했습니다 {Path.GetFileName(path)}: {request.error}");
                        continue;
                    }

                    AudioClip loaded = DownloadHandlerAudioClip.GetContent(request);
                    if (loaded == null)
                    {
                        continue;
                    }

                    loaded.name = Path.GetFileNameWithoutExtension(path);
                    Object.DontDestroyOnLoad(loaded);
                    external.Add(loaded);
                }
            }

            if (external.Count > 0)
            {
                Plugin.Log.LogInfo($"타자음으로 쓸 외부 음원 {external.Count}개를 읽었습니다: {root}");
            }
        }

        private static AudioType TypeOf(string path)
        {
            switch (Path.GetExtension(path).ToLowerInvariant())
            {
                case ".mp3": return AudioType.MPEG;
                case ".wav": return AudioType.WAV;
                case ".ogg": return AudioType.OGGVORBIS;
                case ".aiff":
                case ".aif": return AudioType.AIFF;
                default: return AudioType.UNKNOWN;
            }
        }

        /// <summary>
        /// 쓸 소리를 찾는다. 설정한 이름이 우선이고, 없으면 정해 둔 후보를 순서대로 본다.
        /// 이름만 보고 아무 click이나 집으면 pop 계열이 걸려 뽀잉 하는 소리가 난다.
        /// </summary>
        private static void Search()
        {
            string wanted = Plugin.TypingClip.Value?.Trim();

            AudioClip[] loaded = Resources.FindObjectsOfTypeAll<AudioClip>();
            AudioClip found = Match(loaded, wanted);

            if (found != null)
            {
                foundPreferred = true;
            }
            else
            {
                foreach (string name in Fallbacks)
                {
                    found = Match(loaded, name);
                    if (found != null)
                    {
                        break;
                    }
                }
            }

            if (found == null || found == clip)
            {
                return;
            }

            clip = found;
            Plugin.Log.LogInfo(
                foundPreferred
                    ? $"타자음: {clip.name}"
                    : $"타자음: {clip.name} (설정한 '{wanted}' 을(를) 아직 못 찾아 대신 씁니다)");
        }

        private static AudioClip Match(AudioClip[] clips, string name)
        {
            if (string.IsNullOrEmpty(name))
            {
                return null;
            }

            foreach (AudioClip candidate in clips)
            {
                if (candidate != null && candidate.name == name)
                {
                    return candidate;
                }
            }

            return null;
        }

        /// <summary>게임 효과음이 쓰는 믹서 그룹을 그대로 따라간다.</summary>
        private static UnityEngine.Audio.AudioMixerGroup BorrowMixerGroup()
        {
            foreach (SoundEffectPlayer player in Resources.FindObjectsOfTypeAll<SoundEffectPlayer>())
            {
                AudioSource existing = player != null ? player.GetComponent<AudioSource>() : null;
                if (existing != null && existing.outputAudioMixerGroup != null)
                {
                    return existing.outputAudioMixerGroup;
                }
            }

            return null;
        }
    }

    /// <summary>
    /// 글자를 넣을 때와 지울 때 모두 소리를 낸다.
    ///
    /// 넣는 쪽은 Append가 아니라 Insert를 잡는다. Append는 걸러져 버려지는 문자에도
    /// 불리지만 Insert는 화면에 실제로 들어간 글자에만 불린다.
    ///
    /// 지우는 쪽은 백스페이스와 딜리트가 각각 다른 메서드를 탄다.
    /// 치는 소리만 나고 지우는 소리가 없으면 중간에 끊긴 느낌이 든다.
    /// </summary>
    [HarmonyPatch]
    internal static class TypingSoundPatches
    {
        [HarmonyPostfix]
        [HarmonyPatch(typeof(TMP_InputField), "Insert")]
        [HarmonyPatch(typeof(TMP_InputField), "Backspace")]
        [HarmonyPatch(typeof(TMP_InputField), "DeleteKey")]
        private static void KeyPostfix()
        {
            TypingSound.Play();
        }
    }
}
