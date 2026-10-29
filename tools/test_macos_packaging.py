"""실제 Steam 파일 없이 설치 백업·경로·인수 전달을 확인한다."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from make_macos_release import extract, build_launcher
from make_release import game_dir
import zipfile

SCRIPTS = Path(__file__).resolve().parent.parent / "packaging/macos"


class MacOSPackagingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ddkorean test 한글 ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.payload = self.root / "patch"
        self.game = self.root / "Database Detective"
        self.payload.mkdir()
        managed = self.game / "copOS.app/Contents/Resources/Data/Managed"
        managed.mkdir(parents=True)
        (managed / "Scripts.dll").touch()
        self.plugin = "BepInEx/plugins/DDKoreanPatch"
        for name in ("run_bepinex.sh", "libdoorstop.dylib", "BepInEx/core/BepInEx.dll",
                     "DDKoreanPatch.app/Contents/Info.plist", "DDKoreanPatch.app/Contents/MacOS/DDKoreanPatch",
                     "BepInEx/core/BepInEx.Preloader.dll", f"{self.plugin}/DDKoreanPatch.dll",
                     f"{self.plugin}/translation.json", f"{self.plugin}/fonts/neodgm.ttf",
                     f"{self.plugin}/fonts/LICENSE.txt"):
            path = self.payload / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("new")
        for name in ("install_macos.command", "run_korean_patch.command"):
            shutil.copy2(SCRIPTS / name, self.payload / name)
        # Linux CI에서도 macOS 분기를 실행하되 실제 프로세스에 접근하지 않는다.
        self.bin = self.root / "bin"
        self.bin.mkdir()
        for name, body in (("uname", "echo Darwin"), ("pgrep", "exit 1")):
            path = self.bin / name
            path.write_text(f"#!/bin/sh\n{body}\n")
            path.chmod(0o755)
        self.env = dict(os.environ, PATH=f"{self.bin}:{os.environ['PATH']}")

    def install(self):
        return subprocess.run(["bash", str(self.payload / "install_macos.command"), str(self.game)],
                              env=self.env, capture_output=True, text=True)

    def test_preserves_config_other_mods_and_backs_up_replaced_files(self):
        for name, content in ((f"{self.plugin}/DDKoreanPatch.dll", "old"),
                              ("BepInEx/config/custom.cfg", "user settings"),
                              ("BepInEx/plugins/OtherMod.dll", "other mod")):
            path = self.game / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.game / self.plugin / "DDKoreanPatch.dll").read_text(), "new")
        backups = list((self.game / ".ddkorean-backups").glob(f"*/{self.plugin}/DDKoreanPatch.dll"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(), "old")
        self.assertEqual((self.game / "BepInEx/config/custom.cfg").read_text(), "user settings")
        self.assertEqual((self.game / "BepInEx/plugins/OtherMod.dll").read_text(), "other mod")
        self.assertIn(f'"{self.game}/DDKoreanPatch.app" %command%', result.stdout)
        self.assertTrue(os.access(self.game / "run_korean_patch.command", os.X_OK))
        self.assertEqual(self.install().returncode, 0)

    @unittest.skipUnless(sys.platform == "darwin" and shutil.which("xcrun"), "macOS 빌드 도구 필요")
    def test_native_app_launcher_forwards_arguments(self):
        build_launcher(self.root)
        script = self.root / "run_korean_patch.command"
        script.write_text('#!/bin/bash\nprintf "%s\\n" "$@"\n')
        executable = self.root / "DDKoreanPatch.app/Contents/MacOS/DDKoreanPatch"
        for arguments in ([], [str(self.game / "copOS.app"), "--test", "한글 two words"]):
            result = subprocess.run([str(executable), *arguments], cwd="/", capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.splitlines(), arguments or [""])

    def test_incomplete_payload_does_not_install(self):
        (self.payload / self.plugin / "fonts/neodgm.ttf").unlink()
        self.assertNotEqual(self.install().returncode, 0)
        self.assertFalse((self.game / "BepInEx").exists())

    def test_running_game_does_not_install(self):
        (self.bin / "pgrep").write_text("#!/bin/sh\nexit 0\n")
        self.assertNotEqual(self.install().returncode, 0)
        self.assertFalse((self.game / "BepInEx").exists())

    def test_launcher_preserves_arguments_and_handles_no_arguments(self):
        self.assertEqual(self.install().returncode, 0)
        (self.game / "run_bepinex.sh").write_text('#!/bin/sh\nprintf "%s\\n" "$@"\n')
        launcher = ["bash", str(self.game / "run_korean_patch.command")]
        for arguments, expected in (
            ([], [str(self.game / "copOS.app")]),
            (["-logFile", "/tmp/한글 test.log"], [str(self.game / "copOS.app"), "-logFile", "/tmp/한글 test.log"]),
            ([str(self.game / "copOS.app/Contents/MacOS/copOS"), "--test", "two words"],
             [str(self.game / "copOS.app/Contents/MacOS/copOS"), "--test", "two words"]),
        ):
            result = subprocess.run(launcher + arguments, cwd="/", capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.splitlines(), expected)

    def test_zip_cannot_escape_staging(self):
        archive = self.root / "bad.zip"
        with zipfile.ZipFile(archive, "w") as zf:
            zf.writestr("../escape.txt", "bad")
        with self.assertRaises(ValueError):
            extract(archive, self.payload)
        self.assertFalse((self.root / "escape.txt").exists())

    def test_windows_release_still_resolves_its_default(self):
        self.assertTrue(game_dir().startswith("D:\\"))
        self.assertNotIn("$(", game_dir())


if __name__ == "__main__":
    unittest.main()
