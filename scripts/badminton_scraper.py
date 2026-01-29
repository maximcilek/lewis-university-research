import asyncio
import json
from playwright.async_api import async_playwright
from urllib.parse import urlparse
from datetime import datetime, timezone

# =====================
# CONFIG
# =====================

LOG_CONFIG = {
    "log_headers": False,
    "log_all_responses": False,
    "truncate_len": 50
}


# =====================
# UTILITIES
# =====================

def truncate(text: str, max_len=50):
    if len(text) <= max_len:
        return text
    return f"{text[:35]}...{text[-15:]}"


def format_time(ms):
    if not ms:
        return "N/A"
    dt = datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC")


# =====================
# LOGGING
# =====================

async def log_headers(req):
    headers = await req.all_headers()
    if not headers:
        return

    print("\n--- HEADERS ---")
    for k, v in headers.items():
        print(f"{k}: {v}")


async def log_post_data(req):
    try:
        source = None
        value = None

        # Try JSON first (best for humans)
        try:
            post_json = req.post_data_json
            if post_json:
                source = "json"
                value = json.dumps(post_json)
        except:
            pass

        # Then raw string
        if not value:
            raw = req.post_data
            if raw:
                source = "string"
                value = raw

        # Then binary buffer
        if not value:
            buf = req.post_data_buffer
            if buf:
                source = "buffer"
                value = buf

        if not value:
            return

        host = urlparse(req.url).hostname or "unknown"

        print(f"[INFO] - Post Data ({host}) [{source}]:", end=" ")

        if isinstance(value, str):
            print(truncate(value, LOG_CONFIG["truncate_len"]))
        elif isinstance(value, (bytes, bytearray)):
            preview = value[:25]
            print(f"{preview}... (total {len(value)} bytes)")
        else:
            print(f"[WARN] - Unknown post data type: {type(value)}")

    except Exception as e:
        print("[WARN] - POST data unavailable:", e)


async def log_request(req):
    if req.resource_type not in ("xhr", "fetch"):
        return

    url = req.url
    print(f"[INFO] - {req.method} {req.resource_type.upper()} -> {truncate(url)}")

    if LOG_CONFIG["log_headers"]:
        await log_headers(req)

    if req.method == "POST":
        await log_post_data(req)

    if req.failure:
        print("[ERROR] - Request Failure:", req.failure)


# =====================
# RESPONSE HANDLER
# =====================

def make_response_logger(results_store: dict):
    async def log_response(response):
        ct = response.headers.get("content-type", "")
        if "application/json" not in ct:
            return

        url = urlparse(response.url)
        endpoint = f"{url.scheme}://{url.hostname}{url.path}"

        try:
            data = await response.json()
        except Exception as e:
            print(f"[WARN] - Invalid JSON from {endpoint}: {e}")
            return

        # Store result
        results_store[endpoint] = data

        timing = response.request.timing
        start = timing.get("startTime", 0)
        req_start = timing.get("requestStart", 0)
        resp_start = timing.get("responseStart", 0)
        resp_end = timing.get("responseEnd", 0)

        ttfb = (resp_start - req_start) if resp_start >= 0 else -1
        download = (resp_end - resp_start) if resp_end >= 0 else -1
        total = (resp_end - req_start) if resp_end >= 0 else -1

        print(
            f"[INFO] - JSON {endpoint}\n"
            f"         Start:   {format_time(start)}\n"
            f"         TTFB:    {ttfb:.2f} ms\n"
            f"         Download: {download:.2f} ms\n"
            f"         Total:   {total:.2f} ms"
        )

    return log_response


# =====================
# PAGE FETCH
# =====================

async def fetch(page, url):
    print(f"[INFO] - Visiting Page: {url}")

    results = {}

    page.on("request", log_request)
    page.on("response", make_response_logger(results))

    await page.goto(url, wait_until="domcontentloaded")
    await asyncio.sleep(5)

    return results


# =====================
# MAIN
# =====================

async def main():
    frontend_urls = [
        "https://bwfbadminton.com/calendar/"
    ]

    all_results = {}

    async with async_playwright() as p:
        print("\n[INFO] - Launching browser")
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        for url in frontend_urls:
            results = await fetch(page, url)
            all_results.update(results)

        print("\n==========================================")
        print("FINAL RESULTS")
        print("==========================================")

        for k, v in all_results.items():
            if isinstance(v, list):
                print(f"{k}: {len(v)} records")
            elif isinstance(v, dict):
                print(f"{k}: {len(v)} keys")
            else:
                print(f"{k}: {type(v)}")

        await browser.close()
        print("[INFO] - Browser closed cleanly")


if __name__ == "__main__":
    asyncio.run(main())


    # items: List[str]
    # url = "https://extranet-lv.bwfbadminton.com/api/tournaments/day-matches?tournamentCode=2DFC9259-FA31-48EB-A9F3-5A7C98457593&date=2026-01-15&order=2&court=0"

"""
request_log = {
    "Method": req.method,
    "URL": req.url,
    "Resource Type": req.resource_type,
    "Is Navigation Request": req.is_navigation_request(),
    "Service Worker": req.service_worker,
    "Redirected From URL": req.redirected_from.url if req.redirected_from else None,
    "Redirected To URL": req.redirected_to.url if req.redirected_to else None,
    # "Frame URL": req.frame.url if req.frame else None
}

# for k, v in request_log.items():
    #     if v:
    #         print(f"{k}:  {v}")
"""
