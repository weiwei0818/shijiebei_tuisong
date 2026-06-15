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
QUOTES_FILE = os.path.join(PROJECT_DIR, "quotes_used.json")

# ---------------------------------------------------------------------------
# Daily famous quotes (80 quotes, Chinese + author)
# ---------------------------------------------------------------------------

QUOTES: list[dict[str, str]] = [
    {"text": "生活不止眼前的苟且，还有诗和远方。", "author": "高晓松"},
    {"text": "人生如逆旅，我亦是行人。", "author": "苏轼"},
    {"text": "天行健，君子以自强不息。", "author": "《周易》"},
    {"text": "世上无难事，只怕有心人。", "author": "谚语"},
    {"text": "路漫漫其修远兮，吾将上下而求索。", "author": "屈原"},
    {"text": "千里之行，始于足下。", "author": "老子"},
    {"text": "不积跬步，无以至千里；不积小流，无以成江海。", "author": "荀子"},
    {"text": "业精于勤，荒于嬉；行成于思，毁于随。", "author": "韩愈"},
    {"text": "宝剑锋从磨砺出，梅花香自苦寒来。", "author": "《警世贤文》"},
    {"text": "书山有路勤为径，学海无涯苦作舟。", "author": "韩愈"},
    {"text": "长风破浪会有时，直挂云帆济沧海。", "author": "李白"},
    {"text": "天生我材必有用，千金散尽还复来。", "author": "李白"},
    {"text": "山重水复疑无路，柳暗花明又一村。", "author": "陆游"},
    {"text": "会当凌绝顶，一览众山小。", "author": "杜甫"},
    {"text": "海内存知己，天涯若比邻。", "author": "王勃"},
    {"text": "但愿人长久，千里共婵娟。", "author": "苏轼"},
    {"text": "不以物喜，不以己悲。", "author": "范仲淹"},
    {"text": "先天下之忧而忧，后天下之乐而乐。", "author": "范仲淹"},
    {"text": "富贵不能淫，贫贱不能移，威武不能屈。", "author": "孟子"},
    {"text": "生于忧患，死于安乐。", "author": "孟子"},
    {"text": "三人行，必有我师焉。", "author": "孔子"},
    {"text": "学而不思则罔，思而不学则殆。", "author": "孔子"},
    {"text": "知之者不如好之者，好之者不如乐之者。", "author": "孔子"},
    {"text": "己所不欲，勿施于人。", "author": "孔子"},
    {"text": "知之为知之，不知为不知，是知也。", "author": "孔子"},
    {"text": "敏而好学，不耻下问。", "author": "孔子"},
    {"text": "非淡泊无以明志，非宁静无以致远。", "author": "诸葛亮"},
    {"text": "鞠躬尽瘁，死而后已。", "author": "诸葛亮"},
    {"text": "静以修身，俭以养德。", "author": "诸葛亮"},
    {"text": "天下兴亡，匹夫有责。", "author": "顾炎武"},
    {"text": "为中华之崛起而读书。", "author": "周恩来"},
    {"text": "时间就是生命，浪费时间就是浪费生命。", "author": "鲁迅"},
    {"text": "其实地上本没有路，走的人多了，也便成了路。", "author": "鲁迅"},
    {"text": "横眉冷对千夫指，俯首甘为孺子牛。", "author": "鲁迅"},
    {"text": "成功是百分之一的天赋加上百分之九十九的汗水。", "author": "爱迪生"},
    {"text": "天才是百分之一的灵感加上百分之九十九的汗水。", "author": "爱迪生"},
    {"text": "失败是成功之母。", "author": "谚语"},
    {"text": "知识就是力量。", "author": "培根"},
    {"text": "读一本好书，就是和许多高尚的人谈话。", "author": "歌德"},
    {"text": "人生就像骑自行车，要保持平衡就得不断前进。", "author": "爱因斯坦"},
    {"text": "想象力比知识更重要。", "author": "爱因斯坦"},
    {"text": "人最宝贵的是生命，生命对人来说只有一次。", "author": "奥斯特洛夫斯基"},
    {"text": "冬天来了，春天还会远吗？", "author": "雪莱"},
    {"text": "走自己的路，让别人说去吧。", "author": "但丁"},
    {"text": "我思故我在。", "author": "笛卡尔"},
    {"text": "活着就是为了改变世界。", "author": "乔布斯"},
    {"text": "保持饥饿，保持愚蠢。", "author": "乔布斯"},
    {"text": "人生最大的荣耀不在于从不跌倒，而在于每次跌倒后都能爬起来。", "author": "曼德拉"},
    {"text": "教育是最强大的武器，你可以用它来改变世界。", "author": "曼德拉"},
    {"text": "不经巨大的困难，不会有伟大的事业。", "author": "伏尔泰"},
    {"text": "胜利属于最坚忍的人。", "author": "拿破仑"},
    {"text": "不想当将军的士兵不是好士兵。", "author": "拿破仑"},
    {"text": "给我一个支点，我可以撬动整个地球。", "author": "阿基米德"},
    {"text": "有志者，事竟成。", "author": "《后汉书》"},
    {"text": "滴水穿石，非一日之功。", "author": "谚语"},
    {"text": "一分耕耘，一分收获。", "author": "谚语"},
    {"text": "塞翁失马，焉知非福。", "author": "《淮南子》"},
    {"text": "近朱者赤，近墨者黑。", "author": "谚语"},
    {"text": "青，取之于蓝而青于蓝。", "author": "荀子"},
    {"text": "锲而不舍，金石可镂。", "author": "荀子"},
    {"text": "人生自古谁无死，留取丹心照汗青。", "author": "文天祥"},
    {"text": "春蚕到死丝方尽，蜡炬成灰泪始干。", "author": "李商隐"},
    {"text": "海阔凭鱼跃，天高任鸟飞。", "author": "谚语"},
    {"text": "日省其身，有则改之，无则加勉。", "author": "朱熹"},
    {"text": "纸上得来终觉浅，绝知此事要躬行。", "author": "陆游"},
    {"text": "问渠那得清如许，为有源头活水来。", "author": "朱熹"},
    {"text": "盛年不重来，一日难再晨。及时当勉励，岁月不待人。", "author": "陶渊明"},
    {"text": "采菊东篱下，悠然见南山。", "author": "陶渊明"},
    {"text": "不以规矩，不能成方圆。", "author": "孟子"},
    {"text": "老骥伏枥，志在千里。烈士暮年，壮心不已。", "author": "曹操"},
    {"text": "博观而约取，厚积而薄发。", "author": "苏轼"},
    {"text": "大鹏一日同风起，扶摇直上九万里。", "author": "李白"},
    {"text": "沉舟侧畔千帆过，病树前头万木春。", "author": "刘禹锡"},
    {"text": "莫愁前路无知己，天下谁人不识君。", "author": "高适"},
    {"text": "落红不是无情物，化作春泥更护花。", "author": "龚自珍"},
    {"text": "吃得苦中苦，方为人上人。", "author": "谚语"},
    {"text": "只要功夫深，铁杵磨成针。", "author": "谚语"},
    {"text": "良药苦口利于病，忠言逆耳利于行。", "author": "谚语"},
    {"text": "一寸光阴一寸金，寸金难买寸光阴。", "author": "谚语"},
    {"text": "少壮不努力，老大徒伤悲。", "author": "《长歌行》"},
]


def pick_quote() -> dict[str, str]:
    """Pick a quote that hasn't been used yet. Tracks usage in a JSON file."""
    used_ids: list[int] = []
    if os.path.exists(QUOTES_FILE):
        try:
            with open(QUOTES_FILE, "r", encoding="utf-8") as f:
                used_ids = json.load(f)
        except (json.JSONDecodeError, IOError):
            used_ids = []

    available = [i for i in range(len(QUOTES)) if i not in used_ids]

    # If all quotes used, reset the cycle
    if not available:
        used_ids = []
        available = list(range(len(QUOTES)))

    import random
    idx = random.choice(available)
    used_ids.append(idx)

    # Keep only last 200 to prevent file growth
    if len(used_ids) > 200:
        used_ids = used_ids[-200:]

    with open(QUOTES_FILE, "w", encoding="utf-8") as f:
        json.dump(used_ids, f)

    return QUOTES[idx]

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


def fetch_matches_for_window(now: datetime.datetime | None = None) -> tuple[list[dict], list[dict]]:
    """Return (finished, upcoming) for morning broadcast.

    finished: all recently finished matches (multi-day query)
    upcoming: scheduled matches for today/tomorrow
    """
    if now is None:
        now = datetime.datetime.now(TZ_CHINA)

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

    finished: list[dict] = []
    upcoming: list[dict] = []

    for m in unique:
        if m["status"] in ("STATUS_FINAL", "STATUS_FULL_TIME"):
            finished.append(m)
        elif m["status"] in ("STATUS_SCHEDULED", "STATUS_IN_PROGRESS", "STATUS_HALFTIME"):
            upcoming.append(m)

    finished.sort(key=lambda m: m.get("utc_time", ""), reverse=True)
    upcoming.sort(key=lambda m: m.get("utc_time", ""))

    return finished, upcoming


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
    finished: list[dict],
    upcoming: list[dict],
    now: datetime.datetime,
    quote: dict[str, str] | None = None,
) -> str:
    weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    weekday = weekday_names[now.weekday()]
    date_str = now.strftime("%m月%d日")
    parts = [f"早上好！今天是{date_str}，{weekday}。世界杯比分播报。"]

    if finished:
        parts.append("已结束的比赛：")
        for m in finished:
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

    if quote:
        parts.append(f"今日名言：{quote['text']} ——{quote['author']}")

    parts.append("祝您有美好的一天！")
    return "\n".join(parts)


def build_push_text(
    finished: list[dict],
    upcoming: list[dict],
    now: datetime.datetime,
    audio_url: str,
    quote: dict[str, str] | None = None,
) -> str:
    weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    weekday = weekday_names[now.weekday()]
    date_str = now.strftime("%m月%d日")
    lines = [f"⚽ 世界杯比分播报 | {date_str} {weekday}"]

    if finished:
        lines.append("\n【已结束】")
        for m in finished:
            lines.append(
                f"  {m['home_team']} {m['home_score']} - {m['away_score']} {m['away_team']}"
            )

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

    if not finished and not upcoming:
        lines.append("\n暂无比赛数据。")

    if quote:
        lines.append(f"\n📖 {quote['text']}")
        lines.append(f"  —— {quote['author']}")

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
    finished, upcoming = fetch_matches_for_window(now)

    print(f"  已结束: {len(finished)} 场, 即将开始: {len(upcoming)} 场")

    quote = pick_quote()
    print(f"  今日名言: {quote['text'][:30]}... ——{quote['author']}")

    text = build_announcement_text(finished, upcoming, now, quote)
    print("  播音文本：")
    print(f"  {text[:150]}..." if len(text) > 150 else f"  {text}")

    print("  正在生成语音...")
    asyncio.run(generate_mp3(text, MP3_PATH))
    print(f"  语音已保存: {MP3_PATH}")

    all_matches = finished + upcoming
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
        push_content = build_push_text(finished, upcoming, now, audio_url, quote)
        send_push(push_title, push_content)


def generate_sample():
    os.makedirs(WEB_DIR, exist_ok=True)
    now = datetime.datetime.now(TZ_CHINA)
    finished = [
        {"home_team": "巴西", "away_team": "德国", "home_score": 2, "away_score": 1},
        {"home_team": "阿根廷", "away_team": "法国", "home_score": 1, "away_score": 1},
        {"home_team": "英格兰", "away_team": "西班牙", "home_score": 3, "away_score": 0},
    ]
    upcoming = [
        {"home_team": "日本", "away_team": "韩国", "utc_time": "2026-06-15T19:00Z"},
    ]
    quote = {"text": "生活不止眼前的苟且，还有诗和远方。", "author": "高晓松"}
    text = build_announcement_text(finished, upcoming, now, quote)
    print(f"  播音文本：\n  {text}")
    asyncio.run(generate_mp3(text, MP3_PATH))
    data = {
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M"),
        "match_count": len(finished) + len(upcoming),
        "text": text,
        "matches": finished + upcoming,
    }
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  示例语音已生成: {MP3_PATH}")


if __name__ == "__main__":
    if "--sample" in sys.argv:
        generate_sample()
    else:
        main()
