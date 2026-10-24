// ==UserScript==
// @name         洛谷单题提交助手
// @namespace    https://github.com/rainboy/luogu-submit-helper
// @version      1.0.3
// @description  接收本机 luogu-submit 命令的一次性任务，填写代码并点击提交
// @author       Rainboy
// @match        https://www.luogu.com.cn/problem/*
// @grant        GM_xmlhttpRequest
// @connect      127.0.0.1
// @run-at       document-idle
// ==/UserScript==

(function() {
    'use strict';

    const PORT_PARAM = 'luogu-submit-port';
    const TOKEN_PARAM = 'luogu-submit-token';
    const TASK_TIMEOUT_MS = 15000;
    const CONTROL_TIMEOUT_MS = 15000;
    const TOKEN_PATTERN = /^[A-Za-z0-9_-]{40,128}$/;
    const RESULT_STATUSES = new Set(['submit_clicked', 'error']);

    function parseTaskContext() {
        const url = new URL(window.location.href);
        const portText = url.searchParams.get(PORT_PARAM);
        const token = url.searchParams.get(TOKEN_PARAM);
        if (portText === null || token === null) {
            return null;
        }

        const port = Number(portText);
        if (!/^\d+$/.test(portText) || !Number.isInteger(port) || port < 1 || port > 65535) {
            throw new Error('本地任务端口无效');
        }
        if (!TOKEN_PATTERN.test(token)) {
            throw new Error('本地任务令牌无效');
        }

        url.searchParams.delete(PORT_PARAM);
        url.searchParams.delete(TOKEN_PARAM);
        window.history.replaceState(
            window.history.state,
            '',
            `${url.pathname}${url.search}${url.hash}`,
        );
        return { port, token };
    }

    function requestJson(method, url, payload) {
        return new Promise((resolve, reject) => {
            GM_xmlhttpRequest({
                method,
                url,
                headers: payload === undefined
                    ? { Accept: 'application/json' }
                    : {
                        Accept: 'application/json',
                        'Content-Type': 'application/json',
                    },
                data: payload === undefined ? undefined : JSON.stringify(payload),
                timeout: TASK_TIMEOUT_MS,
                onload(response) {
                    let body;
                    try {
                        body = JSON.parse(response.responseText || '{}');
                    } catch (_error) {
                        reject(new Error(`本地服务返回了无效 JSON（HTTP ${response.status}）`));
                        return;
                    }
                    if (response.status < 200 || response.status >= 300) {
                        reject(new Error(body.error || `本地服务返回 HTTP ${response.status}`));
                        return;
                    }
                    resolve(body);
                },
                onerror() {
                    reject(new Error('无法连接本地 luogu-submit 服务'));
                },
                ontimeout() {
                    reject(new Error('连接本地 luogu-submit 服务超时'));
                },
            });
        });
    }

    function taskUrl(context, path) {
        return `http://127.0.0.1:${context.port}${path}?token=${encodeURIComponent(context.token)}`;
    }

    function reportResult(context, status, message) {
        if (!RESULT_STATUSES.has(status)) {
            return Promise.reject(new Error('userscript 产生了无效状态'));
        }
        return requestJson('POST', taskUrl(context, '/result'), { status, message });
    }

    function showStatus(message, kind) {
        const existing = document.getElementById('luogu-submit-helper-status');
        if (existing) {
            existing.remove();
        }
        const status = document.createElement('div');
        status.id = 'luogu-submit-helper-status';
        status.textContent = `洛谷提交助手: ${message}`;
        const colors = {
            error: '#b42318',
            success: '#18794e',
            working: '#24292f',
        };
        Object.assign(status.style, {
            position: 'fixed',
            top: '16px',
            right: '16px',
            zIndex: '2147483647',
            maxWidth: 'min(420px, calc(100vw - 32px))',
            padding: '10px 12px',
            borderRadius: '6px',
            background: colors[kind] || colors.working,
            color: '#fff',
            fontSize: '14px',
            lineHeight: '1.5',
            boxShadow: '0 4px 14px rgba(0, 0, 0, 0.22)',
            whiteSpace: 'normal',
            overflowWrap: 'anywhere',
        });
        document.documentElement.appendChild(status);
        const lifetime = kind === 'error' ? 15000 : 6000;
        window.setTimeout(() => status.remove(), lifetime);
    }

    function normalizeLabel(value) {
        return value.normalize('NFKC').replace(/\s+/g, ' ').trim().toUpperCase();
    }

    function languageMatches(label, language) {
        const value = normalizeLabel(label);
        switch (language) {
        case 'C++20':
            return /(^|[^A-Z0-9])C\+\+\s*20([^0-9]|$)/.test(value);
        case 'Python 3':
            return /(^|[^A-Z])PYTHON\s*3([^0-9]|$)/.test(value);
        case 'C':
            return /^C(?:\s|\(|$)/.test(value) && !value.startsWith('C++');
        case 'Java':
            return /^JAVA(?:\s|\(|$)/.test(value);
        case 'JavaScript':
            return /^(?:JAVASCRIPT|NODE(?:\.?JS)?)(?:\s|\(|$)/.test(value);
        case 'Rust':
            return /^RUST(?:\s|\(|$)/.test(value);
        case 'Haskell':
            return /^HASKELL(?:\s|\(|$)/.test(value);
        default:
            return false;
        }
    }

    function isVisible(element) {
        if (!(element instanceof Element)) {
            return false;
        }
        const style = window.getComputedStyle(element);
        if (style.display === 'none' || style.visibility === 'hidden') {
            return false;
        }
        const rectangle = element.getBoundingClientRect();
        return rectangle.width > 0 && rectangle.height > 0;
    }

    function waitFor(findValue, description, timeout = CONTROL_TIMEOUT_MS) {
        const started = Date.now();
        return new Promise((resolve, reject) => {
            function check() {
                try {
                    const value = findValue();
                    if (value) {
                        resolve(value);
                        return;
                    }
                } catch (error) {
                    reject(error);
                    return;
                }
                if (Date.now() - started >= timeout) {
                    reject(new Error(`等待${description}超时`));
                    return;
                }
                window.setTimeout(check, 100);
            }
            check();
        });
    }

    function getSubmissionRoot() {
        return document.querySelector('.sidebar-container .main .burger .body')
            || document.querySelector('.sidebar-container .main')
            || document.querySelector('[data-luogu-submit-root]')
            || document.body;
    }

    function activateSubmissionPanel() {
        const safeTabs = Array.from(document.querySelectorAll(
            'a[href$="#submit"], [role="tab"][href$="#submit"], [role="tab"][data-tab="submit"]',
        ));
        const tab = safeTabs.find(isVisible);
        if (tab) {
            tab.click();
        }
    }

    function chooseUnique(matches, description) {
        if (matches.length === 0) {
            throw new Error(`找不到${description}`);
        }
        if (matches.length > 1) {
            throw new Error(`${description}不唯一（找到 ${matches.length} 个）`);
        }
        return matches[0];
    }

    async function selectNativeLanguage(root, language) {
        const selects = Array.from(new Set([
            ...root.querySelectorAll('select.lang-select, .lang-select select, select[name*="lang" i]'),
        ]));
        const matches = [];
        for (const select of selects) {
            for (const option of Array.from(select.options)) {
                if (languageMatches(option.textContent || option.label || '', language)) {
                    matches.push({ select, option });
                }
            }
        }
        if (matches.length === 0) {
            return false;
        }
        const match = chooseUnique(matches, `${language} 语言选项`);
        const setter = Object.getOwnPropertyDescriptor(
            HTMLSelectElement.prototype,
            'value',
        ).set;
        setter.call(match.select, match.option.value);
        match.select.dispatchEvent(new Event('input', { bubbles: true }));
        match.select.dispatchEvent(new Event('change', { bubbles: true }));
        await new Promise(resolve => window.setTimeout(resolve, 50));
        if (!languageMatches(match.select.selectedOptions[0]?.textContent || '', language)) {
            throw new Error(`${language} 语言选择未生效`);
        }
        return true;
    }

    function customLanguageOptions(language) {
        const selectors = [
            '[role="option"]',
            '.dropdown .item',
            '.dropdown li',
            '.menu .item',
            '.select-options .option',
            '.combo-options .option',
            '.combo-wrapper.lang-select [role="menuitem"]',
            '.combo-wrapper.lang-select [data-value]',
            '.combo-wrapper.lang-select li',
            '.combo-wrapper.lang-select button',
        ];
        const all = Array.from(new Set(document.querySelectorAll(selectors.join(','))))
            .filter(element => isVisible(element))
            .filter(element => languageMatches(element.textContent || '', language));
        return all.filter(
            element => !all.some(other => other !== element && element.contains(other)),
        );
    }

    async function selectCustomLanguage(root, language) {
        const controls = Array.from(new Set([
            ...root.querySelectorAll(
                '.combo-wrapper.lang-select, .lang-select[role="combobox"], [class*="language"][role="combobox"]',
            ),
        ])).filter(isVisible);
        const control = chooseUnique(controls, '语言选择控件');
        control.click();
        const options = await waitFor(
            () => {
                const current = customLanguageOptions(language);
                return current.length > 0 ? current : null;
            },
            `${language} 语言选项`,
            3000,
        );
        const option = chooseUnique(options, `${language} 语言选项`);
        option.click();
        await new Promise(resolve => window.setTimeout(resolve, 100));
    }

    async function selectLanguage(language) {
        const root = getSubmissionRoot();
        if (await selectNativeLanguage(root, language)) {
            return;
        }
        await selectCustomLanguage(root, language);
    }

    function settleEditorState() {
        return new Promise(resolve => window.setTimeout(resolve, 50));
    }

    async function selectAllCodeMirror6(content) {
        content.focus();
        const platform = navigator.userAgentData?.platform || navigator.platform || '';
        const mac = /Mac|iPhone|iPad|iPod/i.test(platform);
        const event = new KeyboardEvent('keydown', {
            key: 'a',
            code: 'KeyA',
            ctrlKey: !mac,
            metaKey: mac,
            bubbles: true,
            cancelable: true,
        });
        content.dispatchEvent(event);
        if (!event.defaultPrevented) {
            throw new Error('CodeMirror 6 未处理全选快捷键');
        }
        await settleEditorState();
    }

    function createClipboardTransfer() {
        if (typeof window.DataTransfer !== 'function') {
            throw new Error('浏览器不支持 DataTransfer，无法操作 CodeMirror 6');
        }
        try {
            return new window.DataTransfer();
        } catch (_error) {
            throw new Error('无法创建 DataTransfer，无法操作 CodeMirror 6');
        }
    }

    function dispatchCodeMirror6Clipboard(content, type, transfer) {
        if (typeof window.ClipboardEvent !== 'function') {
            throw new Error('浏览器不支持 ClipboardEvent，无法操作 CodeMirror 6');
        }
        let event;
        try {
            event = new window.ClipboardEvent(type, {
                clipboardData: transfer,
                bubbles: true,
                cancelable: true,
            });
        } catch (_error) {
            throw new Error(`无法创建 CodeMirror 6 ${type} 事件`);
        }
        content.dispatchEvent(event);
        if (!event.defaultPrevented) {
            const action = type === 'paste' ? '粘贴' : '复制';
            throw new Error(`CodeMirror 6 未处理${action}事件`);
        }
    }

    function codeMirror6Editor(root) {
        const contents = Array.from(root.querySelectorAll(
            '.cm-editor .cm-content[contenteditable="true"]',
        )).filter(isVisible);
        if (contents.length === 0) {
            return null;
        }
        const content = chooseUnique(contents, 'CodeMirror 6 代码编辑器');
        return {
            async setValue(code) {
                await selectAllCodeMirror6(content);
                const transfer = createClipboardTransfer();
                transfer.setData('text/plain', code);
                dispatchCodeMirror6Clipboard(content, 'paste', transfer);
                await settleEditorState();
            },
            async getValue() {
                await selectAllCodeMirror6(content);
                const transfer = createClipboardTransfer();
                dispatchCodeMirror6Clipboard(content, 'copy', transfer);
                await settleEditorState();
                return transfer.getData('text/plain');
            },
        };
    }

    function codeMirrorEditor() {
        const element = document.querySelector('.CodeMirror');
        const editor = element?.CodeMirror;
        if (!editor || typeof editor.setValue !== 'function' || typeof editor.getValue !== 'function') {
            return null;
        }
        return {
            setValue(code) { editor.setValue(code); },
            getValue() { return editor.getValue(); },
        };
    }

    function aceEditor() {
        const element = document.querySelector('.ace_editor');
        let editor = element?.env?.editor;
        if (!editor && element && window.ace) {
            try {
                editor = window.ace.edit(element);
            } catch (_error) {
                return null;
            }
        }
        if (!editor || typeof editor.setValue !== 'function' || typeof editor.getValue !== 'function') {
            return null;
        }
        return {
            setValue(code) { editor.setValue(code, -1); },
            getValue() { return editor.getValue(); },
        };
    }

    function monacoEditor() {
        const models = window.monaco?.editor?.getModels?.() || [];
        if (models.length !== 1) {
            return null;
        }
        return {
            setValue(code) { models[0].setValue(code); },
            getValue() { return models[0].getValue(); },
        };
    }

    function textareaEditor(root) {
        const textareas = Array.from(root.querySelectorAll('textarea')).filter(isVisible);
        if (textareas.length === 0) {
            return null;
        }
        const textarea = chooseUnique(textareas, '代码输入框');
        const setter = Object.getOwnPropertyDescriptor(
            HTMLTextAreaElement.prototype,
            'value',
        ).set;
        return {
            setValue(code) {
                setter.call(textarea, code);
                textarea.dispatchEvent(new Event('input', { bubbles: true }));
                textarea.dispatchEvent(new Event('change', { bubbles: true }));
            },
            getValue() { return textarea.value; },
        };
    }

    function findEditor() {
        const root = getSubmissionRoot();
        return codeMirror6Editor(root)
            || codeMirrorEditor()
            || aceEditor()
            || monacoEditor()
            || textareaEditor(root);
    }

    async function fillAndVerifyCode(code) {
        const editor = await waitFor(findEditor, '代码编辑器');
        await editor.setValue(code);
        await new Promise(resolve => window.setTimeout(resolve, 100));
        if ((await editor.getValue()) !== code) {
            throw new Error('代码写入后的回读校验失败');
        }
    }

    function submitButtonText(element) {
        if (element instanceof HTMLInputElement) {
            return normalizeLabel(element.value || '');
        }
        return normalizeLabel(element.textContent || '');
    }

    function findSubmitButton() {
        const root = getSubmissionRoot();
        const expected = new Set([
            '提交',
            '提交答案',
            '提交代码',
            '提交评测',
            'SUBMIT',
            'SUBMIT ANSWER',
            'SUBMIT CODE',
            'SUBMIT TO JUDGE',
        ]);
        const buttons = Array.from(new Set([
            ...root.querySelectorAll('button, input[type="submit"]'),
        ])).filter(element => (
            isVisible(element)
            && !element.disabled
            && element.getAttribute('aria-disabled') !== 'true'
            && expected.has(submitButtonText(element))
        ));
        return chooseUnique(buttons, '可用的提交按钮');
    }

    function pageProblemId() {
        const match = window.location.pathname.match(/^\/problem\/([^/]+)\/?$/);
        if (!match) {
            throw new Error('当前页面不是洛谷题目页');
        }
        return decodeURIComponent(match[1]).toUpperCase();
    }

    function validateTask(task) {
        if (!task || typeof task !== 'object') {
            throw new Error('本地任务格式无效');
        }
        for (const key of ['problem_id', 'source_name', 'language', 'code']) {
            if (typeof task[key] !== 'string') {
                throw new Error(`本地任务缺少 ${key}`);
            }
        }
        if (pageProblemId() !== task.problem_id.toUpperCase()) {
            throw new Error(`页面题号 ${pageProblemId()} 与任务题号 ${task.problem_id} 不一致`);
        }
    }

    async function run(context) {
        let claimed = false;
        try {
            showStatus('正在读取本地提交任务', 'working');
            const task = await requestJson('GET', taskUrl(context, '/task'));
            claimed = true;
            validateTask(task);
            activateSubmissionPanel();
            await selectLanguage(task.language);
            await fillAndVerifyCode(task.code);
            const button = findSubmitButton();
            button.click();
            await reportResult(
                context,
                'submit_clicked',
                `${task.problem_id} / ${task.source_name}`,
            );
            showStatus('已点击提交按钮', 'success');
        } catch (error) {
            const message = error instanceof Error ? error.message : String(error);
            showStatus(message, 'error');
            console.error('[luogu-submit-helper]', error);
            if (claimed) {
                try {
                    await reportResult(context, 'error', message);
                } catch (reportError) {
                    console.error('[luogu-submit-helper] 无法回报错误', reportError);
                }
            }
        }
    }

    let context;
    try {
        context = parseTaskContext();
    } catch (error) {
        showStatus(error instanceof Error ? error.message : String(error), 'error');
        return;
    }
    if (!context || window.__LUOGU_SUBMIT_HELPER_RUNNING__) {
        return;
    }
    window.__LUOGU_SUBMIT_HELPER_RUNNING__ = true;
    run(context);
})();
