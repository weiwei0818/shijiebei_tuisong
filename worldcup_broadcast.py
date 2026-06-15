"""
World Cup morning voice broadcast.
Every 7:00 AM BJT: fetch match scores (0:00-7:00 window), generate Chinese
voice MP3 via edge-tts, push text notification to WeChat via PushPlus.
"""
import os
import sys
import json
import asyncio
import datetime
import zoneinfo
import urllib.request
import urllib.parse
import urllib.error

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(PROJECT_DIR, "web")
MP3_PATH = os.path.join(WEB_DIR, "broadcast.mp3")
DATA_PATH = os.path.join(WEB_DIR, "data.json")

TZ_CHINA = zoneinfo.ZoneInfo("Asia/Shanghai")
TTS_VOICE = "zh-CN-XiaoxiaoNeural"

# ---------------------------------------------------------------------------
# Chinese team name mapping
# ---------------------------------------------------------------------------

TEAM_CN: dict[str, str] = {
    # UEFA
    "Germany": "德国", "France": "法国", "Spain": "西班牙", "England": "英格兰",
    "Portugal": "葡萄牙", "Italy": "意大利", "Netherlands": "荷兰", "Belgium": "比利时",
    "Croatia": "克罗地亚", "Denmark": "丹麦", "Switzerland": "瑞士", "Austria": "奥地利",
    "Ukraine": "乌克兰", "Turkey": "土耳其", "Sweden": "瑞典", "Poland": "波兰",
    "Serbia": "塞尔维亚", "Scotland": "苏格兰", "Czechia": "捷克", "Norway": "挪威",
    "Hungary": "匈牙利", "Romania": "罗马尼亚", "Greece": "希腊", "Slovakia": "斯洛伐克",
    "Wales": "威尔士", "Russia": "俄罗斯", "Finland": "芬兰", "Iceland": "冰岛",
    "Ireland": "爱尔兰", "Slovenia": "斯洛文尼亚", "Albania": "阿尔巴尼亚",
    "Bosnia-Herzegovina": "波黑", "Bosnia and Herzegovina": "波黑",
    "Türkiye": "土耳其",
    # CONMEBOL
    "Argentina": "阿根廷", "Brazil": "巴西", "Uruguay": "乌拉圭", "Colombia": "哥伦比亚",
    "Ecuador": "厄瓜多尔", "Peru": "秘鲁", "Chile": "智利", "Paraguay": "巴拉圭",
    "Bolivia": "玻利维亚", "Venezuela": "委内瑞拉",
    # CONCACAF
    "United States": "美国", "Mexico": "墨西哥", "Canada": "加拿大",
    "Costa Rica": "哥斯达黎加", "Panama": "巴拿马", "Jamaica": "牙买加",
    "Honduras": "洪都拉斯", "El Salvador": "萨尔瓦多", "Haiti": "海地",
    "Curaçao": "库拉索", "Curacao": "库拉索",
    # CAF
    "Morocco": "摩洛哥", "Senegal": "塞内加尔", "Egypt": "埃及", "Nigeria": "尼日利亚",
    "Cameroon": "喀麦隆", "Ivory Coast": "科特迪瓦", "Ghana": "加纳",
    "Algeria": "阿尔及利亚", "South Africa": "南非", "Tunisia": "突尼斯",
    "Mali": "马里", "Burkina Faso": "布基纳法索",
    "Côte d'Ivoire": "科特迪瓦",
    # AFC
    "Japan": "日本", "South Korea": "韩国", "Australia": "澳大利亚",
    "Saudi Arabia": "沙特阿拉伯", "Iran": "伊朗", "United Arab Emirates": "阿联酋",
    "Qatar": "卡塔尔", "China": "中国",
    # OFC
    "New Zealand": "新西兰",
    # Additional
    "Cape Verde": "佛得角",
}

# Team strength tiers for score prediction (lower = stronger)
TEAM_STRENGTH: dict[str, int] = {
    "阿根廷": 1, "巴西": 1, "法国": 1, "英格兰": 1, "西班牙": 1, "德国": 1,
    "葡萄牙": 2, "荷兰": 2, "意大利": 2, "比利时": 2, "克罗地亚": 2, "乌拉圭": 2,
    "丹麦": 3, "瑞士": 3, "哥伦比亚": 3, "墨西哥": 3, "美国": 3, "日本": 3,
    "摩洛哥": 3, "塞内加尔": 3, "韩国": 3, "奥地利": 3,
    "瑞典": 4, "波兰": 4, "乌克兰": 4, "土耳其": 4, "塞尔维亚": 4, "埃及": 4,
    "尼日利亚": 4, "澳大利亚": 4, "伊朗": 4, "沙特阿拉伯": 4, "加拿大": 4,
    "厄瓜多尔": 5, "巴拉圭": 5, "智利": 5, "秘鲁": 5, "喀麦隆": 5,
    "加纳": 5, "科特迪瓦": 5, "阿尔及利亚": 5, "突尼斯": 5, "南非": 5,
    "卡塔尔": 5, "阿联酋": 5, "哥斯达黎加": 5, "巴拿马": 5, "牙买加": 5,
    "捷克": 5, "苏格兰": 5, "挪威": 5, "匈牙利": 5,
    "新西兰": 6, "佛得角": 6, "库拉索": 6, "海地": 6, "波黑": 5,
}


def cn(name: str) -> str:
    """Get Chinese team name. Falls back to original if no mapping."""
    return TEAM_CN.get(name, name)


# ---------------------------------------------------------------------------
# Score prediction
# ---------------------------------------------------------------------------

def predict_score(home_cn: str, away_cn: str) -> str:
    """Predict score for an upcoming match based on team strength tiers."""
    home_s = TEAM_STRENGTH.get(home_cn, 5)
    away_s = TEAM_STRENGTH.get(away_cn, 5)
    diff = away_s - home_s  # positive = home stronger

    if diff >= 3:
        return "3-0"
    elif diff >= 2:
        return "2-0"
    elif diff >= 1:
        return "2-1"
    elif diff >= -1:
        return "1-1"
    elif diff >= -2:
        return "1-2"
    else:
        return "0-2"


# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------

def fetch_date(date_str: str) -> list[dict]:
    """Fetch matches for a UTC date in YYYYMMDD format from ESPN."""
    url = (
        f"https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard"
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

        home_en = home.get("team", {}).get("displayName", "Unknown")
        away_en = away.get("team", {}).get("displayName", "Unknown")

        matches.append({
            "home_team": cn(home_en),
            "away_team": cn(away_en),
            "home_team_en": home_en,
            "away_team_en": away_en,
            "home_score": int(home.get("score", 0) or 0),
            "away_score": int(away.get("score", 0) or 0),
            "status": status,
            "utc_time": evt.get("date", ""),
            "venue": comp.get("venue", {}).get("fullName", ""),
        })
    return matches


def fetch_matches_for_window(now: datetime.datetime | None = None) -> tuple[list[dict], list[dict], list[dict]]:
    """Return (finished_early, finished_other, upcoming) for morning broadcast.

    finished_early: matches that ended in 0:00-7:00 BJT window today
    finished_other: other recently finished matches
    upcoming: scheduled matches for today/tomorrow
    """
    if now is None:
        now = datetime.datetime.now(TZ_CHINA)

    window_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    window_end = now.replace(hour=7, minute=0, second=0, microsecond=0)

    # Query multiple UTC dates to cover the BJT early-morning window:
    # BJT 0:00-7:00 on day D = UTC 16:00-(D-1) to UTC 23:00-(D-1), plus
    # possibly UTC 00:00 of day D for matches that start very late
    today_bj = now
    yesterday_utc = (today_bj - datetime.timedelta(days=1)).strftime("%Y%m%d")
    today_utc = today_bj.strftime("%Y%m%d")
    tomorrow_utc = (today_bj + datetime.timedelta(days=1)).strftime("%Y%m%d")

    all_matches: list[dict] = []
    for d in [yesterday_utc, today_utc, tomorrow_utc]:
        all_matches.extend(fetch_date(d))

    # Deduplicate
    seen = set()
    unique: list[dict] = []
    for m in all_matches:
        key = f"{m['home_team_en']}|{m['away_team_en']}|{m.get('utc_time','')}"
        if key not in seen:
            seen.add(key)
            unique.append(m)
    all_matches = unique

    finished_early: list[dict] = []
    finished_other: list[dict] = []
    upcoming: list[dict] = []

    for m in all_matches:
        if m["status"] in ("STATUS_FINAL", "STATUS_FULL_TIME"):
            # Check if match time falls in the 0:00-7:00 BJT window
            if m.get("utc_time"):
                try:
                    mt = datetime.datetime.fromisoformat(
                        m["utc_time"].replace("Z", "+00:00")
                    )
                    mt_bj = mt.astimezone(TZ_CHINA)
                    if window_start <= mt_bj <= window_end:
                        finished_early.append(m)
                    else:
                        finished_other.append(m)
                except (ValueError, TypeError):
                    finished_other.append(m)
            else:
                finished_other.append(m)
        elif m["status"] in ("STATUS_SCHEDULED", "STATUS_IN_PROGRESS", "STATUS_HALFTIME"):
            upcoming.append(m)

    finished_early.sort(key=lambda m: m.get("utc_time", ""))
    finished_other.sort(key=lambda m: m.get("utc_time", ""), reverse=True)
    upcoming.sort(key=lambda m: m.get("utc_time", ""))

    return finished_early, finished_other, upcoming


# ---------------------------------------------------------------------------
# Time helpers
# ---------------------------------------------------------------------------

def to_beijing_time(utc_str: str) -> str:
    if not utc_str:
        return ""
    try:
        mt = datetime.datetime.fromisoformat(utc_str.replace("Z", "+00:00"))
        return mt.astimezone(TZ_CHINA).strftime("%H:%M")
    except (ValueError, TypeError):
        return ""


def to_beijing_date(utc_str: str) -> str:
    if not utc_str:
        return ""
    try:
        mt = datetime.datetime.fromisoformat(utc_str.replace("Z", "+00:00"))
        return mt.astimezone(TZ_CHINA).strftime("%m月%d日")
    except (ValueError, TypeError):
        return ""


# ---------------------------------------------------------------------------
# Text builders
# ---------------------------------------------------------------------------

def build_announcement_text(
    finished_early: list[dict],
    finished_other: list[dict],
    upcoming: list[dict],
    now: datetime.datetime,
) -> str:
    weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    weekday = weekday_names[now.weekday()]
    date_str = now.strftime("%m月%d日")
    parts = [f"早上好！今天是{date_str}，{weekday}。世界杯比分播报。"]

    if finished_early:
        parts.append("今天凌晨比赛结果：")
        for m in finished_early:
            parts.append(
                f"{m['home_team']}对阵{m['away_team']}，比分"
                f"{m['home_score']}比{m['away_score']}。"
            )
    elif finished_other:
        parts.append("最近比赛结果：")
        for m in finished_other[:6]:
            parts.append(
                f"{m['home_team']}对阵{m['away_team']}，比分"
                f"{m['home_score']}比{m['away_score']}。"
            )
    else:
        parts.append("目前还没有已结束的比赛。")

    if upcoming:
        parts.append("即将进行的比赛（北京时间）：")
        for m in upcoming[:8]:
            bj_time = to_beijing_time(m.get("utc_time", ""))
            time_str = f"，{bj_time}开赛" if bj_time else ""
            pred = predict_score(m["home_team"], m["away_team"])
            parts.append(f"{m['home_team']}对阵{m['away_team']}（预测{pred}）{time_str}。")

    parts.append("祝您有美好的一天！")
    return "\n".join(parts)


def build_push_text(
    finished_early: list[dict],
    finished_other: list[dict],
    upcoming: list[dict],
    now: datetime.datetime,
    audio_url: str,
) -> str:
    weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    weekday = weekday_names[now.weekday()]
    date_str = now.strftime("%m月%d日")
    lines = [f"⚽ 世界杯比分播报 | {date_str} {weekday}"]

    # Show early-morning finished matches first
    if finished_early:
        lines.append("\n【凌晨比分】")
        for m in finished_early:
            lines.append(
                f"  {m['home_team']} {m['home_score']} - {m['away_score']} {m['away_team']}"
            )
    elif finished_other:
        lines.append("\n【近期比分】")
        for m in finished_other[:6]:
            lines.append(
                f"  {m['home_team']} {m['home_score']} - {m['away_score']} {m['away_team']}"
            )

    # Group upcoming by Beijing date
    if upcoming:
        by_date: dict[str, list[dict]] = {}
        for m in upcoming[:12]:
            cn_date = to_beijing_date(m.get("utc_time", "")) or "其他"
            by_date.setdefault(cn_date, []).append(m)

        for cn_date, day_matches in by_date.items():
            lines.append(f"\n【{cn_date}赛程·预测】")
            for m in day_matches:
                bj_time = to_beijing_time(m.get("utc_time", ""))
                pred = predict_score(m["home_team"], m["away_team"])
                line = f"  {bj_time}  {m['home_team']} vs {m['away_team']}  推测{pred}" \
                    if bj_time else f"  {m['home_team']} vs {m['away_team']}  推测{pred}"
                lines.append(line)

    if not finished_early and not finished_other and not upcoming:
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
    url = "http://www.pushplus.plus/send"
    data = json.dumps({
        "token": token, "title": title, "content": content, "template": "txt",
    }).encode("utf-8")
    try:
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode())
            return result.get("code") == 200
    except Exception as e:
        print(f"  PushPlus 推送失败: {e}")
        return False


def send_push(title: str, content: str) -> bool:
    token = os.environ.get("PUSH_TOKEN", "")
    if not token:
        print("  未配置 PUSH_TOKEN，跳过推送")
        return False
    print("  正在推送通知...")
    return send_pushplus(token, title, content)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    os.makedirs(WEB_DIR, exist_ok=True)
    now = datetime.datetime.now(TZ_CHINA)
    do_push = "--push" in sys.argv or os.environ.get("PUSH_TOKEN")

    print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] 正在获取比赛数据...")
    finished_early, finished_other, upcoming = fetch_matches_for_window(now)

    print(f"  凌晨比分: {len(finished_early)} 场, 其他结束: {len(finished_other)} 场, "
          f"即将开始: {len(upcoming)} 场")

    text = build_announcement_text(finished_early, finished_other, upcoming, now)
    print("  播音文本：")
    print(f"  {text[:150]}..." if len(text) > 150 else f"  {text}")

    print("  正在生成语音...")
    asyncio.run(generate_mp3(text, MP3_PATH))
    print(f"  语音已保存: {MP3_PATH}")

    all_matches = finished_early + finished_other + upcoming
    json_matches = []
    for m in all_matches:
        json_matches.append({
            "home_team": m.get("home_team", ""),
            "away_team": m.get("away_team", ""),
            "home_score": m.get("home_score", 0),
            "away_score": m.get("away_score", 0),
        })
    data = {
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M"),
        "match_count": len(json_matches),
        "text": text,
        "matches": json_matches,
    }
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    if do_push:
        audio_base = os.environ.get("AUDIO_BASE_URL", "")
        audio_url = f"{audio_base.rstrip('/')}/" if audio_base else ""
        push_title = f"⚽ 世界杯比分 {now.strftime('%m月%d日')}"
        push_content = build_push_text(finished_early, finished_other, upcoming,
                                       now, audio_url)
        send_push(push_title, push_content)


def generate_sample():
    os.makedirs(WEB_DIR, exist_ok=True)
    now = datetime.datetime.now(TZ_CHINA)
    finished_early = [
        {"home_team": "巴西", "away_team": "德国", "home_score": 2, "away_score": 1},
        {"home_team": "阿根廷", "away_team": "法国", "home_score": 1, "away_score": 1},
    ]
    finished_other = [
        {"home_team": "英格兰", "away_team": "西班牙", "home_score": 3, "away_score": 0},
    ]
    upcoming = [
        {"home_team": "日本", "away_team": "韩国", "utc_time": "2026-06-15T19:00Z"},
    ]
    text = build_announcement_text(finished_early, finished_other, upcoming, now)
    print(f"  播音文本：\n  {text}")
    asyncio.run(generate_mp3(text, MP3_PATH))
    data = {
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M"),
        "match_count": len(finished_early) + len(finished_other) + len(upcoming),
        "text": text,
        "matches": finished_early + finished_other + upcoming,
    }
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  示例语音已生成: {MP3_PATH}")


if __name__ == "__main__":
    if "--sample" in sys.argv:
        generate_sample()
    else:
        main()
