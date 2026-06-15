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

def fetch_all_matches() -> tuple[list[dict], list[dict]]:
    """Fetch all matches from ESPN API. Returns (finished, upcoming) lists.

    ESPN scoreboard endpoint without any date param returns the current
    match-day matches (both finished and upcoming).
    """
    url = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
    except Exception:
        return [], []

    finished = []
    upcoming = []

    for evt in data.get("events", []):
        competitions = evt.get("competitions", [])
        if not competitions:
            continue
        comp = competitions[0]
        competitors = comp.get("competitors", [])
        home = competitors[0] if len(competitors) > 0 else {}
        away = competitors[1] if len(competitors) > 1 else {}
        status = evt.get("status", {}).get("type", {}).get("name", "")

        match = {
            "home_team": home.get("team", {}).get("displayName", "Unknown"),
            "away_team": away.get("team", {}).get("displayName", "Unknown"),
            "home_score": int(home.get("score", 0) or 0),
            "away_score": int(away.get("score", 0) or 0),
            "status": status,
            "utc_time": evt.get("date", ""),
            "venue": comp.get("venue", {}).get("fullName", ""),
        }

        if status == "STATUS_FINAL":
            finished.append(match)
        elif status in ("STATUS_SCHEDULED", "STATUS_IN_PROGRESS", "STATUS_HALFTIME"):
            upcoming.append(match)

    # Sort finished by time descending (most recent first)
    finished.sort(key=lambda m: m.get("utc_time", ""), reverse=True)
    # Sort upcoming by time ascending (earliest first)
    upcoming.sort(key=lambda m: m.get("utc_time", ""))

    return finished, upcoming


def fetch_matches_for_window(now: datetime.datetime | None = None) -> tuple[list[dict], list[dict]]:
    """Return (finished_in_window, upcoming_today) for the morning broadcast."""
    if now is None:
        now = datetime.datetime.now(TZ_CHINA)

    window_start = now.replace(hour=HOUR_START, minute=0, second=0, microsecond=0)
    window_end = now.replace(hour=HOUR_END, minute=0, second=0, microsecond=0)

    all_finished, all_upcoming = fetch_all_matches()

    # Filter finished matches to the 0:00-7:00 AM China time window
    finished_in_window = []
    for m in all_finished:
        if m.get("utc_time"):
            try:
                match_time = datetime.datetime.fromisoformat(
                    m["utc_time"].replace("Z", "+00:00")
                )
                match_time_cn = match_time.astimezone(TZ_CHINA)
                if window_start <= match_time_cn <= window_end:
                    finished_in_window.append(m)
            except (ValueError, TypeError):
                pass

    # If no finished matches in window, include all recent finished matches
    if not finished_in_window:
        finished_in_window = all_finished[:10]

    return finished_in_window, all_upcoming[:10]


# ---------------------------------------------------------------------------
# Announcement text
# ---------------------------------------------------------------------------

def to_beijing_time(utc_str: str) -> str:
    """Convert UTC time string to Beijing time HH:MM format."""
    if not utc_str:
        return ""
    try:
        mt = datetime.datetime.fromisoformat(utc_str.replace("Z", "+00:00"))
        return mt.astimezone(TZ_CHINA).strftime("%H:%M")
    except (ValueError, TypeError):
        return ""


def to_beijing_date(utc_str: str) -> str:
    """Convert UTC time string to Beijing date MM月DD日 format."""
    if not utc_str:
        return ""
    try:
        mt = datetime.datetime.fromisoformat(utc_str.replace("Z", "+00:00"))
        return mt.astimezone(TZ_CHINA).strftime("%m月%d日")
    except (ValueError, TypeError):
        return ""


def build_announcement_text(finished: list[dict], upcoming: list[dict], now: datetime.datetime) -> str:
    weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    weekday = weekday_names[now.weekday()]
    date_str = now.strftime("%m月%d日")

    parts = [f"早上好！今天是{date_str}，{weekday}。世界杯比分播报。"]

    if finished:
        parts.append("已结束的比赛：")
        for m in finished:
            home = m.get("home_team", "未知")
            away = m.get("away_team", "未知")
            hs = m.get("home_score", 0)
            aws = m.get("away_score", 0)
            parts.append(f"{home}对阵{away}，比分{hs}比{aws}。")
    else:
        parts.append("目前还没有已结束的比赛。")

    if upcoming:
        parts.append("即将进行的比赛（北京时间）：")
        for m in upcoming[:8]:
            home = m.get("home_team", "未知")
            away = m.get("away_team", "未知")
            bj_time = to_beijing_time(m.get("utc_time", ""))
            time_str = f"，{bj_time}开赛" if bj_time else ""
            parts.append(f"{home}对阵{away}{time_str}。")

    parts.append("祝您有美好的一天！")
    return "\n".join(parts)


def build_push_text(finished: list[dict], upcoming: list[dict], now: datetime.datetime, audio_url: str) -> str:
    """Build text-only push notification. All times in Beijing time."""
    weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    weekday = weekday_names[now.weekday()]
    date_str = now.strftime("%m月%d日")

    lines = [f"⚽ 世界杯比分播报 | {date_str} {weekday}"]

    if finished:
        lines.append("\n【已结束】")
        for m in finished:
            home = m.get("home_team", "?")
            away = m.get("away_team", "?")
            hs = m.get("home_score", 0)
            aws = m.get("away_score", 0)
            lines.append(f"  {home} {hs} - {aws} {away}")

    if upcoming:
        by_date: dict[str, list[dict]] = {}
        for m in upcoming[:12]:
            cn_date = to_beijing_date(m.get("utc_time", "")) or "其他"
            by_date.setdefault(cn_date, []).append(m)

        for cn_date, day_matches in by_date.items():
            lines.append(f"\n【{cn_date}赛程】")
            for m in day_matches:
                home = m.get("home_team", "?")
                away = m.get("away_team", "?")
                bj_time = to_beijing_time(m.get("utc_time", ""))
                lines.append(f"  {bj_time}  {home} vs {away}" if bj_time else f"  {home} vs {away}")
    elif not finished:
        lines.append("\n暂无比赛数据。")

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
    finished, upcoming = fetch_matches_for_window(now)

    print(f"  已结束: {len(finished)} 场, 即将开始: {len(upcoming)} 场")

    text = build_announcement_text(finished, upcoming, now)
    print("  播音文本：")
    print(f"  {text[:120]}..." if len(text) > 120 else f"  {text}")

    print("  正在生成语音...")
    asyncio.run(generate_mp3(text, MP3_PATH))
    print(f"  语音已保存: {MP3_PATH}")

    # Write data.json for web page
    all_matches = finished + upcoming
    data = {
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M"),
        "match_count": len(all_matches),
        "text": text,
        "matches": [{
            "home_team": m.get("home_team", ""),
            "away_team": m.get("away_team", ""),
            "home_score": m.get("home_score", 0),
            "away_score": m.get("away_score", 0),
        } for m in all_matches],
    }
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  数据已保存: {DATA_PATH}")

    # Push notification
    if do_push:
        audio_base = os.environ.get("AUDIO_BASE_URL", "")
        audio_url = f"{audio_base.rstrip('/')}/" if audio_base else ""
        push_title = f"⚽ 世界杯比分 {now.strftime('%m月%d日')}"
        push_content = build_push_text(finished, upcoming, now, audio_url)
        send_push(push_title, push_content)


def generate_sample():
    """Generate a sample broadcast for testing without API access."""
    os.makedirs(WEB_DIR, exist_ok=True)
    now = datetime.datetime.now(TZ_CHINA)

    sample_finished = [
        {"home_team": "巴西", "away_team": "德国", "home_score": 2, "away_score": 1},
        {"home_team": "阿根廷", "away_team": "法国", "home_score": 1, "away_score": 1},
    ]
    sample_upcoming = [
        {"home_team": "西班牙", "away_team": "葡萄牙", "utc_time": "2026-06-15T19:00Z"},
    ]
    text = build_announcement_text(sample_finished, sample_upcoming, now)
    print(f"  播音文本：\n  {text}")
    asyncio.run(generate_mp3(text, MP3_PATH))

    data = {
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M"),
        "match_count": len(sample_finished) + len(sample_upcoming),
        "text": text,
        "matches": sample_finished + sample_upcoming,
    }
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  示例语音已生成: {MP3_PATH}")


if __name__ == "__main__":
    if "--sample" in sys.argv:
        generate_sample()
    else:
        main()
