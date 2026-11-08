#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
coros-connect —— 一键连接 COROS（高驰）MCP
用法:
  python3 connect.py --serve    启动授权流程（打印一条链接，用户点开登录即可）
  python3 connect.py --check    检查现有连接是否可用
  python3 connect.py --verify   打印账号信息与最近一次运动，确认数据通

连接结果保存在 ~/.workbuddy/coros-running-coach/coros_token.json
"""
import argparse
import base64
import hashlib
import html
import json
import os
import platform
import secrets
import stat
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

AUTH_BASE = "https://mcpcn.coros.com"
MCP_URL = f"{AUTH_BASE}/mcp"
TOKEN_URL = f"{AUTH_BASE}/oauth2/token"
REGISTER_URL = f"{AUTH_BASE}/connect/register"
SCOPE = "openid mcp.tools offline_access"

HOME = os.path.expanduser("~")
DATA_DIR = os.path.join(HOME, ".workbuddy", "coros-running-coach")
TOKEN_FILE = os.path.join(DATA_DIR, "coros_token.json")
CLIENT_FILE = os.path.join(DATA_DIR, "coros_client.json")
BIN_DIR = os.path.join(DATA_DIR, "bin")
PROFILE_FILE = os.path.join(DATA_DIR, "profile.json")
os.makedirs(DATA_DIR, exist_ok=True)

# 2.3.1 只读白名单：以下工具会写入用户高驰账号或涉及敏感生理数据，
# 默认一律拦截，必须显式 --allow-write 且事先取得用户明确同意。
WRITE_TOOLS = {
    "uploadRouteFile", "createScheduledWorkout", "updateScheduledWorkout",
    "createTrainingPlan", "updateTrainingPlan", "createSingleWorkout",
    "scheduleWorkout", "updateWorkoutDetails",
}
SENSITIVE_TOOLS = {"queryMenstruationCycles"}

MIRRORS = [
    "https://ghfast.top/",
    "https://gh-proxy.com/",
    "https://ghproxy.net/",
    "",
]


# ---------------------------------------------------------------- 基础
def log(msg):
    print(msg, flush=True)


def env_flag(name):
    return os.environ.get("COROS_" + name, "").strip()


def post_json(url, payload, headers=None, form=False):
    if form:
        data = urllib.parse.urlencode(payload).encode()
        hdr = {"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"}
    else:
        data = json.dumps(payload).encode()
        hdr = {"Content-Type": "application/json", "Accept": "application/json"}
    hdr.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=hdr, method="POST")
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read().decode())


def pkce_pair():
    v = base64.urlsafe_b64encode(secrets.token_bytes(48)).decode().rstrip("=")
    c = base64.urlsafe_b64encode(hashlib.sha256(v.encode()).digest()).decode().rstrip("=")
    return v, c


# ---------------------------------------------------------------- 令牌
def load_token():
    try:
        with open(TOKEN_FILE) as f:
            return json.load(f)
    except Exception:
        return None


def save_token(tok):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(TOKEN_FILE, "w") as f:
        json.dump(tok, f, indent=2)
    try:
        os.chmod(TOKEN_FILE, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass


def refresh_token(tok):
    rt = tok.get("refresh_token")
    if not rt:
        return None
    try:
        c = json.load(open(CLIENT_FILE))
    except (OSError, ValueError):
        log("[WARN] 客户端注册信息缺失或损坏，无法自动续期")
        return None
    try:
        new = post_json(TOKEN_URL, {
            "grant_type": "refresh_token",
            "refresh_token": rt,
            "client_id": c["client_id"],
        }, form=True)
    except Exception:
        return None
    if new.get("refresh_token") is None:
        new["refresh_token"] = rt
    save_token(new)
    return new


def valid_token():
    tok = load_token()
    if not tok:
        return None
    return tok


# ---------------------------------------------------------------- MCP
def unwrap_text(txt):
    """MCP 有时把结果再包一层 JSON 字符串，这里解掉，保证换行是真换行。"""
    s = (txt or "").strip()
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        try:
            out = json.loads(s)
            if isinstance(out, str):
                return out
        except Exception:
            pass
    return txt


def guard_tool(name, allow_write):
    """2.3.1：所有取数路径统一经过这里，写工具/敏感工具默认拦截。"""
    if name in WRITE_TOOLS and not allow_write:
        log(f"[BLOCKED] {name} 会写入你的高驰账号（创建/修改训练计划、课表或上传路线）。")
        log("必须先向用户说明并取得明确同意，再加 --allow-write 执行。")
        return False
    if name in SENSITIVE_TOOLS and not allow_write:
        log(f"[BLOCKED] {name} 涉及敏感生理数据，需用户明确同意后加 --allow-write。")
        return False
    return True


class Mcp:
    def __init__(self, token, allow_write=False):
        self.token = token
        self.allow_write = allow_write

    def _call(self, payload, timeout=40):
        hdr = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "Authorization": f"Bearer {self.token}",
            "MCP-Protocol-Version": "2025-06-18",
        }
        req = urllib.request.Request(MCP_URL, data=json.dumps(payload).encode(), headers=hdr, method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode()
        return raw

    def tool(self, name, args=None):
        if not guard_tool(name, self.allow_write):
            raise PermissionError(f"tool blocked: {name}")
        payload = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                   "params": {"name": name, "arguments": args or {}}}
        raw = self._call(payload)
        try:
            j = json.loads(raw)
            content = j["result"].get("content", [])
            txt = "\n".join(x.get("text", "") for x in content if x.get("type") == "text")
        except Exception:
            return raw
        return unwrap_text(txt)

    def whoami(self):
        txt = self.tool("queryUserInfo")
        return txt

    def list_tools(self):
        raw = self._call({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
        try:
            return json.loads(raw)["result"]["tools"]
        except Exception:
            return []


# ---------------------------------------------------------------- cloudflared
def bin_name():
    sysname = platform.system().lower()
    mach = platform.machine().lower()
    arm = mach in ("aarch64", "arm64")
    if sysname.startswith("win"):
        return "cloudflared-windows-amd64.exe"
    if sysname == "darwin":
        return "cloudflared-darwin-arm64" if arm else "cloudflared-darwin-amd64"
    return "cloudflared-linux-arm64" if arm else "cloudflared-linux-amd64"


def ensure_cloudflared():
    os.makedirs(BIN_DIR, exist_ok=True)
    target = os.path.join(BIN_DIR, "cloudflared" + (".exe" if os.name == "nt" else ""))
    if os.path.exists(target) and os.path.getsize(target) > 5_000_000:
        return target
    name = bin_name()
    log("[..] 首次使用，正在下载隧道组件（约 40MB，仅一次）...")
    for prefix in MIRRORS:
        url = prefix + f"https://github.com/cloudflare/cloudflared/releases/latest/download/{name}"
        try:
            tmp = target + ".part"
            with urllib.request.urlopen(url, timeout=180) as r, open(tmp, "wb") as f:
                while True:
                    chunk = r.read(1 << 20)
                    if not chunk:
                        break
                    f.write(chunk)
            if os.path.getsize(tmp) > 5_000_000:
                os.replace(tmp, target)
                if os.name != "nt":
                    os.chmod(target, os.stat(target).st_mode | stat.S_IEXEC)
                return target
        except Exception:
            continue
    raise RuntimeError("隧道组件下载失败，请检查网络后重试")


def start_tunnel(binary, port):
    proc = subprocess.Popen(
        [binary, "tunnel", "--url", f"http://localhost:{port}", "--no-autoupdate"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
    )
    url, deadline = None, time.time() + 90
    while time.time() < deadline:
        line = proc.stdout.readline()
        if not line:
            if proc.poll() is not None:
                break
            continue
        if "trycloudflare.com" in line:
            for token in line.replace("|", " ").split():
                if token.startswith("https://") and "trycloudflare.com" in token:
                    url = token.strip()
                    break
        if url:
            break
    if not url:
        try:
            proc.kill()
        except Exception:
            pass
        raise RuntimeError("公网隧道建立失败（可能需要允许出站 7844/UDP 或 443）")
    threading.Thread(target=lambda: proc.wait(), daemon=True).start()
    return url, proc


# ---------------------------------------------------------------- 授权页
STYLE = """
body{margin:0;display:flex;align-items:center;justify-content:center;min-height:100vh;background:#f6f8fb;
font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"PingFang SC","Microsoft YaHei",sans-serif;color:#1a1a1a}
.card{background:#fff;border-radius:18px;padding:42px 34px;max-width:420px;width:86%;text-align:center;
box-shadow:0 8px 40px rgba(0,60,140,.10)}
h1{font-size:21px;margin:0 0 10px}p{color:#5b6b7f;font-size:14px;line-height:1.7;margin:6px 0}
.btn{display:block;margin-top:26px;background:#0072CE;color:#fff;text-decoration:none;padding:15px;
border-radius:12px;font-size:16px;font-weight:600}
.icon{width:64px;height:64px;border-radius:50%;background:#e8f4ff;color:#0072CE;font-size:34px;
line-height:64px;margin:0 auto 20px}
small{display:block;margin-top:16px;color:#93a2b3;font-size:12px}
.who{font-size:15px;color:#1a1a1a;font-weight:600;margin-top:2px}
.rec{margin-top:20px;background:#f5f9fd;border-radius:12px;padding:14px 16px;text-align:left}
.rec span{display:block;font-size:12px;color:#8fa2b5;margin-bottom:5px}
.rec strong{font-size:15px;color:#0072CE;font-weight:600}
.next{margin-top:22px;border-top:1px solid #eef2f7;padding-top:20px}
.next p{margin:0 0 8px}
.next .t{font-size:15px;font-weight:600;color:#1a1a1a}
.cmd{background:#0072CE;color:#fff;border-radius:10px;padding:12px;font-size:15px;
font-weight:600;margin-top:12px}
.alt{margin-top:10px;font-size:13px;color:#5b6b7f}
"""


def page(inner, title="高驰连接"):
    return ('<!doctype html><html lang="zh"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            f"<title>{title}</title><style>{STYLE}</style></head>"
            f'<body><div class="card">{inner}</div></body></html>')


def fetch_profile(token):
    """授权后立刻做一次真实读取，确认通道可用。失败不影响保存令牌。"""
    import datetime as _dt
    import re as _re
    out = {"who": "高驰账号已授权", "rec": "", "ok": False}
    try:
        m = Mcp(token)
        info = m.tool("queryUserInfo")
        nick = _re.search(r"Nickname:\s*(.+)", info or "")
        hgt = _re.search(r"Height:\s*([\d.]+)", info or "")
        wgt = _re.search(r"Weight:\s*([\d.]+)", info or "")
        bits = []
        if nick:
            bits.append(nick.group(1).strip().strip('"').strip())
        if hgt and wgt:
            bits.append(f"{hgt.group(1)}cm · {wgt.group(1)}kg")
        if bits:
            out["who"] = " · ".join(bits)

        today = _dt.date.today()
        start = (today - _dt.timedelta(days=30)).strftime("%Y%m%d")
        rec = m.tool("querySportRecords", {
            "startDate": start, "endDate": today.strftime("%Y%m%d"),
            "sportTypeCodes": [100, 101, 102, 103], "limit": 30,
        })
        best = None
        hits = list(_re.finditer(r"^\s*\d+\.\s.*?—\s*(\d{4}-\d{2}-\d{2})", rec or "", _re.M))
        for i, h in enumerate(hits):
            end = hits[i + 1].start() if i + 1 < len(hits) else len(rec)
            seg = rec[h.start():end]
            dist = _re.search(r"Distance:\s*([\d.]+)\s*km", seg)
            if not dist:
                continue
            pace = _re.search(r"Average Pace:\s*([\d:]+)", seg)
            if best is None or h.group(1) > best[0]:
                best = (h.group(1), dist.group(1), pace.group(1) if pace else "")
        if best:
            line = f"{best[0][5:]} · {best[1]}km"
            if best[2]:
                line += f" · {best[2]}/km"
            out["rec"] = line
        out["ok"] = True
    except Exception as e:
        out["err"] = str(e)[:80]
    return out


def success_inner(p):
    if p.get("rec"):
        rec = ('<div class="rec"><span>最近一次跑步 · 已实际读取验证</span>'
               f'<strong>{p["rec"]}</strong></div>')
    elif p.get("ok"):
        rec = ('<div class="rec"><span>数据通道</span>'
               '<strong>已打通，暂无近期记录</strong></div>')
    else:
        rec = ('<div class="rec"><span>数据通道</span>'
               '<strong>授权成功，读取验证稍后在对话里完成</strong></div>')
    return (
        '<div class="icon">&#10003;</div>'
        "<h1>连接成功</h1>"
        f'<p class="who">{p["who"]}</p>'
        + rec +
        '<div class="next">'
        '<p class="t">现在可以关掉这个页面了</p>'
        '<p class="alt">回到对话框，直接说：</p>'
        '<div class="cmd">「分析我最近一次跑步」</div>'
        '<p class="alt">也可以说：「帮我排下周课表」</p>'
        "</div>"
        "<small>数据只保存在本机 · 可随时在高驰 App 解除授权</small>"
    )


def fail_inner(msg):
    return (
        '<div class="icon" style="background:#fff2f0;color:#d9534f">!</div>'
        "<h1>授权没完成</h1>"
        f"<p>{msg}</p>"
        '<div class="next">'
        '<p class="t">回到对话框说一句：</p>'
        '<div class="cmd">「重新连接高驰」</div>'
        "</div>"
    )


class AuthFlow:
    def __init__(self, port):
        self.port = port
        self.sessions = {}
        self.client = None
        self.done = threading.Event()
        self.error = None

    def public_base(self):
        return self.base.rstrip("/")

    def make_handler(self):
        flow = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def send_html(self, body, code=200):
                raw = body.encode("utf-8")
                self.send_response(code)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def do_GET(self):
                u = urllib.parse.urlparse(self.path)
                q = urllib.parse.parse_qs(u.query)

                if u.path in ("/", "/start"):
                    verifier, challenge = pkce_pair()
                    state = base64.urlsafe_b64encode(secrets.token_bytes(16)).decode().rstrip("=")
                    flow.sessions[state] = verifier
                    params = {
                        "response_type": "code",
                        "client_id": flow.client["client_id"],
                        "redirect_uri": flow.client["redirect_uri"],
                        "scope": SCOPE,
                        "code_challenge": challenge,
                        "code_challenge_method": "S256",
                        "state": state,
                    }
                    auth = f"{AUTH_BASE}/oauth2/authorize?" + urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
                    inner = ("<h1>连接你的高驰账号</h1>"
                             "<p>点下面按钮，登录高驰账号并同意授权。<br>密码只在官方域名输入。</p>"
                             f'<a class="btn" href="{auth}">去授权</a>'
                             "<small>授权范围：读取训练、睡眠、恢复数据</small>")
                    self.send_html(page(inner))
                    log(f"[AUTH_URL] {flow.public_base()}/start")
                    return

                if u.path == "/callback":
                    code = (q.get("code") or [""])[0]
                    state = (q.get("state") or [""])[0]
                    err = (q.get("error") or [""])[0]
                    if err or not code or state not in flow.sessions:
                        flow.error = err or "授权信息不完整或已过期"
                        self.send_html(page(fail_inner(html.escape(flow.error)), "授权未完成"), 400)
                        flow.done.set()
                        return
                    try:
                        tok = post_json(TOKEN_URL, {
                            "grant_type": "authorization_code",
                            "code": code,
                            "redirect_uri": flow.client["redirect_uri"],
                            "client_id": flow.client["client_id"],
                            "code_verifier": flow.sessions.pop(state),
                        }, form=True)
                    except urllib.error.HTTPError as e:
                        flow.error = f"换取令牌失败 HTTP {e.code}"
                        self.send_html(page(fail_inner(html.escape(flow.error)), "授权未完成"), 400)
                        flow.done.set()
                        return
                    save_token(tok)
                    log("[VERIFY] 正在读取账号与最近一次运动，确认通道可用...")
                    prof = fetch_profile(tok["access_token"])
                    if prof.get("ok"):
                        log(f"[VERIFIED] {prof['who']}" + (f" | {prof['rec']}" if prof.get("rec") else ""))
                    else:
                        log(f"[WARN] 读取验证失败：{prof.get('err', '未知')}")
                    self.send_html(page(success_inner(prof), "连接成功"))
                    log("[CONNECTED] 授权完成，令牌已保存")
                    flow.done.set()
                    return

                self.send_html(page("<h1>页面不存在</h1>"), 404)

            def do_HEAD(self):
                self.send_response(200)
                self.end_headers()

        return H


def run_serve(force=False):
    tok = load_token()
    if tok and not force:
        log("[..] 检测到已有令牌，正在验证...")
        try:
            m = Mcp(tok["access_token"])
            info = m.whoami()
            if "error" not in info.lower()[:40]:
                log("[READY] 已经连接过了，无需重新授权")
                log(info.strip()[:400])
                return 0
        except Exception:
            pass
        log("[..] 令牌已失效，走重新授权")

    binary = ensure_cloudflared()

    # 选端口
    port = 8410
    for p in range(8410, 8460):
        import socket
        s = socket.socket()
        try:
            s.bind(("127.0.0.1", p))
            port = p
            break
        except OSError:
            continue
        finally:
            s.close()

    log(f"[..] 启动本地回调服务 :{port}")
    flow = AuthFlow(port)
    server = ThreadingHTTPServer(("0.0.0.0", port), flow.make_handler())
    threading.Thread(target=server.serve_forever, daemon=True).start()

    log("[..] 启动公网隧道...")
    url, proc = start_tunnel(binary, port)
    log(f"[TUNNEL] {url}")

    # 注册客户端
    redirect = f"{url}/callback"
    try:
        cli = post_json(REGISTER_URL, {
            "redirect_uris": [redirect],
            "token_endpoint_auth_method": "none",
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "client_name": "WorkBuddy Running Coach",
        })
    except Exception as e:
        log(f"[FAIL] 客户端注册失败：{e}")
        return 1
    cli["redirect_uri"] = redirect
    with open(CLIENT_FILE, "w") as f:
        json.dump(cli, f, indent=2)
    flow.client = cli
    flow.base = url

    log(f"[AUTH_URL] {url}/start")
    log("[..] 等待用户在浏览器完成授权（最长 15 分钟）...")

    ok = flow.done.wait(900)
    try:
        if proc:
            proc.terminate()
    except Exception:
        pass

    if not ok or flow.error:
        log(f"[FAIL] {flow.error or '等待超时，请重新发起'}")
        return 1

    tok = load_token()
    try:
        m = Mcp(tok["access_token"])
        log("[VERIFY] 正在读取账号信息...")
        log(m.whoami().strip()[:400])
    except Exception as e:
        log(f"[WARN] 令牌已保存，但验证请求失败：{e}")
    log("[READY] 连接完成")
    return 0


def run_check():
    tok = load_token()
    if not tok:
        log("[NO_TOKEN] 尚未连接，需要授权")
        return 1
    try:
        info = Mcp(tok["access_token"]).whoami()
        low = (info or "").lower()
        if any(k in low for k in ("401", "unauthorized", "invalid_token", "token expired")):
            raise RuntimeError("token expired")
        log("[OK] 连接可用")
        log(info.strip()[:400])
        return 0
    except Exception:
        new = refresh_token(tok)
        if not new:
            log("[EXPIRED] 令牌失效且无法自动续期，需要重新授权")
            return 1
        try:
            log("[OK] 已自动续期")
            log(Mcp(new["access_token"]).whoami().strip()[:400])
            return 0
        except Exception as e:
            log(f"[EXPIRED] 续期后仍不可用：{e}")
            return 1


def run_verify():
    tok = load_token()
    if not tok:
        log("[NO_TOKEN] 尚未连接")
        return 1
    try:
        m = Mcp(tok["access_token"])
        log("=== 账号 ===")
        log(m.whoami().strip()[:500])
        log("")
        log("=== 最近 1 次运动 ===")
        import datetime
        today = datetime.date.today()
        start = (today - datetime.timedelta(days=14)).strftime("%Y%m%d")
        log(m.tool("querySportRecords", {
            "startDate": start, "endDate": today.strftime("%Y%m%d"),
            "sportTypeCodes": [100, 101, 102, 103], "limit": 1,
        }).strip()[:600])
        return 0
    except Exception as e:
        log(f"[FAIL] 读取失败：{e}")
        return 1


# ---------------------------------------------------------------- 数据查询
def _ymd(offset=0):
    import datetime
    return (datetime.date.today() + datetime.timedelta(days=offset)).strftime("%Y%m%d")


def mcp(allow_write=False):
    """返回可用的 Mcp 实例；令牌过期会先尝试自动续期。"""
    tok = load_token()
    if not tok:
        log("[NO_TOKEN] 尚未连接，请先授权：python3 connect.py --serve")
        sys.exit(1)
    m = Mcp(tok["access_token"], allow_write=allow_write)
    try:
        if not m.whoami().strip():
            raise RuntimeError("empty")
    except Exception:
        new = refresh_token(tok)
        if not new:
            log("[EXPIRED] 令牌失效，需要重新授权：python3 connect.py --serve")
            sys.exit(1)
        m = Mcp(new["access_token"], allow_write=allow_write)
    return m


def cmd_recent(days=30, limit=50):
    m = mcp()
    log(m.tool("querySportRecords", {
        "startDate": _ymd(-days), "endDate": _ymd(),
        "sportTypeCodes": [100, 101, 102, 103], "limit": limit,
    }))
    return 0


def cmd_detail(label_id, sport_type=100):
    m = mcp()
    log(m.tool("getActivityDetail", {"labelId": label_id, "sportType": sport_type}))
    return 0


def cmd_laps(label_id, sport_type=100, raw=False):
    m = mcp()
    txt = m.tool("queryActivityLapData", {"labelId": label_id, "sportType": sport_type})
    if raw:
        log(txt)
        return 0
    try:
        j = json.loads(txt)
    except Exception:
        log(txt)
        return 0

    groups = j.get("lapGroups") or []
    g = next((x for x in groups if x.get("lapDistance") == 100000), None) \
        or (groups[0] if groups else None)
    if not g:
        log(txt)
        return 0

    def pace(sec):
        try:
            sec = round(float(sec))
        except Exception:
            return "-"
        return f"{sec // 60}:{sec % 60:02d}"

    log(f"# 分段表（每圈 {g.get('lapDistance', 0) / 100000:.1f}km，共 {len(g['laps'])} 圈）")
    log("圈  距离km  配速    均心 最大心 步频 步幅m 触地ms 垂比% 功率")
    for L in g["laps"]:
        dist = L.get("distance", 0) / 100000
        log("%2d  %6.2f  %6s  %4s %5s %4s %5.2f %5s %5s %4s" % (
            L.get("lapIndex", 0), dist, pace(L.get("avgPace")),
            L.get("avgHr", "-"), L.get("maxHr", "-"), L.get("avgCadence", "-"),
            (L.get("avgStrideLength") or 0) / 100, L.get("groundTime", "-"),
            L.get("strideRatio", "-"), L.get("avgPower", "-")))
    return 0


def cmd_sleep(days=2):
    m = mcp()
    log(m.tool("querySleepOverview", {"days": days}))
    return 0


def cmd_tools():
    m = mcp()
    for t in m.list_tools():
        req = (t.get("inputSchema") or {}).get("required") or []
        tag = ""
        if t['name'] in WRITE_TOOLS:
            tag = "  [WRITE 需 --allow-write]"
        elif t['name'] in SENSITIVE_TOOLS:
            tag = "  [SENSITIVE 需 --allow-write]"
        log(f"- {t['name']}  required={req}{tag}")
    return 0


def cmd_call(name, args=None, allow_write=False):
    try:
        m = mcp(allow_write=allow_write)
        log(m.tool(name, args or {}))
    except PermissionError:
        return 2
    return 0


def cmd_context(days=14):
    """一次拉齐复盘所需的全部上下文，省去 AI 多次往返。"""
    m = mcp()
    blocks = [
        ("账号", "queryUserInfo", {}),
        ("最近运动", "querySportRecords", {
            "startDate": _ymd(-days), "endDate": _ymd(),
            "sportTypeCodes": [100, 101, 102, 103], "limit": 10}),
        ("睡眠", "querySleepOverview", {"days": 3}),
        ("睡眠HRV", "querySleepHrv", {"days": 7}),
        ("静息心率", "queryRestingHeartRate", {"days": 14}),
        ("恢复状态", "queryRecoveryStatus", {}),
        ("全天活动/交叉负荷", "queryDailyHealthData", {"days": 2}),
        ("训练负荷", "queryTrainingLoadAssessment", {"days": 42}),
        ("体能评估", "queryFitnessAssessmentOverview", {}),
    ]
    for title, name, args in blocks:
        log(f"\n===== {title} =====")
        try:
            log(m.tool(name, args).strip()[:2500])
        except Exception as e:
            log(f"[WARN] {name} 读取失败：{e}")
    return 0


# ---------------------------------------------------------------- 天气 / 档案 / 赛历 (2.3.1)
def cmd_weather(lat, lon, date=None):
    """逐小时气象（气温/湿度/露点/风）+ 热应激判定。
    2.3.1 起天气由脚本实际取数，不再依赖模型自行编造；坐标取自 --recent 的 Start Coordinates。"""
    import datetime
    if date is None:
        date = datetime.date.today().isoformat()
    url = ("https://api.open-meteo.com/v1/forecast?"
           f"latitude={lat}&longitude={lon}"
           "&hourly=temperature_2m,relative_humidity_2m,dew_point_2m,apparent_temperature,wind_speed_10m"
           f"&start_date={date}&end_date={date}&timezone=Asia%2FShanghai")
    try:
        with urllib.request.urlopen(url, timeout=25) as r:
            d = json.load(r)
    except Exception as e:
        log(f"[FAIL] 天气接口不可用：{e}")
        return 1
    h = d.get("hourly") or {}
    if not h.get("time"):
        log("[FAIL] 天气接口未返回逐小时数据")
        return 1
    log(f"# {date} 逐小时气象（{lat}, {lon}）— 来源 api.open-meteo.com，非现场实测")
    log("时刻   气温    体感    湿度   露点    风速     热应激判定（依据 weather_adjustment.md §3）")
    for i, t in enumerate(h["time"]):
        temp, rh = h["temperature_2m"][i], h["relative_humidity_2m"][i]
        dew, app = h["dew_point_2m"][i], h["apparent_temperature"][i]
        wind = h["wind_speed_10m"][i]
        if (temp > 22 and rh > 70) or dew > 18:
            flag = "闷热潮湿档，同等配速心率代偿 +5~10 bpm"
        elif dew > 15:
            flag = "略闷，代偿 +3~6 bpm"
        else:
            flag = "舒适"
        log(f"{t[11:16]}  {temp:>5}°C {app:>6}°C {rh:>5}% {dew:>6}°C {wind:>6}km/h  {flag}")
    return 0


def load_profile():
    try:
        with open(PROFILE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def cmd_profile_show():
    p = load_profile()
    if p is None:
        log("[NO_PROFILE] 尚无个人档案。字段格式见 references/profile_schema.md；"
            "可用 --profile-set '{\"location\":{\"city\":\"深圳\"}}' 逐步建立。")
        return 1
    log(json.dumps(p, ensure_ascii=False, indent=2))
    return 0


def cmd_profile_set(payload):
    """按 JSON 合并写入本地档案；支持点路径键，如 {"goal.target_race.race_date":"2026-12-13"}。"""
    try:
        patch = json.loads(payload)
    except Exception as e:
        log(f"[FAIL] 参数不是合法 JSON：{e}")
        return 1
    if not isinstance(patch, dict):
        log("[FAIL] 参数必须是 JSON 对象")
        return 1
    p = load_profile() or {}
    for k, v in patch.items():
        if "." in k:
            cur = p
            parts = k.split(".")
            for part in parts[:-1]:
                cur = cur.setdefault(part, {})
            cur[parts[-1]] = v
        else:
            p[k] = v
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(PROFILE_FILE, "w", encoding="utf-8") as f:
        json.dump(p, f, ensure_ascii=False, indent=2)
    try:
        os.chmod(PROFILE_FILE, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass
    log(f"[OK] 档案已更新：{PROFILE_FILE}")
    log(json.dumps(p, ensure_ascii=False, indent=2))
    return 0


def cmd_countdown():
    """赛历倒计时。2.3.1 起明确：本技能不内置赛事日历，日期必须由 profile.json 提供。"""
    import datetime
    p = load_profile()
    race = ((p or {}).get("goal") or {}).get("target_race") or {}
    raw = race.get("race_date")
    if not raw:
        log("[NO_RACE_DATE] 本技能不内置赛历，无法由「北马」等简称自动推出日期。"
            "请在 profile.json 填 goal.target_race.race_date（YYYY-MM-DD），"
            "例：--profile-set '{\"goal.target_race.race_date\":\"2026-12-13\"}'")
        return 1
    try:
        rd = datetime.date.fromisoformat(raw)
    except ValueError:
        log(f"[FAIL] race_date 格式错误：{raw}（应为 YYYY-MM-DD）")
        return 1
    today = datetime.date.today()
    days = (rd - today).days
    weeks = days / 7.0
    if days < 0:
        phase = "赛事已结束"
    elif weeks > 12:
        phase = "Base 基础期"
    elif weeks > 8:
        phase = "Build 提高期"
    elif weeks > 4:
        phase = "Peak 巅峰期"
    else:
        phase = "Taper 减量期"
    log(f"# 赛历倒计时 — {race.get('name') or race.get('alias') or '目标赛事'}")
    log(f"比赛日 {rd} | 今天 {today} | 剩余 {days} 天（约 {weeks:.1f} 周）| 建议阶段 {phase}")
    log("注：阶段划分为本技能经验规则（>12 / 8-12 / 4-8 / <4 周），非 Daniels / Pfitzinger 原法，"
        "请以实际周期化计划为准。")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="高驰连接与数据读取")
    ap.add_argument("--serve", action="store_true", help="启动授权流程并打印链接")
    ap.add_argument("--check", action="store_true", help="检查连接是否可用")
    ap.add_argument("--verify", action="store_true", help="打印账号与最近一次运动")
    ap.add_argument("--force", action="store_true", help="忽略已有令牌，强制重新授权")
    ap.add_argument("--context", action="store_true", help="一次拉齐复盘所需全部数据")
    ap.add_argument("--recent", type=int, nargs="?", const=30, metavar="DAYS",
                    help="最近运动记录（默认 30 天）")
    ap.add_argument("--detail", metavar="LABEL_ID", help="单次运动详情，需同时给 --sport")
    ap.add_argument("--laps", metavar="LABEL_ID", help="单次运动分段，需同时给 --sport")
    ap.add_argument("--sleep", type=int, nargs="?", const=2, metavar="DAYS",
                    help="睡眠概览（默认 2 天）")
    ap.add_argument("--sport", type=int, default=100, help="运动类型码，默认 100 跑步")
    ap.add_argument("--raw", action="store_true", help="--laps 时输出原始 JSON")
    ap.add_argument("--tools", action="store_true", help="列出全部可用工具")
    ap.add_argument("--call", nargs="+", metavar="TOOL", help="调用任意工具：--call 名称 ['{json}']")
    ap.add_argument("--allow-write", action="store_true",
                    help="放行写工具/敏感工具；必须先取得用户明确同意")
    ap.add_argument("--limit", type=int, default=50, help="--recent 返回条数上限（默认 50）")
    ap.add_argument("--weather", nargs="+", metavar="ARG",
                    help="逐小时气象：--weather 纬度 经度 [YYYY-MM-DD]")
    ap.add_argument("--profile-show", action="store_true", help="查看本地个人档案")
    ap.add_argument("--profile-set", metavar="JSON", help="按 JSON 合并写入本地个人档案")
    ap.add_argument("--countdown", action="store_true", help="读取档案比赛日计算倒计时周数")
    a = ap.parse_args()

    if a.weather:
        if len(a.weather) < 2:
            log("[FAIL] --weather 需要至少 纬度 经度 两个参数")
            sys.exit(1)
        sys.exit(cmd_weather(a.weather[0], a.weather[1],
                             a.weather[2] if len(a.weather) > 2 else None))
    if a.profile_show:
        sys.exit(cmd_profile_show())
    if a.profile_set is not None:
        sys.exit(cmd_profile_set(a.profile_set))
    if a.countdown:
        sys.exit(cmd_countdown())
    if a.context:
        sys.exit(cmd_context())
    if a.recent is not None:
        sys.exit(cmd_recent(a.recent, a.limit))
    if a.detail is not None:
        sys.exit(cmd_detail(a.detail, a.sport))
    if a.laps is not None:
        sys.exit(cmd_laps(a.laps, a.sport, a.raw))
    if a.sleep is not None:
        sys.exit(cmd_sleep(a.sleep))
    if a.tools:
        sys.exit(cmd_tools())
    if a.call:
        extra = {}
        if len(a.call) > 1:
            try:
                extra = json.loads(a.call[1])
            except Exception as e:
                log(f"[FAIL] 参数不是合法 JSON：{e}")
                sys.exit(1)
        sys.exit(cmd_call(a.call[0], extra, a.allow_write))
    if a.check:
        sys.exit(run_check())
    if a.verify:
        sys.exit(run_verify())
    sys.exit(run_serve(a.force))
