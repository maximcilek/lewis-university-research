import re
import json
import aiohttp
import aiofiles
import asyncio
from aiolimiter import AsyncLimiter
from pathlib import Path
from bs4 import BeautifulSoup

MAX_RETRIES = 3
CHARTING_BASE_URL = "https://www.tennisabstract.com/charting/"
DEFAULT_HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"}

tennisabstract_players = set()

def get_match_outcome_and_score(soup: BeautifulSoup):
    outcome_text = soup.find_next("b").get_text(strip=True)
    outcome_match = re.match(r'^(.*?)\s+(\d+-\d+(?:\(\d+\))?(?:\s+\d+-\d+(?:\(\d+\))?)*)$', outcome_text)
    if not outcome_match or len(outcome_match.groups()) != 2:
        raise ValueError(f"Failed regex match on outcome and match score: {outcome_text!r}")        
    try:
        winner_name, loser_name = outcome_match.group(1).split(" d. ", maxsplit=1)
        return winner_name.strip(), loser_name.strip(), outcome_match.group(2).strip()
    except ValueError:
        raise ValueError(f"Cannot parse match winner or loser: {outcome_text!r}")

async def handle_response(response, matches_file):
    print(f"Received Response ({response.status}): {response.headers.get('Content-Type')}: {response.request_info.url.name}")
    
    soup = BeautifulSoup(await response.text(), 'html.parser')
    match_header = soup.find("h2")

    match_url = CHARTING_BASE_URL + response.request_info.url.name
    match_id = response.request_info.url.name.replace(".html", "")
    match_info = dict(zip(["match_date", "gender", "tournament_name", "round"], match_id.split("-", maxsplit=6)))
    
    players = []
    for hyperlink in match_header.find_all('a', href=True):
        profile_url = hyperlink['href'].replace("player.cgi", "player-classic.cgi")
        players.append({"profile_url": profile_url, "display_name": hyperlink.get_text(strip=True)})
        if profile_url not in tennisabstract_players:
            tennisabstract_players.add(profile_url)
    
    winner_name, loser_name, match_score = get_match_outcome_and_score(match_header)
    match_info.update({"match_id": match_id, "match_score": match_score if match_score else None})
    for c, p in enumerate(players):
        if winner_name.lower() == p["display_name"].lower():
            p["won"] = True
        if loser_name.lower() == p["display_name"].lower():
            p["won"] = False
        match_info[f"player_{c+1}"] = p
    
    await matches_file.write(json.dumps(match_info) + "\n")


async def fetch(session, url, limiter, matches_file):
    for attempt in range(MAX_RETRIES):
        try:
            async with limiter:
                async with session.get(url) as resp:
                    if resp.status == 429:
                        retry_after = resp.headers.get("Retry-After")
                        wait = float(retry_after) if retry_after else (2 ** attempt)
                        attempts_left = MAX_RETRIES - (attempt + 1)
                        print(f"429 Rate Limited. Sleeping {wait:.2f}s — Attempts left: {attempts_left}")
                        await asyncio.sleep(wait)
                        continue

                    if resp.status in (500, 502, 503, 504):
                        raise Exception(f"Server Error ({resp.status})")
                    return await handle_response(resp, matches_file)
        except Exception as e:
            print(f"Failed Request Attempt: {e}")
            attempts_left = MAX_RETRIES - (attempt + 1)
            if attempts_left == 0:
                print(f"Request Failed (attempts: {MAX_RETRIES}): {url}")
                return None
            # Exponential backoff + jitter
            wait = (2 ** attempt) + random.uniform(0.1, 0.5)
            print(f"Retry {attempts_left}/{MAX_RETRIES} ({wait:.2f}s): {url}")
            await asyncio.sleep(wait)

def load_urls(fp):
    with open(fp, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

async def main():
    print("-------------------------------------")
    print("SCRAPING TENNISABSTRACT CHARTING DATA")
    print("-------------------------------------")
    data_directory = Path(__file__).resolve().parent.parent.parent / "data" / "dev"

    urls_fp = data_directory / "charting_matches_urls.txt"    
    matches_fp = data_directory / "charting_matches.jsonl"
    players_fp = data_directory / "charting_players.txt"

    urls = load_urls(urls_fp) # [:100]
    print(f"FOUND {len(urls)} URLs (Charting Matches)")
    
    limiter = AsyncLimiter(10, 1)
    async with aiohttp.ClientSession() as session:
        async with aiofiles.open(matches_fp, "a", encoding="utf-8") as matches_file:
            tasks = [fetch(session, url, limiter, matches_file) for url in urls]
            await asyncio.gather(*tasks, return_exceptions=True)

    with open(players_fp, "w", encoding="utf-8") as f:
        for p in tennisabstract_players:
            f.write(p + "\n")

if __name__ == "__main__":
    asyncio.run(main())