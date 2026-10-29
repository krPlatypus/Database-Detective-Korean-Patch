using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text.RegularExpressions;
using Newtonsoft.Json.Linq;
using HarmonyLib;
using DDKoreanPatch;

class Program
{
    static int count;
    static void Check(bool ok, string message) { count++; if (!ok) throw new Exception(message); }
    static void Main(string[] args)
    {
        string root=args[0];
        Translator.Load(Path.Combine(root,"dist"));
        var bundle=JObject.Parse(File.ReadAllText(Path.Combine(root,"dist/translation.json")));
        foreach (var item in ((JObject)bundle["ui"]).Properties())
        {
            if (Regex.IsMatch(item.Name,@"\{\d+\}"))
            {
                string source=Regex.Replace(item.Name,@"\{(\d+)\}", m => "VALUE_"+m.Groups[1].Value);
                string expected=Regex.Replace((string)item.Value,@"\{(\d+)\}", m => "VALUE_"+m.Groups[1].Value);
                Check(Translator.TranslateUi(source)==expected,"Format: "+source+" => "+Translator.TranslateUi(source));
            }
        }
        foreach(var c in JArray.Parse(File.ReadAllText(Path.Combine(root,"tests/translation_cases.json"))))
            Check(Translator.TranslateUi((string)c["source"])==(string)c["expected"],"Fixture: "+c["source"]+" => "+Translator.TranslateUi((string)c["source"]));
        foreach(var file in new[]{"ui_keep_original", "code_strings_skipped"})
        foreach(var p in JObject.Parse(File.ReadAllText(Path.Combine(root,"translation/"+file+".json"))).Properties())
            Check(Translator.TranslateUi(p.Name)==p.Name,"Protected: "+p.Name);
        foreach(var p in ((JObject)bundle["textAssets"]).Properties())
            Check(Translator.TranslateAsset(p.Name)==(string)p.Value,"TextAsset");
        Check(MessageTitlePatches.MatchesTitle("환영한다, 신입!", "Welcome recruit!"),"Intro title");
        Check(MessageTitlePatches.MatchesTitle("고맙다.", "Thank you."),"Ending success title");
        Check(MessageTitlePatches.MatchesTitle("일을 망쳤군", "HORRIBLE JOB"),"Ending failure title");
        Check(!MessageTitlePatches.MatchesTitle("일을 망쳤군", "Thank you."),"Must not confuse ending outcomes");
        Check(MessageTitlePatches.MatchesTitle("Thank you.", "Thank you."),"Original title");
        var targets = (IEnumerable<MethodBase>)typeof(MessageTitlePatches)
            .GetMethod("TargetMethods", BindingFlags.Static | BindingFlags.NonPublic).Invoke(null, null);
        Check(targets.Select(m => m.Name).OrderBy(n => n).SequenceEqual(new[] { "PlayAudio", "StopAudioAction" }),
            "Both message-control methods must be patched");
        var rewrite=typeof(MessageTitlePatches).GetMethod("CompareTitles",BindingFlags.Static|BindingFlags.NonPublic);
        using (var assembly=Mono.Cecil.AssemblyDefinition.ReadAssembly(typeof(AudioMessageManager).Assembly.Location))
        foreach(var name in new[]{"PlayAudio","StopAudioAction"})
        {
            var method=assembly.MainModule.GetType("AudioMessageManager").Methods.Single(m=>m.Name==name);
            int actual=method.Body.Instructions.Count(i=>i.Operand is Mono.Cecil.MethodReference m && m.Name=="op_Equality" && m.DeclaringType.FullName=="System.String");
            int expected=name=="PlayAudio"?2:3;
            Check(actual==expected,"Original title comparisons: "+name);
            var equality=typeof(string).GetMethod("op_Equality");
            var codes=Enumerable.Range(0,actual).Select(_=>new CodeInstruction(System.Reflection.Emit.OpCodes.Call,equality)).ToList();
            codes.Insert(0,new CodeInstruction(System.Reflection.Emit.OpCodes.Nop));
            var patched=((IEnumerable<CodeInstruction>)rewrite.Invoke(null,new object[]{codes})).ToList();
            var target=typeof(MessageTitlePatches).GetMethod("MatchesTitle",BindingFlags.NonPublic|BindingFlags.Static);
            Check(patched.Count(c=>Equals(c.operand,target))==expected,"Patched title comparisons: "+name);
            Check(patched[0].opcode==System.Reflection.Emit.OpCodes.Nop,"Preserve other instructions");
        }
        Console.WriteLine($"PASS: {count} runtime translation / preservation / title-control checks");
    }
}
namespace DDKoreanPatch
{
    internal static class Plugin { internal static readonly TestLog Log=new TestLog(); }
    internal class TestLog {
        public void LogInfo(object x) { Console.WriteLine(x); }
        public void LogWarning(object x) { throw new Exception(x.ToString()); }
        public void LogError(object x) { throw new Exception(x.ToString()); }
    }
}
