"""Build bilingual offline guides from the maintained Markdown source."""
from html import escape
from pathlib import Path
import posixpath
import re

ROOT = Path(__file__).resolve().parents[1]
REPO = 'https://github.com/Alexantry/Ultimate-U1-ACE-link/blob/main/'


def target(url, source, image=False):
    if url.startswith('#'):
        return url
    if re.match(r'https?://', url):
        return url
    if 'before-you-start.zh-CN.md' in url:
        return '#prepare' if '.zh-CN.' in source.name else 'START-HERE.html#prepare'
    if 'quick-start.zh-CN.md' in url or 'README.zh-CN.md' in url:
        return '#start' if '.zh-CN.' in source.name else 'START-HERE.html#start'
    if url == 'installation.md' or url == '../docs/installation.md':
        return 'MANUAL-INSTALL.html'
    sections = {'u1-preparation.md': 'firmware', 'u1-preparation.zh-CN.md': 'firmware',
                'configuration.md': 'parameters', 'configuration.zh-CN.md': 'parameters',
                'nfc.md': 'nfc', 'nfc.zh-CN.md': 'nfc',
                'daily-use.md': 'daily', 'daily-use.zh-CN.md': 'daily',
                'ace-wizard.md': 'ace-firmware', 'ace-wizard.zh-CN.md': 'ace-firmware'}
    if url in sections:
        if ('.zh-CN.' in url) == ('.zh-CN.' in source.name):
            return '#' + sections[url]
        return ('START-HERE.html' if '.zh-CN.' in url else 'START-HERE.en.html') + '#' + sections[url]
    path = posixpath.normpath(str(source.parent.relative_to(ROOT)).replace('\\', '/') + '/' + url)
    return path if image else REPO + path


def inline(text, source):
    saved = []
    def keep(value):
        saved.append(value)
        return '\x00%d\x00' % (len(saved) - 1)
    text = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)',
                  lambda m: keep('<img alt="%s" src="%s">' %
                                 (escape(m[1], quote=True), escape(target(m[2], source, True), quote=True))), text)
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)',
                  lambda m: keep('<a href="%s">%s</a>' %
                                 (escape(target(m[2], source), quote=True), escape(m[1]))), text)
    text = escape(text)
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
    return re.sub(r'\x00(\d+)\x00', lambda m: saved[int(m[1])], text)


def render(source):
    result, listing, table, alert, fence = [], None, False, None, None
    def close():
        nonlocal listing, table, alert
        if listing:
            result.append('</%s>' % listing); listing = None
        if table:
            result.append('</tbody></table></div>'); table = False
        if alert:
            result.append('</aside>'); alert = None
    for line in source.read_text(encoding='utf8').splitlines():
        if fence is None and re.fullmatch(r'<a id="[A-Za-z0-9_-]+"></a>', line):
            close(); result.append(line); continue
        if line.startswith('```'):
            if fence is not None:
                result.append('</code></pre>'); fence = None
            else:
                close(); fence = line[3:].strip()
                result.append('<pre><code>')
            continue
        if fence is not None:
            result.append(escape(line))
            continue
        notice = re.fullmatch(r'> \[!(CAUTION|WARNING|IMPORTANT|NOTE|TIP)\]', line)
        if notice:
            close(); alert = notice[1].lower()
            labels = {'CAUTION': '重要警示', 'WARNING': '警告', 'IMPORTANT': '必须确认', 'NOTE': '说明', 'TIP': '提示'}
            label = labels[notice[1]] if '.zh-CN.' in source.name else notice[1]
            result.append('<aside class="alert %s"><div class="alert-title">%s</div>' % (alert, label))
            continue
        if alert and line.startswith('>'):
            content = line[1:].lstrip()
            if content:
                result.append('<p>' + inline(content, source) + '</p>')
            continue
        if not line.strip():
            close(); continue
        heading = re.match(r'^(#{1,6}) (.+)', line)
        if heading:
            close()
            level = min(len(heading[1]) + 1, 6)
            slug = re.sub(r'[^\w\s-]', '', heading[2].lower())
            slug = re.sub(r'\s+', '-', slug)
            result.append('<h%d id="%s">%s</h%d>' % (level, escape(slug, quote=True), inline(heading[2], source), level)); continue
        if line.startswith('|'):
            cells = [c.strip() for c in line.strip('|').split('|')]
            if all(re.fullmatch(r':?-+:?', c) for c in cells):
                continue
            if not table:
                close(); table = True
                result.append('<div class="table"><table><thead><tr>' + ''.join('<th>' + inline(c, source) + '</th>' for c in cells) + '</tr></thead><tbody>')
            else:
                result.append('<tr>' + ''.join('<td>' + inline(c, source) + '</td>' for c in cells) + '</tr>')
            continue
        item = re.match(r'^(?:\d+\. |(-) )(.+)', line)
        if item:
            kind = 'ul' if item[1] else 'ol'
            if listing != kind:
                close(); listing = kind; result.append('<' + kind + '>')
            result.append('<li>' + inline(item[2], source) + '</li>'); continue
        close(); result.append('<p>' + inline(line, source) + '</p>')
    close()
    if fence is not None:
        raise ValueError('Unclosed code fence: ' + str(source))
    return '\n'.join(result)


def main():
    quick = render(ROOT / 'docs/quick-start.zh-CN.md')
    critical = re.search(r'<aside class="alert caution">.*?</aside>', quick, re.S)[0]
    quick = quick.replace(critical, '', 1)
    prepare = render(ROOT / 'docs/before-you-start.zh-CN.md')
    page = '''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>从这里开始 · Ultimate U1-ACE link</title>
<style>
:root{color-scheme:light;font-family:"Microsoft YaHei",system-ui,sans-serif;color:#15283e;background:#eff3f8}
*{box-sizing:border-box}body{margin:0}main{max-width:1020px;margin:auto;padding:32px 22px 64px}
header{padding:34px;background:#132d4c;border-radius:20px;color:#fff}header p{color:#dce8f7}h1{font-size:34px;margin:12px 0}
.tag{font-size:14px;letter-spacing:2px;color:#93c6ff}h2{font-size:27px;margin-top:12px}h3{font-size:24px;margin-top:32px}h4{font-size:20px}
p,li,td,th{font-size:17px;line-height:1.8}li{margin:8px 0}a{color:#125dc2;text-underline-offset:3px}header a{color:#b2dbff}
section,details{background:#fff;border:1px solid #dbe4ef;border-radius:18px;padding:28px;margin-top:24px}
summary{cursor:pointer;font-size:23px;font-weight:bold}summary small{display:block;font-size:15px;font-weight:normal;margin-top:10px;color:#52657b}
img{display:block;max-width:100%;height:auto;margin:20px auto}code{font-family:Consolas,monospace;background:#edf2f8;padding:2px 6px;border-radius:5px;overflow-wrap:anywhere}
pre{padding:16px;background:#edf2f8;overflow:auto;border-radius:8px;white-space:pre}pre code{padding:0;background:none;overflow-wrap:normal}
.routes{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:24px}.routes a{display:block;padding:24px;border:3px solid #125dc2;border-radius:14px;background:#fff;font-size:21px;font-weight:800;text-decoration:none}.routes a:last-child{border-color:#375143;color:#214e34;background:#effbf3}.routes small{display:block;font-size:15px;font-weight:400;margin-top:10px}
table{border-collapse:collapse;width:100%}td,th{border:1px solid #d6e0ed;padding:12px;text-align:left;vertical-align:top}th{background:#edf3fa}.table{overflow:auto}
.steps{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-top:24px}.steps div{background:#fff;padding:22px;border-radius:14px;border:1px solid #dbe4ef}.steps b{display:block;font-size:20px;margin-bottom:12px}
.note{background:#e9f6ef;border-left:4px solid #25814b;padding:14px 18px;margin-top:22px}.note p{margin:0}
.alert{padding:18px 22px;border:1px solid #c8d3e2;border-left-width:6px;border-radius:12px;margin:24px 0;background:#f4f7fc}
.alert-title{font-size:19px;font-weight:800;margin-bottom:10px;letter-spacing:.3px}.alert p{margin:8px 0}
.alert.caution{color:#8c1421;background:#fff1f2;border-color:#d42b40}.alert.caution strong{font-weight:800}
.alert.important{color:#41297a;background:#f4f0ff;border-color:#7c55c7}.alert.warning{color:#734200;background:#fff8e6;border-color:#c58100}
footer{padding:22px;color:#52657b;font-size:15px}@media(max-width:700px){.steps,.routes{grid-template-columns:1fr}main{padding:14px}section,details,header{padding:20px}h1{font-size:27px}td,th{min-width:140px}}
@media print{body{background:#fff}section,details,header{break-inside:avoid}header{background:#fff;color:#15283e}details>*{display:block}}
</style></head><body><main>
<header><div class="tag">ULTIMATE U1-ACE LINK · 新手入口 · <a href="START-HERE.en.html">English</a></div><h1>安装不需要编程。</h1>
<p>双击 <strong>START-HERE.cmd</strong>，选择中文或 English。向导可从准备 U1 固件开始；这里是离线说明，不是安装按钮。</p>
<p>由用户提出需求和完成实机测试，使用 <strong>OpenAI Codex</strong> 开发代码、工具及文档。使用者无需安装 Codex。</p></header>
<div class="steps"><div><b>① 已经解压了吗？</b>如果还在压缩包里，先右键压缩文件，选择“全部解压缩”。</div>
<div><b>② 打开这个文件夹</b>找到 START-HERE.cmd，快速点鼠标左键两次。</div>
<div><b>③ 跟着窗口回答</b>输入地址和密码；新装时确认管路长度。向导负责执行命令。</div></div>
<div class="note"><p><strong>External 已自动处理。</strong>向导会设置耗材来源、处理内置读卡服务，并保存备份。受支持标签无需自行寻找或填写 NFC 密钥。</p></div>
<details id="prepare"><summary>机器还没准备好？从这里展开<small>固件、访问开关、网络、线缆和 ACE 代际；已完成的人可以跳过。</small></summary>''' + prepare + '''</details>
<section id="start">''' + quick + '''</section>
<footer>说明中的链接需要网络；本页和步骤示意图可以离线阅读。图为概念示意，不是硬件接线尺寸图。</footer>
</main></body></html>
'''
    routes = '<nav class="routes"><a href="#start">安装向导<small>双击 START-HERE.cmd，按提示准备和安装。</small></a><a href="MANUAL-INSTALL.html">手动安装 · 查看源码<small>完整英文命令步骤；不运行 Windows 向导。</small></a></nav>'
    page = page.replace('</header>', '</header>\n' + routes + critical, 1)
    extra = ''
    for section, name, title in [('firmware', 'u1-preparation.zh-CN.md', 'U1 固件与访问设置'),
                                 ('ace-firmware', 'ace-wizard.zh-CN.md', 'ACE 固件：跟着窗口更新和查询结果'),
                                 ('parameters', 'configuration.zh-CN.md', '料管长度、退料及回送参数'),
                                 ('nfc', 'nfc.zh-CN.md', 'NFC 支持范围与识别流程'),
                                 ('daily', 'daily-use.zh-CN.md', '日常进退料与远程操作'),
                                 ('licensing', 'licensing.zh-CN.md', '使用、分享和再分发许可')]:
        extra += '<details id="%s"><summary>%s</summary>%s</details>' % (section, title, render(ROOT / 'docs' / name))
    page = page.replace('<footer>', extra + '<footer>', 1)
    (ROOT / 'START-HERE.html').write_text(page, encoding='utf8')
    style = re.search(r'<style>(.*?)</style>', page, re.S)[1]
    english_quick = render(ROOT / 'docs/quick-start.md')
    english_critical = re.search(r'<aside class="alert caution">.*?</aside>', english_quick, re.S)[0]
    english_quick = english_quick.replace(english_critical, '', 1)
    english = '''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Start here · Ultimate U1-ACE link</title><style>''' + style + '''</style></head><body><main>
<header><div class="tag">ULTIMATE U1-ACE LINK · <a href="START-HERE.html">简体中文</a></div>
<h1>No programming knowledge is required.</h1>
<p>Double-click <strong>START-HERE.cmd</strong>. Select <strong>2. English</strong>. The wizard can start with U1 firmware preparation.</p>
<p>This is the offline guide. It does not start installation when opened.</p>
<p>Built with <strong>OpenAI Codex</strong>. Installation does not require Codex or an API key.</p></header>
<div class="steps"><div><b>1. Extract all files</b>Right-click the downloaded ZIP. Select Extract All.</div>
<div><b>2. Open the new folder</b>Double-click START-HERE.cmd in the extracted folder.</div>
<div><b>3. Select English</b>Follow the prompts. The launcher enters the commands for you.</div></div>
<div class="note"><p><strong>External detection is automatic.</strong> The installer saves backups, sets External, and verifies the internal-reader service state.</p></div>
<section id="start">''' + english_quick + '''</section>
<footer>Source and reference links require internet access. The instructions on this page are available offline.</footer>
</main></body></html>'''
    routes_en = '<nav class="routes"><a href="#start">GUIDED INSTALLATION<small>Run START-HERE.cmd for preparation and installation prompts.</small></a><a href="MANUAL-INSTALL.html">MANUAL INSTALLATION<small>Read the source and enter the documented commands.</small></a></nav>'
    english = english.replace('</header>', '</header>\n' + routes_en + english_critical, 1)
    extra_en = ''
    for section, name, title in [('firmware', 'u1-preparation.md', 'U1 firmware and access setup'),
                                 ('ace-firmware', 'ace-wizard.md', 'ACE firmware: guided preparation and result checks'),
                                 ('parameters', 'configuration.md', 'Tube lengths and take-up settings'),
                                 ('nfc', 'nfc.md', 'NFC support and recognition'),
                                 ('daily', 'daily-use.md', 'Daily use and remote controls'),
                                 ('licensing', 'licensing.md', 'Use, sharing, and redistribution')]:
        extra_en += '<details id="%s"><summary>%s</summary>%s</details>' % (section, title, render(ROOT / 'docs' / name))
    english = english.replace('<footer>', extra_en + '<footer>', 1)
    (ROOT / 'START-HERE.en.html').write_text(english, encoding='utf8')
    manual = '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Manual installation / 手动安装</title><style>' + style + '</style></head><body><main>'
    manual += '<header><h1>MANUAL INSTALLATION / 手动安装</h1><p>Read the source and enter each command. This page does not execute anything.</p><p>本页提供完整英文命令步骤，不运行 Windows 向导；仍会使用可阅读的 printer installer.py。</p><a href="START-HERE.html">中文说明</a> · <a href="START-HERE.en.html">English guide</a></header>'
    manual += '<section>' + render(ROOT / 'docs/installation.md') + '</section></main></body></html>'
    # Manual links refer to the appropriate online document, not absent inline sections.
    manual = re.sub(r'href="#(?:firmware|ace-firmware|parameters|nfc|daily)"', lambda m: 'href="' + REPO + 'docs/' + {'firmware':'u1-preparation.md','ace-firmware':'ace-wizard.md','parameters':'configuration.md','nfc':'nfc.md','daily':'daily-use.md'}[m[0].split('#')[1].rstrip('"')] + '"', manual)
    (ROOT / 'MANUAL-INSTALL.html').write_text(manual, encoding='utf8')
    print('Built bilingual offline guides and the manual installation entry.')


if __name__ == '__main__':
    main()
