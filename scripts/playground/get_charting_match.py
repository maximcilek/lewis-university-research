import requests, re
from bs4 import BeautifulSoup

def normalize_soup_text(soup, strip=True):
    return soup.get_text(strip=strip).replace("\u2011", "-")

def get_point_rows(html):
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.find_all("tr")
    point_table_headers = [th.get_text(strip=True) for th in rows[0].find_all("th", attrs={"align": "left"})]
    if point_table_headers == ['Server', 'Sets', 'Games', 'Points']:
        point_table_headers.append("Description")
    else:
        print(f"[WARNING] - Point Table Header Unexpected Column: {point_table_headers}")
        quit()
    return point_table_headers, rows[1:]

url = "https://www.tennisabstract.com/charting/20000306-M-Scottsdale-SF-Lleyton_Hewitt-Juan_Carlos_Ferrero.html"

headers = {
    "User-Agent": "Mozilla/5.0"
}

html = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}).text

# pattern = r"var serve\s*=\s*'(.*?)';\s*var serve1\s*=\s*'(.*?)';\s*var pointlog\s*=\s*'(.*?)';"
pattern = r"var pointlog\s*=\s*'(.*?)';"



match = re.search(pattern, html, re.DOTALL)

#serve_html = match.group(1)
#serve1_html = match.group(2)
pointlog = match.group(1)
point_table_headers, point_rows = get_point_rows(pointlog)
print(point_table_headers)
print("------------------------------------------------")
prev_point_cols = None
for p in point_rows:
    point_cols = p.find_all("td")
    if not normalize_soup_text(point_cols[0]):
        print(f"Empty Point Row Cell: {p}")
        prev_game_points = normalize_soup_text(prev_point_cols[3]).split("-")
        prev_game_sets = normalize_soup_text(prev_point_cols[3]).split("-")
        print(f"Finished Game: {prev_game_points}")
        quit()
    try:
        point_server_name = normalize_soup_text(point_cols[0])
        server_sets, returner_sets = normalize_soup_text(point_cols[1]).split("-")
        server_games, returner_games = normalize_soup_text(point_cols[2]).split("-")
        server_points, returner_points = normalize_soup_text(point_cols[3]).split("-")
        point_description = normalize_soup_text(point_cols[-1])
        if any(s is None or s == "" for s in [point_server_name, server_sets, returner_sets, server_games, returner_games, server_points, returner_points, point_description]):
            print(f"[FATAL] - Point Row Missing Value(s): {p}")
            quit()

        print(f"Server: {point_server_name}")
        print(f"Sets (S-R): {server_sets}-{returner_sets}")
        print(f"Games (S-R): {server_games}-{returner_games}")
        print(f"Points (S-R): {server_points}-{returner_points}")
        print(f"Description: {point_description}")
    except:
        print(f"[FATAL] - Failed to parse point\n")
        print(point_cols, len(point_cols))
        quit()
    
    print(f"====================================================================================")
    prev_point_cols = point_cols