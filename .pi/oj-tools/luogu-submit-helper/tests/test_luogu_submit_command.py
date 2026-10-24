#!/usr/bin/env python3
import importlib.machinery
import importlib.util
import io
import json
import sys
import tempfile
import threading
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit
from urllib.request import Request, urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = PROJECT_ROOT / "luogu-submit"
LOADER = importlib.machinery.SourceFileLoader(
    "luogu_submit_command",
    str(MODULE_PATH),
)
SPEC = importlib.util.spec_from_loader(LOADER.name, LOADER)
luogu_submit = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = luogu_submit
LOADER.exec_module(luogu_submit)


class LuoguSubmitCommandTest(unittest.TestCase):
    def make_problems_root(self, directory):
        root = Path(directory) / "problems"
        (root / "luogu").mkdir(parents=True)
        return root

    def test_config_round_trip_uses_xdg_location_and_absolute_root(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.make_problems_root(directory)
            environment = {
                "HOME": str(Path(directory) / "home"),
                "XDG_CONFIG_HOME": str(Path(directory) / "xdg"),
            }

            path = luogu_submit.write_config(root / ".." / "problems", environment)
            loaded = luogu_submit.load_config(environment)

            self.assertEqual(
                path,
                Path(directory)
                / "xdg"
                / "luogu-submit-helper"
                / "config.json",
            )
            self.assertEqual(loaded, root.resolve())
            self.assertEqual(
                json.loads(path.read_text(encoding="utf-8")),
                {
                    "problems_root": str(root.resolve()),
                    "source_blacklist": ["gen.cpp", "gen.py"],
                },
            )
            self.assertEqual(list(path.parent.glob("*.tmp")), [])

    def test_configured_source_blacklist_extends_required_defaults(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.make_problems_root(directory)
            environment = {"XDG_CONFIG_HOME": str(Path(directory) / "xdg")}

            luogu_submit.write_config(
                root,
                environment,
                source_blacklist=["brute.py", "debug.cpp"],
            )
            settings = luogu_submit.load_settings(environment)

            self.assertEqual(settings.problems_root, root.resolve())
            self.assertEqual(
                settings.source_blacklist,
                frozenset({"gen.py", "gen.cpp", "brute.py", "debug.cpp"}),
            )

    def test_old_config_without_blacklist_uses_required_defaults(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.make_problems_root(directory)
            environment = {"XDG_CONFIG_HOME": str(Path(directory) / "xdg")}
            config_path = luogu_submit.get_config_path(environment)
            config_path.parent.mkdir(parents=True)
            config_path.write_text(
                json.dumps({"problems_root": str(root)}),
                encoding="utf-8",
            )

            settings = luogu_submit.load_settings(environment)

            self.assertEqual(
                settings.source_blacklist,
                luogu_submit.DEFAULT_SOURCE_BLACKLIST,
            )

    def test_blacklist_rejects_paths(self):
        for value in ("tools/gen.py", "tools\\gen.py", "..", ""):
            with self.subTest(value=value):
                with self.assertRaises(luogu_submit.UserError):
                    luogu_submit.validate_source_blacklist([value])

    def test_config_validation_reports_missing_luogu_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(luogu_submit.UserError, "没有 luogu/"):
                luogu_submit.validate_problems_root(directory)

    def test_problem_resolution_normalizes_ids_and_infers_current_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.make_problems_root(directory)
            p1001 = root / "luogu" / "1001"
            b2002 = root / "luogu" / "b2002"
            p1001.mkdir()
            b2002.mkdir()

            p_id, p_dir = luogu_submit.resolve_problem(root, "1001")
            b_id, b_dir = luogu_submit.resolve_problem(root, "b2002")
            inferred_id, inferred_dir = luogu_submit.resolve_problem(root, None, cwd=p1001)

            self.assertEqual((p_id, p_dir), ("P1001", p1001.resolve()))
            self.assertEqual((b_id, b_dir), ("B2002", b2002.resolve()))
            self.assertEqual(
                (inferred_id, inferred_dir),
                ("P1001", p1001.resolve()),
            )

    def test_problem_resolution_rejects_invalid_id_and_unrelated_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.make_problems_root(directory)
            unrelated = Path(directory) / "1001"
            unrelated.mkdir()

            for invalid in ("../1001", "P.1001", " P1001", ""):
                with self.subTest(problem_id=invalid):
                    with self.assertRaises(luogu_submit.UserError):
                        luogu_submit.normalize_problem_id(invalid)
            with self.assertRaisesRegex(luogu_submit.UserError, "当前目录必须"):
                luogu_submit.resolve_problem(root, None, cwd=unrelated)

    def test_problem_resolution_accepts_rbook_prefixed_directories(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.make_problems_root(directory)
            p1119 = root / "luogu" / "P1119"
            b2002 = root / "luogu" / "b2002"
            p1119.mkdir()
            b2002.mkdir()

            for problem_id in ("1119", "P1119", "p1119"):
                with self.subTest(problem_id=problem_id):
                    real_id, problem_dir = luogu_submit.resolve_problem(root, problem_id)
                    self.assertEqual((real_id, problem_dir), ("P1119", p1119.resolve()))

            inferred_id, inferred_dir = luogu_submit.resolve_problem(root, None, cwd=p1119)
            self.assertEqual((inferred_id, inferred_dir), ("P1119", p1119.resolve()))
            self.assertEqual(
                luogu_submit.resolve_problem(root, "B2002"),
                ("B2002", b2002.resolve()),
            )

    def test_problem_resolution_reports_all_candidate_directories(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.make_problems_root(directory)
            with self.assertRaises(luogu_submit.UserError) as context:
                luogu_submit.resolve_problem(root, "1119")
            message = str(context.exception)
            self.assertIn("1119", message)
            self.assertIn("P1119", message)

    def test_source_discovery_is_direct_and_prioritizes_main_files(self):
        with tempfile.TemporaryDirectory() as directory:
            problem = Path(directory)
            (problem / "z.cpp").write_text("z", encoding="utf-8")
            (problem / "answer.rs").write_text("rs", encoding="utf-8")
            (problem / "main.py").write_text("py", encoding="utf-8")
            (problem / "main.CPP").write_text("cpp", encoding="utf-8")
            (problem / "notes.txt").write_text("notes", encoding="utf-8")
            nested = problem / "nested"
            nested.mkdir()
            (nested / "main.c").write_text("c", encoding="utf-8")

            candidates = luogu_submit.discover_sources(problem)

            self.assertEqual(
                [candidate.path.name for candidate in candidates],
                ["main.CPP", "main.py", "answer.rs", "z.cpp"],
            )
            self.assertEqual(
                [candidate.language for candidate in candidates],
                ["C++20", "Python 3", "Rust", "C++20"],
            )

    def test_source_discovery_excludes_default_and_configured_blacklist(self):
        with tempfile.TemporaryDirectory() as directory:
            problem = Path(directory)
            for filename in ("main.cpp", "gen.py", "gen.cpp", "brute.py"):
                (problem / filename).write_text(filename, encoding="utf-8")

            candidates = luogu_submit.discover_sources(
                problem,
                source_blacklist=["brute.py"],
            )

            self.assertEqual(
                [candidate.path.name for candidate in candidates],
                ["main.cpp"],
            )

    def test_config_arguments_accept_blacklist_only_for_config(self):
        args = luogu_submit.parse_arguments([
            "config",
            "/tmp/problems",
            "--blacklist",
            "brute.py",
            "debug.cpp",
        ])

        self.assertEqual(args.source_blacklist, ["brute.py", "debug.cpp"])
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                luogu_submit.parse_arguments(["1001", "--blacklist", "brute.py"])

    def test_source_selection_reprompts_and_supports_cancel(self):
        candidates = [
            luogu_submit.SourceCandidate(Path("main.py"), "Python 3"),
            luogu_submit.SourceCandidate(Path("other.cpp"), "C++20"),
        ]
        answers = iter(["bad", "9", "2"])
        output = io.StringIO()

        chosen = luogu_submit.choose_source(
            candidates,
            input_func=lambda _prompt: next(answers),
            output=output,
        )
        cancelled = luogu_submit.choose_source(
            candidates,
            input_func=lambda _prompt: "q",
            output=io.StringIO(),
        )

        self.assertEqual(chosen, candidates[1])
        self.assertIsNone(cancelled)
        self.assertIn("超出范围", output.getvalue())

    def test_source_selection_defaults_to_first_and_confirmation_requires_empty(self):
        candidate = luogu_submit.SourceCandidate(Path("main.cpp"), "C++20")

        chosen = luogu_submit.choose_source(
            [candidate],
            input_func=lambda _prompt: "",
            output=io.StringIO(),
        )
        confirmed = luogu_submit.confirm_submission(
            "P1001",
            candidate,
            input_func=lambda _prompt: "",
            output=io.StringIO(),
        )
        rejected = luogu_submit.confirm_submission(
            "P1001",
            candidate,
            input_func=lambda _prompt: "yes",
            output=io.StringIO(),
        )

        self.assertEqual(chosen, candidate)
        self.assertTrue(confirmed)
        self.assertFalse(rejected)


class LoopbackProtocolTest(unittest.TestCase):
    def setUp(self):
        self.task = luogu_submit.SubmissionTask(
            problem_id="P1001",
            source_name="main.cpp",
            language="C++20",
            code="#include <iostream>\n",
        )

    def start_server(self, token="test-token"):
        server, state, actual_token = luogu_submit.create_submission_server(
            self.task,
            token=token,
        )
        thread = threading.Thread(
            target=server.serve_forever,
            kwargs={"poll_interval": 0.01},
            daemon=True,
        )
        thread.start()
        self.addCleanup(thread.join, 2)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return server, state, actual_token

    def request_json(self, url, data=None, method=None):
        body = None if data is None else json.dumps(data).encode("utf-8")
        request = Request(
            url,
            data=body,
            method=method,
            headers={"Content-Type": "application/json"},
        )
        with urlopen(request, timeout=2) as response:
            return response.status, json.loads(response.read().decode("utf-8"))

    def test_task_can_be_claimed_once_and_result_is_recorded(self):
        server, state, token = self.start_server()
        base = f"http://127.0.0.1:{server.server_address[1]}"

        status, payload = self.request_json(f"{base}/task?token={token}")
        with self.assertRaises(HTTPError) as duplicate:
            self.request_json(f"{base}/task?token={token}")
        result_status, result_payload = self.request_json(
            f"{base}/result?token={token}",
            data={"status": "submit_clicked", "message": "clicked"},
            method="POST",
        )

        self.assertEqual(status, 200)
        self.assertEqual(payload, self.task.as_payload())
        self.assertEqual(duplicate.exception.code, 409)
        duplicate.exception.close()
        self.assertEqual((result_status, result_payload), (200, {"ok": True}))
        self.assertTrue(state.result_event.wait(1))
        self.assertEqual(state.result.status, "submit_clicked")

    def test_wrong_token_does_not_claim_task(self):
        server, state, token = self.start_server()
        base = f"http://127.0.0.1:{server.server_address[1]}"

        with self.assertRaises(HTTPError) as denied:
            self.request_json(f"{base}/task?token=wrong")
        status, _payload = self.request_json(f"{base}/task?token={token}")

        self.assertEqual(denied.exception.code, 403)
        denied.exception.close()
        self.assertEqual(status, 200)
        self.assertEqual(state.phase, "claimed")

    def test_invalid_and_oversized_results_are_rejected(self):
        server, _state, token = self.start_server()
        base = f"http://127.0.0.1:{server.server_address[1]}"
        self.request_json(f"{base}/task?token={token}")

        with self.assertRaises(HTTPError) as invalid:
            self.request_json(
                f"{base}/result?token={token}",
                data={"status": "unknown", "message": "bad"},
                method="POST",
            )
        oversized_request = Request(
            f"{base}/result?token={token}",
            data=b"x" * (luogu_submit.MAX_RESULT_BODY + 1),
            method="POST",
        )
        with self.assertRaises(HTTPError) as oversized:
            urlopen(oversized_request, timeout=2)

        self.assertEqual(invalid.exception.code, 400)
        self.assertEqual(oversized.exception.code, 413)
        invalid.exception.close()
        oversized.exception.close()

    def test_serve_submission_reports_browser_failure_and_timeout(self):
        output = io.StringIO()

        result = luogu_submit.serve_submission(
            self.task,
            timeout=0.02,
            browser_open=lambda _url: False,
            output=output,
        )

        self.assertEqual(result, 1)
        self.assertIn("请手动打开", output.getvalue())
        self.assertIn("等待 userscript 超时", output.getvalue())

    def test_serve_submission_returns_success_after_userscript_result(self):
        output = io.StringIO()
        client_errors = []
        client_threads = []

        def browser_open(url):
            parsed = urlsplit(url)
            query = parse_qs(parsed.query)
            port = int(query["luogu-submit-port"][0])
            token = query["luogu-submit-token"][0]

            def act_as_userscript():
                try:
                    base = f"http://127.0.0.1:{port}"
                    self.request_json(f"{base}/task?token={token}")
                    self.request_json(
                        f"{base}/result?token={token}",
                        data={
                            "status": "submit_clicked",
                            "message": "P1001 / main.cpp",
                        },
                        method="POST",
                    )
                except Exception as error:
                    client_errors.append(error)

            thread = threading.Thread(target=act_as_userscript)
            client_threads.append(thread)
            thread.start()
            return True

        result = luogu_submit.serve_submission(
            self.task,
            timeout=2,
            browser_open=browser_open,
            output=output,
        )
        for thread in client_threads:
            thread.join(2)

        self.assertEqual(client_errors, [])
        self.assertEqual(result, 0)
        self.assertIn("已点击提交按钮", output.getvalue())


if __name__ == "__main__":
    unittest.main()
