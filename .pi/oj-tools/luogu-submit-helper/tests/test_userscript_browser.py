#!/usr/bin/env python3
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
USERSCRIPT = PROJECT_ROOT / "userscripts" / "luogu-submit-helper.user.js"
TOKEN = "abcdefghijklmnopqrstuvwxyz0123456789ABCDEFG"


NATIVE_FIXTURE = """<!doctype html>
<html>
<head><meta charset="utf-8"><title>Luogu fixture</title></head>
<body>
  <div class="sidebar-container">
    <main class="main">
      <div class="burger">
        <div class="body" data-luogu-submit-root>
          <select class="lang-select" id="language">
            <option value="cpp14">C++14 (GCC 9)</option>
            <option value="cpp20">C++20 (GCC 13)</option>
            <option value="python3">Python 3</option>
          </select>
          <textarea id="editor"></textarea>
          __BUTTONS__
        </div>
      </div>
    </main>
  </div>
  <script>
    window.__clicks = 0;
    document.querySelectorAll('[data-submit]').forEach(button => {
      button.addEventListener('click', event => {
        event.preventDefault();
        window.__clicks += 1;
      });
    });
  </script>
</body>
</html>
"""


CUSTOM_FIXTURE = """<!doctype html>
<html>
<head><meta charset="utf-8"><title>Luogu custom fixture</title></head>
<body>
  <div class="sidebar-container">
    <main class="main">
      <div class="burger">
        <div class="body" data-luogu-submit-root>
          <div class="combo-wrapper lang-select" role="combobox" tabindex="0">
            C++14 (GCC 9)
          </div>
          <div class="dropdown" style="display:none">
            <button class="item" data-language="cpp14">C++14 (GCC 9)</button>
            <button class="item" data-language="cpp20">C++20 (GCC 13)</button>
          </div>
          <textarea id="editor"></textarea>
          <button type="button" data-submit>提交评测</button>
        </div>
      </div>
    </main>
  </div>
  <script>
    window.__clicks = 0;
    window.__selectedLanguage = '';
    const control = document.querySelector('[role="combobox"]');
    const dropdown = document.querySelector('.dropdown');
    control.addEventListener('click', () => { dropdown.style.display = 'block'; });
    document.querySelectorAll('[data-language]').forEach(option => {
      option.addEventListener('click', () => {
        window.__selectedLanguage = option.dataset.language;
        control.textContent = option.textContent;
        dropdown.style.display = 'none';
      });
    });
    document.querySelector('[data-submit]').addEventListener('click', event => {
      event.preventDefault();
      window.__clicks += 1;
    });
  </script>
</body>
</html>
"""


CODEMIRROR6_FIXTURE = """<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Luogu CodeMirror 6 fixture</title>
  <style>
    .cm-editor { width: 600px; height: 320px; }
    .cm-content { min-height: 300px; }
  </style>
</head>
<body>
  <div class="sidebar-container">
    <main class="main">
      <div class="burger">
        <div class="body" data-luogu-submit-root>
          <select class="lang-select" id="language">
            <option value="cpp14">C++14 (GCC 9)</option>
            <option value="cpp20">C++20 (GCC 13)</option>
          </select>
          <div class="cm-editor">
            <div class="cm-content" contenteditable="true" role="textbox"></div>
          </div>
          <button type="button" data-submit>提交评测</button>
        </div>
      </div>
    </main>
  </div>
  <script>
    window.__clicks = 0;
    window.__cmState = 'old editor content';
    window.__cmSelectedAll = false;
    window.__cmHandlePaste = true;
    window.__cmHandleCopy = true;
    const content = document.querySelector('.cm-content');
    const render = () => {
      content.replaceChildren();
      for (const line of window.__cmState.split('\\n')) {
        const element = document.createElement('div');
        element.className = 'cm-line';
        element.textContent = line || '\\u00a0';
        content.appendChild(element);
      }
    };
    render();
    content.addEventListener('keydown', event => {
      if (event.key.toLowerCase() === 'a' && (event.ctrlKey || event.metaKey)) {
        event.preventDefault();
        window.__cmSelectedAll = true;
      }
    });
    content.addEventListener('paste', event => {
      if (!window.__cmHandlePaste) return;
      event.preventDefault();
      const pasted = event.clipboardData.getData('text/plain');
      window.__cmState = window.__cmSelectedAll
        ? pasted
        : window.__cmState + pasted;
      window.__cmSelectedAll = false;
      render();
    });
    content.addEventListener('copy', event => {
      if (!window.__cmHandleCopy) return;
      event.preventDefault();
      if (window.__cmSelectedAll) {
        event.clipboardData.setData('text/plain', window.__cmState);
      }
    });
    document.querySelector('[data-submit]').addEventListener('click', event => {
      event.preventDefault();
      window.__clicks += 1;
    });
  </script>
</body>
</html>
"""


class UserscriptBrowserTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as error:
            raise unittest.SkipTest(f"Playwright unavailable: {error}")
        cls.playwright = sync_playwright().start()
        try:
            cls.browser = cls.playwright.chromium.launch(headless=True)
        except Exception as error:
            cls.playwright.stop()
            raise unittest.SkipTest(f"Chromium unavailable: {error}")

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()

    def make_task(self, **overrides):
        task = {
            "problem_id": "P1001",
            "source_name": "main.cpp",
            "language": "C++20",
            "code": "#include <iostream>\nint main() { return 0; }\n",
        }
        task.update(overrides)
        return task

    def run_userscript(self, task, html, page_problem="P1001", setup_script=None):
        context = self.browser.new_context(viewport={"width": 1000, "height": 700})
        self.addCleanup(context.close)
        page = context.new_page()
        page.route(
            "https://www.luogu.com.cn/problem/**",
            lambda route: route.fulfill(
                status=200,
                content_type="text/html; charset=utf-8",
                body=html,
            ),
        )
        url = (
            f"https://www.luogu.com.cn/problem/{page_problem}"
            f"?luogu-submit-port=32123&luogu-submit-token={TOKEN}#submit"
        )
        page.goto(url, wait_until="domcontentloaded")
        page.evaluate(
            """task => {
                window.__task = task;
                window.__result = null;
                window.__requests = [];
                window.GM_xmlhttpRequest = options => {
                    window.__requests.push({
                        method: options.method,
                        url: options.url,
                        data: options.data || null,
                    });
                    window.setTimeout(() => {
                        if (options.url.includes('/task?')) {
                            options.onload({
                                status: 200,
                                responseText: JSON.stringify(window.__task),
                            });
                            return;
                        }
                        if (options.url.includes('/result?')) {
                            window.__result = JSON.parse(options.data);
                            options.onload({ status: 200, responseText: '{"ok": true}' });
                            return;
                        }
                        options.onload({ status: 404, responseText: '{"error": "unknown"}' });
                    }, 0);
                };
            }""",
            task,
        )
        if setup_script:
            page.evaluate(setup_script)
        page.add_script_tag(path=str(USERSCRIPT))
        page.wait_for_function("window.__result !== null", timeout=5000)
        return page

    def test_native_select_fills_code_and_clicks_once(self):
        html = NATIVE_FIXTURE.replace(
            "__BUTTONS__",
            '<button type="button" data-submit>提交评测</button>',
        )
        task = self.make_task()

        page = self.run_userscript(task, html)

        self.assertEqual(page.locator("#language").input_value(), "cpp20")
        self.assertEqual(page.locator("#editor").input_value(), task["code"])
        self.assertEqual(page.evaluate("window.__clicks"), 1)
        self.assertEqual(page.evaluate("window.__result.status"), "submit_clicked")
        self.assertNotIn("luogu-submit-token", page.url)

    def test_custom_language_control_selects_cpp20(self):
        task = self.make_task()

        page = self.run_userscript(task, CUSTOM_FIXTURE)

        self.assertEqual(page.evaluate("window.__selectedLanguage"), "cpp20")
        self.assertEqual(page.locator("#editor").input_value(), task["code"])
        self.assertEqual(page.evaluate("window.__clicks"), 1)
        self.assertEqual(page.evaluate("window.__result.status"), "submit_clicked")

    def test_english_submit_to_judge_button_clicks_once(self):
        html = NATIVE_FIXTURE.replace(
            "__BUTTONS__",
            '<button type="button" data-submit>Submit to Judge</button>',
        )

        page = self.run_userscript(self.make_task(), html)

        self.assertEqual(page.evaluate("window.__clicks"), 1)
        self.assertEqual(page.evaluate("window.__result.status"), "submit_clicked")

    def test_codemirror6_replaces_and_reads_back_complete_code(self):
        task = self.make_task(
            code=(
                "#include <iostream>\n"
                "int main() {\n"
                "    std::cout << 3 << '\\n';\n"
                "    return 0;\n"
                "}\n"
            )
        )

        page = self.run_userscript(task, CODEMIRROR6_FIXTURE)

        self.assertEqual(page.locator("#language").input_value(), "cpp20")
        self.assertEqual(page.evaluate("window.__cmState"), task["code"])
        self.assertEqual(page.evaluate("window.__clicks"), 1)
        self.assertEqual(page.evaluate("window.__result.status"), "submit_clicked")

    def test_codemirror6_unhandled_paste_reports_error_without_clicking(self):
        page = self.run_userscript(
            self.make_task(),
            CODEMIRROR6_FIXTURE,
            setup_script="() => { window.__cmHandlePaste = false; }",
        )

        self.assertEqual(page.evaluate("window.__clicks"), 0)
        self.assertEqual(page.evaluate("window.__result.status"), "error")
        self.assertIn("未处理粘贴事件", page.evaluate("window.__result.message"))

    def test_codemirror6_unhandled_copy_reports_error_without_clicking(self):
        page = self.run_userscript(
            self.make_task(),
            CODEMIRROR6_FIXTURE,
            setup_script="() => { window.__cmHandleCopy = false; }",
        )

        self.assertEqual(page.evaluate("window.__clicks"), 0)
        self.assertEqual(page.evaluate("window.__result.status"), "error")
        self.assertIn("未处理复制事件", page.evaluate("window.__result.message"))

    def test_problem_mismatch_reports_error_without_clicking(self):
        html = NATIVE_FIXTURE.replace(
            "__BUTTONS__",
            '<button type="button" data-submit>提交评测</button>',
        )

        page = self.run_userscript(self.make_task(), html, page_problem="P1002")

        self.assertEqual(page.evaluate("window.__clicks"), 0)
        self.assertEqual(page.evaluate("window.__result.status"), "error")
        self.assertIn("不一致", page.evaluate("window.__result.message"))

    def test_language_mismatch_reports_error_without_clicking(self):
        html = NATIVE_FIXTURE.replace(
            '<option value="cpp20">C++20 (GCC 13)</option>',
            '',
        ).replace(
            "__BUTTONS__",
            '<button type="button" data-submit>提交评测</button>',
        )

        page = self.run_userscript(self.make_task(), html)

        self.assertEqual(page.evaluate("window.__clicks"), 0)
        self.assertEqual(page.evaluate("window.__result.status"), "error")
        self.assertIn("语言选择控件", page.evaluate("window.__result.message"))

    def test_editor_mismatch_reports_error_without_clicking(self):
        html = NATIVE_FIXTURE.replace(
            '<textarea id="editor"></textarea>',
            '<div class="CodeMirror" id="editor"></div>',
        ).replace(
            "__BUTTONS__",
            '<button type="button" data-submit>提交评测</button>',
        )
        setup_script = """() => {
            const element = document.querySelector('.CodeMirror');
            let value = '';
            element.CodeMirror = {
                setValue(code) { value = `${code}changed`; },
                getValue() { return value; },
            };
        }"""

        page = self.run_userscript(
            self.make_task(),
            html,
            setup_script=setup_script,
        )

        self.assertEqual(page.evaluate("window.__clicks"), 0)
        self.assertEqual(page.evaluate("window.__result.status"), "error")
        self.assertIn("回读校验失败", page.evaluate("window.__result.message"))

    def test_ambiguous_submit_buttons_report_error_without_clicking(self):
        html = NATIVE_FIXTURE.replace(
            "__BUTTONS__",
            """
            <button type="button" data-submit>提交评测</button>
            <button type="button" data-submit>提交代码</button>
            """,
        )

        page = self.run_userscript(self.make_task(), html)

        self.assertEqual(page.evaluate("window.__clicks"), 0)
        self.assertEqual(page.evaluate("window.__result.status"), "error")
        self.assertIn("不唯一", page.evaluate("window.__result.message"))

    def test_submit_file_label_is_not_treated_as_judge_button(self):
        html = NATIVE_FIXTURE.replace(
            "__BUTTONS__",
            '<button type="button" data-submit>提交文件</button>',
        )

        page = self.run_userscript(self.make_task(), html)

        self.assertEqual(page.evaluate("window.__clicks"), 0)
        self.assertEqual(page.evaluate("window.__result.status"), "error")
        self.assertIn("找不到", page.evaluate("window.__result.message"))

    def test_normal_problem_page_is_inert(self):
        html = NATIVE_FIXTURE.replace(
            "__BUTTONS__",
            '<button type="button" data-submit>提交评测</button>',
        )
        context = self.browser.new_context(viewport={"width": 1000, "height": 700})
        self.addCleanup(context.close)
        page = context.new_page()
        page.route(
            "https://www.luogu.com.cn/problem/**",
            lambda route: route.fulfill(
                status=200,
                content_type="text/html; charset=utf-8",
                body=html,
            ),
        )
        page.goto(
            "https://www.luogu.com.cn/problem/P1001#submit",
            wait_until="domcontentloaded",
        )
        page.evaluate(
            """() => {
                window.__requestCount = 0;
                window.GM_xmlhttpRequest = () => { window.__requestCount += 1; };
            }"""
        )

        page.add_script_tag(path=str(USERSCRIPT))
        page.wait_for_timeout(200)

        self.assertEqual(page.evaluate("window.__requestCount"), 0)
        self.assertEqual(page.evaluate("window.__clicks"), 0)


if __name__ == "__main__":
    unittest.main()
