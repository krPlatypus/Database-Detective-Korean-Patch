using HarmonyLib;
using TMPro;
using UnityEngine;

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
        private static bool searched;
        private static float lastPlayed;

        /// <summary>
        /// 키를 꾹 누르고 있을 때 소리가 기관총처럼 겹치지 않게 최소 간격을 둔다.
        /// </summary>
        private const float MinimumInterval = 0.03f;

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

            if (!EnsureReady())
            {
                return;
            }

            lastPlayed = Time.unscaledTime;

            // 같은 소리가 그대로 반복되면 기계처럼 들린다. 음높이를 조금씩 흔든다.
            source.pitch = Random.Range(0.94f, 1.06f);
            source.PlayOneShot(clip, Plugin.TypingVolume.Value);
        }

        private static bool EnsureReady()
        {
            if (source != null && clip != null)
            {
                return true;
            }

            if (searched && clip == null)
            {
                return false;   // 한 번 찾아 실패했으면 매 타건마다 다시 뒤지지 않는다
            }

            searched = true;
            clip = FindClip();
            if (clip == null)
            {
                Plugin.Log.LogWarning(
                    $"타자음으로 쓸 소리를 찾지 못했습니다: {Plugin.TypingClip.Value}. 타자음을 끕니다.");
                return false;
            }

            if (source == null)
            {
                GameObject holder = new GameObject("DDKoreanPatch 타자음");
                Object.DontDestroyOnLoad(holder);
                holder.hideFlags = HideFlags.HideAndDontSave;

                source = holder.AddComponent<AudioSource>();
                source.playOnAwake = false;
                source.spatialBlend = 0f;            // 화면 UI 소리라 방향감이 없어야 한다
                source.outputAudioMixerGroup = BorrowMixerGroup();
            }

            Plugin.Log.LogInfo($"타자음 준비 완료: {clip.name}");
            return true;
        }

        private static AudioClip FindClip()
        {
            string wanted = Plugin.TypingClip.Value?.Trim();
            AudioClip fallback = null;

            foreach (AudioClip candidate in Resources.FindObjectsOfTypeAll<AudioClip>())
            {
                if (candidate == null)
                {
                    continue;
                }

                if (!string.IsNullOrEmpty(wanted) && candidate.name == wanted)
                {
                    return candidate;
                }

                // 지정한 클립이 아직 안 올라왔을 수 있으니 비슷한 것을 받아 둔다
                if (fallback == null && candidate.name.IndexOf("click", System.StringComparison.OrdinalIgnoreCase) >= 0)
                {
                    fallback = candidate;
                }
            }

            return fallback;
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
    /// 글자가 실제로 끼워 넣어지는 지점에서 소리를 낸다.
    /// Append가 아니라 Insert를 잡는 이유는, Append는 걸러져 버려지는 문자에도 불리지만
    /// Insert는 화면에 실제로 들어간 글자에만 불리기 때문이다.
    /// </summary>
    [HarmonyPatch]
    internal static class TypingSoundPatches
    {
        [HarmonyPostfix]
        [HarmonyPatch(typeof(TMP_InputField), "Insert")]
        private static void InsertPostfix()
        {
            TypingSound.Play();
        }
    }
}
