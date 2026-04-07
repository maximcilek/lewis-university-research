import re
import ast
import json
import aiohttp
import aiofiles
import asyncio
from aiolimiter import AsyncLimiter
from pathlib import Path
from bs4 import BeautifulSoup
import random
import traceback
import chardet
import gzip

MAX_RETRIES = 3
DEFAULT_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:149.0) Gecko/20100101 Firefox/149.0"
}

tennisabstract_players = {}
javascript_urls = []

PLAYER_ATTRIBUTES = ["active", "atp_id", "backhand", "blast_link", "careerjs", "chartagg", "country", "current_dubs", "currentrank", "dc_id",
        "death_date", "dob", "dob_approx", "elo_rank", "elo_rating", "exclude", "ht", "opp_team", "opponent", "fc_id", "fullname", "hand", "itf_id",
        "lastdate", "lastname", "liverank", "more_link", "nameparam", "partner", "peak_dubs", "peakfirst", "peakfirst_dubs", "peaklast", "peakrank", "photog",
        "photog_credit", "photog_link", "shortlist", "twitter", "wiki_id", "wta_id", "matchmx"] # "ychoices", "tchoices", "tdates"

# Rate Limited
rate_limited_until = 0
rate_limit_lock = asyncio.Lock()

def parse_html_js_array(var_name, html):
    match = re.search(rf"var {var_name}\s*=\s*(\[[\s\S]*?\]);", html)
    if not match:
        return None
    return json.loads(match.group(1))

def parse_html_js_value(var_name, html):
    match = re.search(
        rf"var\s+{var_name}\s*=\s*(.*?);",
        html,
        re.DOTALL
    )
    
    if not match:
        return None

    value = match.group(1).strip()

    # -----------------------
    # STRING
    # -----------------------
    if value.startswith(("'", '"')):
        return value.strip('"\'')
    
    # -----------------------
    # NULL
    # -----------------------
    if value == "null":
        return None

    # -----------------------
    # NUMBER (int / float)
    # -----------------------
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        pass

    # -----------------------
    # FALLBACK (raw string)
    # -----------------------
    return value

def parse_js_vars(text, var_names):
    data = {}

    for var_name in var_names:

        # Match ANY JS var assignment robustly
        match = re.search(
            rf'var\s+{var_name}\s*=\s*(.*?);',
            text,
            re.DOTALL
        )

        if not match:
            data[var_name] = None
            continue

        value = match.group(1).strip()

        try:
            # -----------------------
            # STRING (possibly JSON)
            # -----------------------
            if value.startswith(("'", '"')):
                value = value.strip('"\'')
                
                # Try parsing JSON inside string
                if value.startswith("["):
                    try:
                        data[var_name] = json.loads(value)
                    except:
                        data[var_name] = ast.literal_eval(value)
                else:
                    data[var_name] = value

            # -----------------------
            # ARRAY
            # -----------------------
            elif value.startswith("["):
                try:
                    data[var_name] = json.loads(value.replace("'", '"'))
                except:
                    data[var_name] = ast.literal_eval(value)

            # -----------------------
            # NULL / EMPTY
            # -----------------------
            elif value in ("null", ""):
                data[var_name] = None

            # -----------------------
            # NUMBER
            # -----------------------
            else:
                try:
                    data[var_name] = int(value)
                except:
                    data[var_name] = float(value)

        except Exception:
            data[var_name] = None

    return data

async def save_player_file(player, filename, content, compress=False):
    player_dir = Path("/home/mcilek/Github/maximcilek/lewis-university-research/data/raw/tennisabstract/players") / player
    player_dir.mkdir(parents=True, exist_ok=True)

    if compress:
        fp = player_dir / f"{filename}.gz"
        async with aiofiles.open(fp, "wb") as f:
            await f.write(gzip.compress(content.encode("utf-8")))
    else:
        fp = player_dir / filename
        async with aiofiles.open(fp, "w", encoding="utf-8") as f:
            await f.write(content)

async def handle_response(response):
    url = str(response.request_info.url)
    text = await response.text(errors="ignore")
    if ("cgi-bin" in url):
        paramname = url.split("?")[1].split("&")[0].replace("p=", "")
        await save_player_file(paramname, "html-profile.html", text, compress=False)
    elif (".js" in url):
        paramname = url.split("/")[-1].replace("Career","").replace(".js", "")
        if "Career.js" in url:
            await save_player_file(paramname, "js-career-profile", text, compress=True)
        elif f"{paramname}.js" in url:
            await save_player_file(paramname, "js-profile", text, compress=True)
    else:
        raise ValueError(f"Unexpected URL cannot parse player paramname: {url}")

    print(f"Received Response ({response.status}): \t{response.headers.get('Content-Type')}: {str(response.request_info.url).replace('https://www.tennisabstract.com/', '')} - {paramname}")
    
    """soup = BeautifulSoup(text, "html.parser")
        if soup.find(id='abovestats').find("span", {"class": "statsw stattab likelink"}) is not None:
            tennisabstract_players[paramname] = {k: None for k in PLAYER_ATTRIBUTES}
            for k in PLAYER_ATTRIBUTES:
                if k == "matchmx":
                    tennisabstract_players[paramname]["matches"] = parse_html_js_array("matchmx", text)
                else:
                    tennisabstract_players[paramname][k] = parse_html_js_value(k, text)
                if "/wplayer-classic.cgi" in url:
                    tennisabstract_players[paramname]["gender"] = "W"
                if "/player-classic.cgi" in url:
                    tennisabstract_players[paramname]["gender"] = "M"
    """

    
    # javascript_urls.append(f"https://www.tennisabstract.com/jsmatches/{paramname}.js")


async def fetch(session, limiter, url):
    global rate_limited_until
    for attempt in range(MAX_RETRIES):
        try:
            async with rate_limit_lock:
                ts = asyncio.get_event_loop().time()
                if ts < rate_limited_until:
                    sleep_time = rate_limited_until - ts
                    print(f"\tGLOBAL COOLDOWN: {sleep_time:.1f}s")
                    await asyncio.sleep(sleep_time)

            async with limiter:
                async with session.get(url, headers=DEFAULT_HEADERS) as resp:
                    if resp.status == 404:
                        break
                    if resp.status == 429:
                        retry_after = resp.headers.get("Retry-After")
                        wait = float(retry_after)+1 if retry_after else (10 + random.uniform(0.5,1.5))
                        async with rate_limit_lock:
                            rate_limited_until = asyncio.get_event_loop().time() + wait
                        continue
                    if resp.status in (500, 502, 503, 504, 403):
                        raise Exception(f"Server Error ({resp.status})")
                    await handle_response(resp)
                    return
        except Exception as e:
            attempts_left = MAX_RETRIES - (attempt + 1)
            if attempts_left == 0:
                print(f"Request Failed (attempts: {attempts_left}): {url} - {str(e)}")
                traceback.print_exc()
                return

            # Exponential backoff + jitter
            wait = (2 ** attempt) + random.uniform(0.5, 1.5)
            print(f"Retry {attempts_left}/{MAX_RETRIES} ({wait:.1f}s): {url} - {str(e)}")
            await asyncio.sleep(wait)

async def process_player(session, limiter, semaphore, players_file, player_name, url_list):
    async with semaphore:  # limit concurrent players
        for url in url_list:
            await fetch(session, limiter, url)
        # if player_name in tennisabstract_players:
        #     print(f"Successfully Processed {player_name}'s Profile")
        #     await players_file.write(json.dumps({player_name: tennisabstract_players[player_name]}) + "\n")
        #     del tennisabstract_players[player_name]
        # elif f"https://www.tennisabstract.com/jsmatches/{player_name}.js" in javascript_urls:
        #   print(f"[DEBUG] - JavaScript Player URLs: {len(javascript_urls)}")
        #   return
        # else:
        #     print(f"WARNING: {player_name} had no data collected")

def load_urls(fp):
    urls = {}
    with open(fp, "r", encoding="utf-8") as f:
        for url in f:
            if url.strip():
                paramname = url.split("?p=")[1].strip()
                urls[paramname] = [
                    url.strip() + "&f=ACareerqqw1", 
                    f"https://www.tennisabstract.com/jsmatches/{paramname}.js", 
                    f"https://www.tennisabstract.com/jsmatches/{paramname}Career.js"
                ]
    return urls

async def main():
    global javascript_urls
    print("-------------------------------------")
    print("SCRAPING TENNISABSTRACT CHARTING DATA")
    print("-------------------------------------")
    data_directory = Path(__file__).resolve().parent.parent.parent / "data" / "dev"

    urls_fp = data_directory / "charting_players_urls.txt"
    players_fp = data_directory / "player_profiles_test.jsonl"
    players_javascript_fp = data_directory / "charting_players_js_test.txt"

    urls = load_urls(urls_fp)
    print(f"FOUND {len(urls)} PROFILE URLs (Charting Players)")

    limiter = AsyncLimiter(1, 3)
    semaphore = asyncio.Semaphore(3)
    async with aiohttp.ClientSession(requote_redirect_url=False) as session:
        async with aiofiles.open(players_fp, "a", encoding="utf-8") as players_file:
            tasks = [process_player(session, limiter, semaphore, players_file, player_name, url_list) for player_name, url_list in urls.items()]
            await asyncio.gather(*tasks) #, return_exceptions=True)

    # javascript_urls = list(set(javascript_urls))
    # async with aiofiles.open(players_javascript_fp, "a", encoding="utf-8") as players_javascript_file:
    #     await players_javascript_file.write("\n".join(javascript_urls) + "\n")


if __name__ == "__main__":
    asyncio.run(main())

#if "morematchmx" in tennisabstract_players[player_name] and (type(tennisabstract_players[player_name]["morematchmx"]) == list and len(tennisabstract_players[player_name]["morematchmx"]) > 0):
#    tennisabstract_players[player_name]["matchmx"].extend(tennisabstract_players[player_name]["morematchmx"])
    #del tennisabstract_players[player_name]["morematchmx"]
# tennisabstract_players[player_name]["matchmx"] = [list(match) for match in set(tuple(m) for m in tennisabstract_players[player_name]["matchmx"])]
    