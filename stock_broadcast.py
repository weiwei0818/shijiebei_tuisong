"""
Stock market daily broadcast.
Pushes US stock top gainers, hot themes, and A-share momentum screening to WeChat.
Runs at 6:00 AM Beijing time via GitHub Actions.
"""
import os
import sys
import json
import time
import random
import datetime
import zoneinfo
import urllib.request
import urllib.error
import warnings

warnings.filterwarnings("ignore")

# Fix Unicode output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
TZ_CHINA = zoneinfo.ZoneInfo("Asia/Shanghai")
QUOTES_FILE = os.path.join(PROJECT_DIR, "quotes_used.json")

# ============================================================================
# Daily quotes (80 quotes kept from original)
# ============================================================================

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
    used_ids: list[int] = []
    if os.path.exists(QUOTES_FILE):
        try:
            with open(QUOTES_FILE, "r", encoding="utf-8") as f:
                used_ids = json.load(f)
        except (json.JSONDecodeError, IOError):
            used_ids = []

    available = [i for i in range(len(QUOTES)) if i not in used_ids]
    if not available:
        used_ids = []
        available = list(range(len(QUOTES)))

    idx = random.choice(available)
    used_ids.append(idx)
    if len(used_ids) > 200:
        used_ids = used_ids[-200:]

    with open(QUOTES_FILE, "w", encoding="utf-8") as f:
        json.dump(used_ids, f)

    return QUOTES[idx]


# ============================================================================
# US stock data
# ============================================================================

# Watchlist: ~130 major US stocks with sector classification
US_WATCHLIST: dict[str, str] = {
    # Mega-cap Tech
    "AAPL": "消费电子", "MSFT": "软件云服务", "GOOGL": "互联网广告",
    "AMZN": "电商云服务", "META": "社交元宇宙", "NVDA": "AI芯片",
    "TSLA": "电动车", "NFLX": "流媒体",
    # Semiconductors
    "AMD": "半导体", "INTC": "半导体", "QCOM": "通信芯片",
    "AVGO": "半导体", "TXN": "模拟芯片", "MU": "存储芯片",
    "AMAT": "半导体设备", "LRCX": "半导体设备", "ADI": "模拟芯片",
    "MRVL": "数据中心芯片", "ARM": "芯片IP", "MPWR": "电源芯片",
    "ON": "功率半导体", "NXPI": "汽车芯片",
    # Software / Cloud
    "ADBE": "软件", "CRM": "企业软件", "ORCL": "数据库",
    "NOW": "SaaS", "SNOW": "数据平台", "PLTR": "大数据AI",
    "CRWD": "网络安全", "ZS": "网络安全", "NET": "CDN边缘计算",
    "DDOG": "云监控", "MDB": "数据库", "HUBS": "营销SaaS",
    "TEAM": "协作软件", "INTU": "财税软件",
    # Internet / E-commerce
    "UBER": "出行平台", "ABNB": "共享住宿", "SHOP": "电商SaaS",
    "SNAP": "社交媒体", "PINS": "图片社交", "RBLX": "元宇宙游戏",
    "DASH": "外卖平台", "DKNG": "在线博彩",
    # Hardware / IT
    "DELL": "PC服务器", "SMCI": "AI服务器", "ANET": "网络设备",
    "HPQ": "PC打印", "NTAP": "存储", "STX": "硬盘",
    "WDC": "硬盘", "LOGI": "外设",
    # Finance
    "JPM": "银行", "BAC": "银行", "GS": "投行", "MS": "投行",
    "C": "银行", "WFC": "银行", "BLK": "资管", "SCHW": "券商",
    "BX": "私募", "KKR": "私募", "V": "支付", "MA": "支付",
    "PYPL": "支付", "SQ": "支付", "COIN": "加密货币",
    # Healthcare
    "JNJ": "医药", "PFE": "医药", "MRK": "医药", "ABBV": "医药",
    "LLY": "医药", "BMY": "医药", "GILD": "生物科技",
    "AMGN": "生物科技", "REGN": "生物科技", "VRTX": "生物科技",
    "UNH": "医疗保险", "ISRG": "手术机器人", "DXCM": "医疗设备",
    "TMO": "生命科学", "DHR": "医疗诊断",
    # Consumer
    "WMT": "零售", "COST": "会员零售", "HD": "家装零售",
    "MCD": "餐饮", "SBUX": "咖啡连锁", "NKE": "运动服饰",
    "LULU": "瑜伽服饰", "CMG": "快餐", "YUM": "餐饮连锁",
    "DIS": "娱乐媒体", "RCL": "邮轮", "BKNG": "在线旅游",
    "DHI": "房屋建筑", "LEN": "房屋建筑",
    # Energy
    "XOM": "石油", "CVX": "石油", "COP": "油气", "EOG": "油气",
    "SLB": "油服", "HAL": "油服", "OXY": "油气",
    "ENPH": "太阳能", "FSLR": "太阳能", "NEE": "清洁能源",
    # Industrial
    "CAT": "工程机械", "BA": "航空航天", "GE": "工业制造",
    "RTX": "国防", "LMT": "国防", "DE": "农机",
    "HON": "工业自动化", "ETN": "电力管理", "MMM": "多元化工业",
    "UNP": "铁路", "UPS": "物流快递", "FDX": "物流快递",
    # Materials / Others
    "LIN": "工业气体", "FCX": "铜矿", "NEM": "金矿",
    "SHW": "涂料", "APD": "工业气体",
    # Chinese ADRs
    "BABA": "中概电商", "JD": "中概电商", "PDD": "中概电商",
    "BIDU": "中概AI", "BILI": "中概视频", "NIO": "中概电动车",
    "XPEV": "中概电动车", "LI": "中概电动车", "TAL": "中概教育",
    "TME": "中概音乐", "BEKE": "中概房产",
}

# Sector ETF mapping
SECTOR_ETFS: dict[str, str] = {
    "科技": "XLK", "金融": "XLF", "能源": "XLE",
    "医疗": "XLV", "消费": "XLY", "工业": "XLI",
    "材料": "XLB", "公用事业": "XLU", "房地产": "XLRE",
    "通信": "XLC", "必选消费": "XLP",
}

# Ticker -> Chinese name for common stocks
CN_NAME: dict[str, str] = {
    "AAPL": "苹果", "MSFT": "微软", "GOOGL": "谷歌", "AMZN": "亚马逊",
    "META": "Meta", "NVDA": "英伟达", "TSLA": "特斯拉", "NFLX": "奈飞",
    "AMD": "AMD", "INTC": "英特尔", "QCOM": "高通", "AVGO": "博通",
    "TXN": "德州仪器", "MU": "美光", "AMAT": "应用材料", "LRCX": "拉姆研究",
    "ADI": "亚德诺", "MRVL": "迈威尔", "ARM": "Arm", "ON": "安森美",
    "ADBE": "Adobe", "CRM": "赛富时", "ORCL": "甲骨文", "NOW": "ServiceNow",
    "SNOW": "Snowflake", "PLTR": "Palantir", "CRWD": "CrowdStrike",
    "ZS": "Zscaler", "NET": "Cloudflare", "DDOG": "Datadog",
    "UBER": "优步", "ABNB": "爱彼迎", "SHOP": "Shopify",
    "SNAP": "Snap", "PINS": "Pinterest", "DASH": "DoorDash",
    "SMCI": "超微电脑", "DELL": "戴尔", "ANET": "Arista",
    "JPM": "摩根大通", "BAC": "美国银行", "GS": "高盛", "MS": "摩根士丹利",
    "C": "花旗", "WFC": "富国", "BLK": "贝莱德", "BX": "黑石",
    "V": "Visa", "MA": "万事达", "PYPL": "PayPal", "COIN": "Coinbase",
    "JNJ": "强生", "PFE": "辉瑞", "MRK": "默克", "ABBV": "艾伯维",
    "LLY": "礼来", "UNH": "联合健康", "ISRG": "直觉外科",
    "WMT": "沃尔玛", "COST": "好市多", "HD": "家得宝",
    "MCD": "麦当劳", "SBUX": "星巴克", "NKE": "耐克", "DIS": "迪士尼",
    "XOM": "埃克森美孚", "CVX": "雪佛龙", "COP": "康菲", "OXY": "西方石油",
    "ENPH": "Enphase", "FSLR": "First Solar", "NEE": "新纪元能源",
    "CAT": "卡特彼勒", "BA": "波音", "GE": "通用电气",
    "RTX": "雷神", "LMT": "洛克希德", "LIN": "林德",
    "BABA": "阿里巴巴", "JD": "京东", "PDD": "拼多多",
    "BIDU": "百度", "BILI": "哔哩哔哩", "NIO": "蔚来",
    "XPEV": "小鹏", "LI": "理想", "BEKE": "贝壳",
}


def get_us_top_gainers(top_n: int = 20) -> tuple[list[dict], str] | None:
    """Fetch yesterday's top gaining US stocks. Returns (gainers_list, data_date_str)."""
    try:
        import yfinance as yf
    except ImportError:
        print("  yfinance not installed, skipping US stocks")
        return None

    tickers = list(US_WATCHLIST.keys())
    batch_size = 40

    all_close_data = {}
    all_last_date = None
    all_prev_date = None

    for batch_start in range(0, len(tickers), batch_size):
        batch = tickers[batch_start:batch_start + batch_size]
        if batch_start > 0:
            time.sleep(0.5)

        try:
            data = yf.download(" ".join(batch), period="5d", progress=False,
                               auto_adjust=True, threads=False)
        except Exception as e:
            print(f"  yfinance batch {batch_start // batch_size} failed: {e}")
            continue

        if data.empty:
            continue

        close = data.get("Close")
        if close is None or close.empty or len(close) < 2:
            continue

        dates = close.index
        if len(dates) < 2:
            continue

        all_last_date = dates[-1]
        all_prev_date = dates[-2]

        for ticker in close.columns:
            try:
                val_last = float(close[ticker].iloc[-1])
                val_prev = float(close[ticker].iloc[-2])
                if val_prev > 0:
                    all_close_data[ticker] = (val_last, val_prev)
            except (IndexError, KeyError, TypeError):
                continue

    if not all_close_data:
        print("  No US stock close data after batch fetch")
        return None

    # Calculate changes
    changes = {}
    for ticker, (last, prev) in all_close_data.items():
        if ticker in US_WATCHLIST and prev > 0:
            changes[ticker] = (last - prev) / prev * 100

    sorted_changes = sorted(changes.items(), key=lambda x: x[1], reverse=True)

    gainers: list[dict] = []
    for ticker, pct in sorted_changes[:top_n]:
        last_price = all_close_data[ticker][0]
        gainers.append({
            "ticker": ticker,
            "name_cn": CN_NAME.get(ticker, ticker),
            "change_pct": round(float(pct), 2),
            "sector": US_WATCHLIST[ticker],
            "close": round(float(last_price), 2),
        })

    if all_last_date:
        data_date = all_last_date.strftime("%m月%d日") if hasattr(all_last_date, 'strftime') else str(all_last_date)[:10]
    else:
        data_date = "—"
    return gainers, data_date


def get_us_sector_heat(gainers: list[dict]) -> dict[str, int]:
    """Count sectors among top gainers."""
    sector_count: dict[str, int] = {}
    for g in gainers:
        s = g["sector"]
        sector_count[s] = sector_count.get(s, 0) + 1
    return dict(sorted(sector_count.items(), key=lambda x: x[1], reverse=True))


def get_us_sector_etf_performance() -> list[dict]:
    """Get sector ETF daily performance."""
    try:
        import yfinance as yf
    except ImportError:
        return []

    etf_tickers = list(SECTOR_ETFS.values())
    try:
        data = yf.download(" ".join(etf_tickers), period="5d", progress=False,
                           auto_adjust=True, threads=False)
    except Exception:
        return []

    if data.empty:
        return []

    close = data.get("Close")
    if close is None or close.empty or len(close) < 2:
        return []

    results = []
    for etf_ticker, sector_name in {v: k for k, v in SECTOR_ETFS.items()}.items():
        if etf_ticker in close.columns:
            try:
                chg = (close[etf_ticker].iloc[-1] - close[etf_ticker].iloc[-2]) / close[etf_ticker].iloc[-2] * 100
                results.append({"sector": sector_name, "etf": etf_ticker, "change_pct": round(float(chg), 2)})
            except (IndexError, KeyError):
                pass

    results.sort(key=lambda x: x["change_pct"], reverse=True)
    return results


# ============================================================================
# A-share stock screening
# ============================================================================

def _get_a_trading_days(n: int = 8) -> list[str]:
    """Get last N potential trading days as YYYYMMDD strings."""
    today = datetime.datetime.now(TZ_CHINA)
    days = []
    for i in range(1, n + 1):
        d = today - datetime.timedelta(days=i)
        if d.weekday() < 5:  # Mon-Fri
            days.append(d.strftime("%Y%m%d"))
    return days


def _fetch_url(url: str, timeout: int = 20, retries: int = 3) -> dict | None:
    """Helper to fetch JSON from a URL with retry logic."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://data.eastmoney.com/",
        "Accept": "application/json, text/plain, */*",
    }
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(1.5 * (attempt + 1))
            else:
                print(f"  HTTP error (retried {retries}x): {e}")
                return None
    return None


# ============================================================================
# A-share stock screening (via akshare)
# ============================================================================

def _get_recent_trading_days(n: int = 6) -> list[str]:
    """Get last N trading days as YYYYMMDD strings using akshare calendar."""
    try:
        import akshare as ak
        df = ak.tool_trade_date_hist_sina()
        if df is None or df.empty:
            raise ValueError("empty trade calendar")
        trade_dates = sorted(df["trade_date"].tolist(), reverse=True)
        today = datetime.datetime.now(TZ_CHINA).strftime("%Y-%m-%d")
        # Get past trading days (before today)
        past = [d for d in trade_dates if d < today]
        return [d.replace("-", "") for d in past[:n]]
    except Exception:
        pass

    # Fallback: use weekdays
    today = datetime.datetime.now(TZ_CHINA)
    days = []
    for i in range(1, n + 5):
        d = today - datetime.timedelta(days=i)
        if d.weekday() < 5:
            days.append(d.strftime("%Y%m%d"))
        if len(days) >= n:
            break
    return days


def get_limit_up_stocks_ak(date_str: str) -> list[dict]:
    """Get limit-up stocks for a given date using akshare."""
    try:
        import akshare as ak
        df = ak.stock_zt_pool_em(date=date_str)
        if df is None or df.empty:
            return []

        stocks = []
        for _, row in df.iterrows():
            code = str(row.get("代码", "")).strip()
            name = str(row.get("名称", "")).strip()
            pct = row.get("涨跌幅", 0) or 0
            if float(pct) >= 9.5:
                stocks.append({
                    "code": code,
                    "name": name,
                    "change_pct": round(float(pct), 2),
                    "limit_up_date": date_str,
                })
        return stocks
    except Exception as e:
        print(f"  akshare limit-up query failed for {date_str}: {e}")
        return []


def get_kline_ak(code: str, lookback: int = 25) -> list[dict] | None:
    """Fetch daily K-line data for an A-share stock using akshare."""
    try:
        import akshare as ak
        end_date = datetime.datetime.now(TZ_CHINA).strftime("%Y%m%d")
        start_date = (datetime.datetime.now(TZ_CHINA) - datetime.timedelta(days=lookback + 15)).strftime("%Y%m%d")
        df = ak.stock_zh_a_hist(symbol=code, period="daily",
                                start_date=start_date, end_date=end_date,
                                adjust="qfq")
        if df is None or df.empty or len(df) < 10:
            return None

        result = []
        for _, row in df.iterrows():
            result.append({
                "date": str(row.get("日期", ""))[:10].replace("-", ""),
                "open": float(row.get("开盘", 0) or 0),
                "close": float(row.get("收盘", 0) or 0),
                "high": float(row.get("最高", 0) or 0),
                "low": float(row.get("最低", 0) or 0),
                "volume": float(row.get("成交量", 0) or 0),
                "amount": float(row.get("成交额", 0) or 0),
            })
        return result
    except Exception as e:
        print(f"  akshare kline query failed for {code}: {e}")
        return None


def screen_a_stocks(max_stocks: int = 60) -> list[dict]:
    """Screen A-share stocks using akshare: limit-up in last 5 days + volume up + above MA5."""
    trading_days = _get_recent_trading_days(6)
    print(f"  交易日: {', '.join(trading_days[:5])}")

    # Phase 1: Get limit-up stocks for each trading day
    all_stocks: dict[str, dict] = {}
    for day in trading_days[:5]:
        print(f"  查询 {day} 涨停板...")
        stocks = get_limit_up_stocks_ak(day)
        if stocks:
            for s in stocks:
                code = s["code"]
                if code not in all_stocks:
                    all_stocks[code] = s
        time.sleep(0.5)

    if not all_stocks:
        print("  未获取到涨停股数据")
        return []

    print(f"  去重后共 {len(all_stocks)} 只涨停股，开始K线筛选...")

    # Sort by most recent limit-up date, take top N
    sorted_stocks = sorted(all_stocks.values(), key=lambda x: x["limit_up_date"], reverse=True)
    candidates = sorted_stocks[:max_stocks]

    results = []
    for i, stock in enumerate(candidates):
        code = stock["code"]
        if i > 0 and i % 10 == 0:
            time.sleep(0.8)
        elif i > 0:
            time.sleep(0.3)

        klines = get_kline_ak(code, lookback=25)
        if not klines:
            continue

        closes = [k["close"] for k in klines]
        volumes = [k["volume"] for k in klines]

        if len(closes) < 7:
            continue

        # MA5
        ma5 = sum(closes[-5:]) / 5
        ma5_dist = (closes[-1] - ma5) / ma5 * 100

        # Check: above MA5 for recent days (不跌破5日线)
        above_ma5 = True
        for j in range(1, min(4, len(closes))):
            c = closes[-j]
            ma = sum(closes[max(0, len(closes) - j - 4):len(closes) - j + 1]) / min(j + 1, 5)
            if c < ma * 0.98:
                above_ma5 = False
                break
        if not above_ma5:
            continue

        # Volume ratio: 5-day avg / 20-day avg
        if len(volumes) >= 20:
            vol_5 = sum(volumes[-5:]) / 5
            vol_20 = sum(volumes[-20:]) / 20
            vol_ratio = round(vol_5 / vol_20, 2)
        elif len(volumes) >= 10:
            vol_5 = sum(volumes[-5:]) / 5
            vol_20 = sum(volumes[:-5]) / (len(volumes) - 5)
            vol_ratio = round(vol_5 / vol_20, 2) if vol_20 > 0 else 0
        else:
            continue

        if vol_ratio < 1.1:
            continue

        # Volume trend
        if len(volumes) >= 5:
            first_half = sum(volumes[-5:-2]) / 3
            second_half = sum(volumes[-3:]) / 3
            vol_trend = "递增" if second_half > first_half else "维持"
        else:
            vol_trend = "—"

        results.append({
            "code": code,
            "name": stock["name"],
            "limit_up_date": stock["limit_up_date"],
            "limit_up_pct": stock["change_pct"],
            "vol_ratio": vol_ratio,
            "ma5_distance": round(ma5_dist, 2),
            "vol_trend": vol_trend,
            "close": round(closes[-1], 2),
        })

    results.sort(key=lambda x: (x["vol_ratio"], x["ma5_distance"]), reverse=True)
    return results


# ============================================================================
# Push text builder
# ============================================================================

def build_push_text(
    now: datetime.datetime,
    us_gainers: list[dict] | None,
    us_date: str,
    sector_heat: dict[str, int],
    sector_etfs: list[dict],
    a_results: list[dict],
    quote: dict[str, str] | None = None,
) -> str:
    weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    weekday = weekday_names[now.weekday()]
    date_str = now.strftime("%m月%d日")

    lines = [f"📈 每日股市播报 | {date_str} {weekday}"]

    # ── US stock top gainers ──
    if us_gainers:
        lines.append(f"\n━━━ 美股涨幅榜 TOP{len(us_gainers)} ({us_date}) ━━━")
        for i, g in enumerate(us_gainers, 1):
            icon = "🔴" if i <= 3 else ("🟠" if i <= 10 else "⚪")
            lines.append(
                f"{icon}{i:2d}. {g['name_cn']}({g['ticker']}) "
                f"{g['change_pct']:+.2f}%  [{g['sector']}]"
            )
    else:
        lines.append("\n【美股】今日暂无数据（可能为非交易日）")

    # ── Hot themes / sectors ──
    lines.append("\n【热门板块/题材】")
    if sector_heat:
        top_sectors = list(sector_heat.keys())[:5]
        lines.append(f"  🔥 涨幅榜集中板块: {'、'.join(top_sectors)}")

        # Theme analysis
        theme_keywords = {
            "AI芯片": ["AI芯片", "半导体", "半导体设备", "芯片IP", "数据中心芯片"],
            "软件云": ["软件云服务", "软件", "SaaS", "企业软件", "云监控", "数据库", "大数据AI"],
            "电动车": ["电动车", "中概电动车", "汽车芯片"],
            "消费": ["消费电子", "电商", "零售", "餐饮", "咖啡连锁", "运动服饰"],
            "金融": ["银行", "投行", "支付", "加密货币", "私募"],
            "医药健康": ["医药", "生物科技", "医疗保险", "医疗设备"],
            "能源": ["石油", "油气", "太阳能", "清洁能源", "油服"],
            "中概": ["中概电商", "中概AI", "中概电动车", "中概视频"],
        }

        hits = []
        for theme, keywords in theme_keywords.items():
            count = sum(sector_heat.get(k, 0) for k in keywords if k in sector_heat)
            if count >= 2:
                hits.append((theme, count))

        if hits:
            hits.sort(key=lambda x: x[1], reverse=True)
            themes_str = "、".join(f"{t}({c}只)" for t, c in hits[:4])
            lines.append(f"  📊 活跃题材: {themes_str}")
    else:
        lines.append("  暂无板块数据")

    # Sector ETF performance
    if sector_etfs:
        etf_parts = []
        for se in sector_etfs[:6]:
            sign = "+" if se["change_pct"] >= 0 else ""
            etf_parts.append(f"{se['sector']} {sign}{se['change_pct']:.2f}%")
        lines.append(f"  📈 ETF: {' | '.join(etf_parts)}")

    # ── A-share screening results ──
    lines.append(f"\n━━━ A股涨停筛选 (近5日涨停+放量+站上5日线) ━━━")
    if a_results:
        lines.append(f"  共筛选出 {len(a_results)} 只个股：")
        for i, s in enumerate(a_results[:10], 1):
            lu_date = s["limit_up_date"][4:6] + "/" + s["limit_up_date"][6:8]
            lines.append(
                f"  {i:2d}. {s['code']} {s['name']}  "
                f"涨停:{lu_date}  "
                f"量比:{s['vol_ratio']}  "
                f"距5线:{s['ma5_distance']:+.1f}%  "
                f"量能:{s['vol_trend']}"
            )
    else:
        lines.append("  暂无符合条件的个股（或非交易日）")

    # ── Quote ──
    if quote:
        lines.append(f"\n📖 {quote['text']}")
        lines.append(f"  —— {quote['author']}")

    lines.append(f"\n⚠️ 以上内容仅供参考，不构成投资建议。")
    return "\n".join(lines)


# ============================================================================
# Push notification
# ============================================================================

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


# ============================================================================
# Main
# ============================================================================

def main():
    now = datetime.datetime.now(TZ_CHINA)
    do_push = "--push" in sys.argv or os.environ.get("PUSH_TOKEN")

    print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] 正在获取股市数据...")

    quote = pick_quote()
    print(f"  今日名言: {quote['text'][:30]}... ——{quote['author']}")

    # 1. US stock top gainers
    print("\n── 美股数据 ──")
    us_result = get_us_top_gainers(top_n=10)
    us_gainers: list[dict] = []
    us_date = ""
    sector_heat: dict[str, int] = {}
    sector_etfs: list[dict] = []

    if us_result:
        us_gainers, us_date = us_result
        print(f"  获取到 {len(us_gainers)} 只涨幅居前个股 ({us_date})")
        sector_heat = get_us_sector_heat(us_gainers)
        sector_etfs = get_us_sector_etf_performance()
        for g in us_gainers[:5]:
            print(f"    {g['ticker']} {g['name_cn']} +{g['change_pct']:.2f}%")
    else:
        print("  美股数据获取失败，跳过")

    # 2. A-share screening
    print("\n── A股涨停筛选 ──")
    a_results = screen_a_stocks(max_stocks=60)
    print(f"  筛选出 {len(a_results)} 只符合条件的个股")
    for s in a_results[:5]:
        print(f"    {s['code']} {s['name']} 涨停:{s['limit_up_date']} 量比:{s['vol_ratio']}")

    # 3. Build and send push
    push_content = build_push_text(now, us_gainers if us_gainers else None, us_date,
                                   sector_heat, sector_etfs, a_results, quote)
    print(f"\n── 推送内容预览 ──")
    print(push_content[:500])

    if do_push:
        push_title = f"📈 股市播报 {now.strftime('%m月%d日')}"
        ok = send_push(push_title, push_content)
        print(f"  推送结果: {'成功' if ok else '失败'}")
    else:
        print("  (未启用推送，使用 --push 或设置 PUSH_TOKEN 环境变量)")


def generate_sample():
    """Generate a sample push to verify the text format."""
    now = datetime.datetime.now(TZ_CHINA)
    sample_gainers = [
        {"ticker": "NVDA", "name_cn": "英伟达", "change_pct": 8.52, "sector": "AI芯片"},
        {"ticker": "AMD", "name_cn": "AMD", "change_pct": 7.31, "sector": "半导体"},
        {"ticker": "TSLA", "name_cn": "特斯拉", "change_pct": 5.20, "sector": "电动车"},
        {"ticker": "MSFT", "name_cn": "微软", "change_pct": 3.15, "sector": "软件云服务"},
        {"ticker": "AVGO", "name_cn": "博通", "change_pct": 2.88, "sector": "半导体"},
        {"ticker": "PLTR", "name_cn": "Palantir", "change_pct": 2.50, "sector": "大数据AI"},
        {"ticker": "META", "name_cn": "Meta", "change_pct": 2.10, "sector": "社交元宇宙"},
        {"ticker": "AMZN", "name_cn": "亚马逊", "change_pct": 1.95, "sector": "电商云服务"},
        {"ticker": "SMCI", "name_cn": "超微电脑", "change_pct": 1.80, "sector": "AI服务器"},
        {"ticker": "UBER", "name_cn": "优步", "change_pct": 1.65, "sector": "出行平台"},
        {"ticker": "CRM", "name_cn": "赛富时", "change_pct": 1.50, "sector": "企业软件"},
        {"ticker": "CRWD", "name_cn": "CrowdStrike", "change_pct": 1.45, "sector": "网络安全"},
        {"ticker": "AAPL", "name_cn": "苹果", "change_pct": 1.30, "sector": "消费电子"},
        {"ticker": "LLY", "name_cn": "礼来", "change_pct": 1.25, "sector": "医药"},
        {"ticker": "JPM", "name_cn": "摩根大通", "change_pct": 1.10, "sector": "银行"},
    ]
    sample_sector_heat = {"半导体": 2, "AI芯片": 1, "电动车": 1, "软件云服务": 1, "大数据AI": 1}
    sample_etfs = [
        {"sector": "科技", "etf": "XLK", "change_pct": 2.1},
        {"sector": "通信", "etf": "XLC", "change_pct": 1.5},
        {"sector": "消费", "etf": "XLY", "change_pct": 0.8},
        {"sector": "金融", "etf": "XLF", "change_pct": -0.3},
        {"sector": "能源", "etf": "XLE", "change_pct": -0.5},
    ]
    sample_a = [
        {"code": "600519", "name": "贵州茅台", "limit_up_date": "20260723", "vol_ratio": 2.15,
         "ma5_distance": 2.3, "vol_trend": "递增"},
        {"code": "000858", "name": "五粮液", "limit_up_date": "20260722", "vol_ratio": 1.85,
         "ma5_distance": 1.5, "vol_trend": "维持"},
        {"code": "300750", "name": "宁德时代", "limit_up_date": "20260723", "vol_ratio": 1.72,
         "ma5_distance": 3.1, "vol_trend": "递增"},
        {"code": "002594", "name": "比亚迪", "limit_up_date": "20260721", "vol_ratio": 1.56,
         "ma5_distance": 0.8, "vol_trend": "递增"},
        {"code": "601012", "name": "隆基绿能", "limit_up_date": "20260723", "vol_ratio": 1.48,
         "ma5_distance": 2.7, "vol_trend": "维持"},
    ]
    quote = pick_quote()
    text = build_push_text(now, sample_gainers, "07月23日", sample_sector_heat,
                           sample_etfs, sample_a, quote)
    print("=" * 60)
    print(text)
    print("=" * 60)
    print("\nSample push text generated successfully.")


if __name__ == "__main__":
    if "--sample" in sys.argv:
        generate_sample()
    else:
        main()
