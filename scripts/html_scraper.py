import requests
from bs4 import BeautifulSoup

# 1) target URL
url = "https://www.tennisabstract.com/charting/20241016-M-Almaty-R16-Justin_Engel-Francisco_Cerundolo.html"
url = "https://tennisabstract.com/charting/meta.html"

# 2) Download page
response = requests.get(url)
response.raise_for_status()  # stop if request failed

# 3) Parse HTML with BeautifulSoup
soup = BeautifulSoup(response.text, "html.parser")

# 4) Find the specific table(s)
#    If there are multiple tables on the page, use soup.find_all("table")
table = soup.find_all("table")[1]

# 5) Extract headers (if the table has any)
headers = []
thead = table.find("thead")
if thead:
    headers = [th.get_text(strip=True) for th in thead.find_all("th")]

# 6) Extract all row data
rows = []
for tr in table.find_all("tr"):
    vals = tr.find_all("td")
    current_rank = vals[0].get_text(strip=True)
    player = vals[1]

    print(f"Found {len(vals)} Values: {vals}")
    quit()
    row = [td.get_text(strip=True) for td in tr.find_all(["td","th"])]
    if row:
        rows.append(row)

# 7) Print or work with the data
print("Headers:", headers)
for r in rows:
    print(r)
