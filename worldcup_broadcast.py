"""
World Cup morning voice broadcast.
Fetches match scores from midnight to 7:00 AM China time, generates Chinese
voice MP3 via edge-tts, and optionally sends a push notification to mobile.

Usage:
  python worldcup_broadcast.py              # normal run
  python worldcup_broadcast.py --sample     # test with sample data
  python worldcup_broadcast.py --push       # run + send push notification

Environment variables for push:
  PUSH_TOKEN     - PushPlus token or Server酱 sendkey
  PUSH_SERVICE   - "pushplus" (default) or "serverchan"
  AUDIO_BASE_URL - Public base URL where web/ files are served (e.g. GitHub Pages)
"""
import os
import sys
import json
import asyncio
import datetime
import zoneinfo
import urllib.request
import urllib.error

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(PROJECT_DIR, "web")
MP3_PATH = os.path.join(WEB_DIR, "broadcast.mp3")
DATA_PATH = os.path.join(WEB_DIR, "data.json")

TZ_CHINA = zoneinfo.ZoneInfo("Asia/Shanghai")
HOUR_START = 0
HOUR_END = 7
TTS_VOICE = "zh-CN-XiaoxiaoNeural"

# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------

def fetch_matches_espn(date_str: str) -> list[dict]:
    url = (
        "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard"
        f"?dates={date_str}"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
    except Exception:
        return []

    matches = []
    for evt in data.get("events", []):
        competitions = evt.get("competitions", [])
        if not competitions:
            continue
        comp = competitions[0]
        competitors = comp.get("competitors", [])
        home = competitors[0] if len(competitors) > 0 else {}
        away = competitors[1] if len(competitors) > 1 else {}
        status = evt.get("status", {}).get("type", {}).get("name", "")
        matches.append({
            "home_team": home.get("team", {}).get("displayName", "Unknown"),
            "away_team": away.get("team", {}).get("displayName", "Unknown"),
            "home_score": int(home.get("score", 0) or 0),
            "away_score": int(away.get("score", 0) or 0),
            "status": status,
            "utc_time": evt.get("date", ""),
        })
    return matches


def fetch_matches_for_window(now: datetime.datetime | None = None) -> list[dict]:
    if now is None:
        now = datetime.datetime.now(TZ_CHINA)

    window_start = now.replace(hour=HOUR_START, minute=0, second=0, microsecond=0)
    window_end = now.replace(hour=HOUR_END, minute=0, second=0, microsecond=0)

    date_param = now.strftime("%Y-%m-%d")
    all_matches = fetch_matches_espn(date_param)

    yesterday = (now - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    all_matches += fetch_matches_espn(yesterday)

    seen = set()
    filtered = []
    for m in all_matches:
        key = f"{m['home_team']}|{m['away_team']}|{m.get('utc_time', '')}"
        if key in seen:
            continue
        seen.add(key)

        if m["status"] != "STATUS_FINAL":
            continue

        if m.get("utc_time"):
            try:
                match_time = datetime.datetime.fromisoformat(
                    m["utc_time"].replace("Z", "+00:00")
                )
                match_time_cn = match_time.astimezone(TZ_CHINA)
                if not (window_start <= match_time_cn <= window_end):
                    continue
            except (ValueError, TypeError):
                pass

        filtered.append(m)

    return filtered


# ---------------------------------------------------------------------------
# Announcement text
# ---------------------------------------------------------------------------

def build_announcement_text(matches: list[dict], now: datetime.datetime) -> str:
    weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    weekday = weekday_names[now.weekday()]
    date_str = now.strftime("%m月%d日")

    if not matches:
        return (
            f"早上好！今天是{date_str}，{weekday}。"
            "今天凌晨零点到早上7点之间没有世界杯比赛，祝您有美好的一天！"
        )

    lines = [f"早上好！今天是{date_str}，{weekday}。世界杯比分播报。"]
    lines.append(f"今天凌晨共有{len(matches)}场比赛结果：")

    for i, m in enumerate(matches, 1):
        home = m.get("home_team", "未知")
        away = m.get("away_team", "未知")
        hs = m.get("home_score", 0)
        aws = m.get("away_score", 0)
        lines.append(f"第{i}场，{home}对阵{away}，比分{hs}比{aws}。")

    lines.append("以上就是今天凌晨的世界杯比分播报，祝您有美好的一天！")
    return "\n".join(lines)


def build_push_text(matches: list[dict], now: datetime.datetime, audio_url: str) -> str:
    """Build shorter push notification text with clickable audio link."""
    weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    weekday = weekday_names[now.weekday()]
    date_str = now.strftime("%m月%d日")

    if not matches:
        return (
            f"⚽ 世界杯比分播报 | {date_str} {weekday}\n\n"
            "今天凌晨没有比赛。\n\n"
            f"👉 点击收听语音播报\n{audio_url}"
        )

    lines = [f"⚽ 世界杯比分播报 | {date_str} {weekday}\n"]
    for m in matches:
        home = m.get("home_team", "?")
        away = m.get("away_team", "?")
        hs = m.get("home_score", 0)
        aws = m.get("away_score", 0)
        lines.append(f"  {home} {hs} - {aws} {away}")
    lines.append(f"\n👉 点击收听完整语音播报\n{audio_url}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Voice generation
# ---------------------------------------------------------------------------

async def generate_mp3(text: str, output_path: str):
    import edge_tts
    communicate = edge_tts.Communicate(text, TTS_VOICE)
    await communicate.save(output_path)


# ---------------------------------------------------------------------------
# Push notification
# ---------------------------------------------------------------------------

def send_pushplus(token: str, title: str, content: str) -> bool:
    """Send push notification via PushPlus (pushplus.plus)."""
    url = "http://www.pushplus.plus/send"
    data = json.dumps({
        "token": token,
        "title": title,
        "content": content,
        "template": "txt",
    }).encode("utf-8")
    try:
        req = urllib.request.Request(url, data=data, headers={
            "Content-Type": "application/json"
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode())
            return result.get("code") == 200
    except Exception as e:
        print(f"  PushPlus 推送失败: {e}")
        return False


def send_serverchan(sendkey: str, title: str, content: str) -> bool:
    """Send push notification via Server酱 (sct.ftqq.com)."""
    url = f"https://sctapi.ftqq.com/{sendkey}.send"
    form_data = f"title={urllib.parse.quote(title)}&desp={urllib.parse.quote(content)}"
    try:
        req = urllib.request.Request(url, data=form_data.encode("ascii"), headers={
            "Content-Type": "application/x-www-form-urlencoded"
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode())
            return result.get("code") == 0
    except Exception as e:
        print(f"  Server酱推送失败: {e}")
        return False


def send_push(title: str, content: str) -> bool:
    """Send push notification. Reads config from environment variables."""
    token = os.environ.get("PUSH_TOKEN", "")
    service = os.environ.get("PUSH_SERVICE", "pushplus").lower()

    if not token:
        print("  未配置 PUSH_TOKEN，跳过推送")
        return False

    print(f"  正在推送通知 ({service})...")
    if service == "serverchan":
        return send_serverchan(token, title, content)
    else:
        return send_pushplus(token, title, content)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    os.makedirs(WEB_DIR, exist_ok=True)
    now = datetime.datetime.now(TZ_CHINA)
    do_push = "--push" in sys.argv or os.environ.get("PUSH_TOKEN")

    print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] 正在获取比赛数据...")
    matches = fetch_matches_for_window(now)

    print(f"  找到 {len(matches)} 场比赛")

    text = build_announcement_text(matches, now)
    print("  播音文本：")
    print(f"  {text[:120]}..." if len(text) > 120 else f"  {text}")

    print("  正在生成语音...")
    asyncio.run(generate_mp3(text, MP3_PATH))
    print(f"  语音已保存: {MP3_PATH}")

    # Write data.json for web page
    data = {
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M"),
        "match_count": len(matches),
        "text": text,
        "matches": [{
            "home_team": m.get("home_team", ""),
            "away_team": m.get("away_team", ""),
            "home_score": m.get("home_score", 0),
            "away_score": m.get("away_score", 0),
        } for m in matches],
    }
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  数据已保存: {DATA_PATH}")

    # Push notification
    if do_push:
        audio_base = os.environ.get("AUDIO_BASE_URL", "")
        audio_url = f"{audio_base.rstrip('/')}/" if audio_base else ""
        push_title = f"⚽ 世界杯比分 {now.strftime('%m月%d日')}"
        push_content = build_push_text(matches, now, audio_url)
        send_push(push_title, push_content)


def generate_sample():
    """Generate a sample broadcast for testing without API access."""
    os.makedirs(WEB_DIR, exist_ok=True)
    now = datetime.datetime.now(TZ_CHINA)

    sample_matches = [
        {"home_team": "巴西", "away_team": "德国", "home_score": 2, "away_score": 1},
        {"home_team": "阿根廷", "away_team": "法国", "home_score": 1, "away_score": 1},
    ]
    text = build_announcement_text(sample_matches, now)
    print(f"  播音文本：\n  {text}")
    asyncio.run(generate_mp3(text, MP3_PATH))

    data = {
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M"),
        "match_count": len(sample_matches),
        "text": text,
        "matches": sample_matches,
    }
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  示例语音已生成: {MP3_PATH}")


if __name__ == "__main__":
    if "--sample" in sys.argv:
        generate_sample()
    else:
        main()
