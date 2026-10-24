#!/usr/bin/env python3
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INSTALLER = PROJECT_ROOT / "install.sh"
NEW_EXECUTABLE = PROJECT_ROOT / "luogu-submit"
OLD_EXECUTABLE = PROJECT_ROOT / "luogu"


class InstallScriptTest(unittest.TestCase):
    def run_installer(self, home: Path):
        environment = os.environ.copy()
        environment.update({"HOME": str(home), "PATH": "/usr/bin:/bin"})
        return subprocess.run(
            [str(INSTALLER)],
            cwd=PROJECT_ROOT,
            env=environment,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def command_paths(self, home: Path):
        bin_dir = home / ".local" / "bin"
        bin_dir.mkdir(parents=True)
        return bin_dir / "luogu-submit", bin_dir / "luogu"

    def test_installs_new_command_and_removes_project_owned_old_link(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            new_command, old_command = self.command_paths(home)
            old_command.symlink_to(OLD_EXECUTABLE)

            result = self.run_installer(home)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(new_command.is_symlink())
            self.assertEqual(os.readlink(new_command), str(NEW_EXECUTABLE))
            self.assertFalse(old_command.is_symlink())
            self.assertIn("已移除旧命令链接", result.stdout)

    def test_preserves_unrelated_old_command_link(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            new_command, old_command = self.command_paths(home)
            unrelated_target = home / "unrelated-luogu"
            old_command.symlink_to(unrelated_target)

            result = self.run_installer(home)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(new_command.is_symlink())
            self.assertTrue(old_command.is_symlink())
            self.assertEqual(os.readlink(old_command), str(unrelated_target))

    def test_failed_install_does_not_remove_old_command_link(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            new_command, old_command = self.command_paths(home)
            new_command.mkdir()
            old_command.symlink_to(OLD_EXECUTABLE)

            result = self.run_installer(home)

            self.assertNotEqual(result.returncode, 0)
            self.assertTrue(new_command.is_dir())
            self.assertTrue(old_command.is_symlink())
            self.assertEqual(os.readlink(old_command), str(OLD_EXECUTABLE))


if __name__ == "__main__":
    unittest.main()
