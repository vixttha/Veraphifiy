import json
import os
import re
from pathlib import Path
from playwright.sync_api import expect, sync_playwright

base = Path(__file__).parent
page_file = base / "Veraphify-Mind-Map.html"
source = page_file.read_text()
data = json.loads(re.search(r'<script type="application/json" id="catalog">([\s\S]*?)</script>',source)[1])
catalog = {record["id"]:record for record in data["records"]}
assert len(catalog) == 77 and len(data["groups"]) == 5
seen = set()
errors = []
requests = []
with sync_playwright() as p:
    browser_opts = {"args":["--no-sandbox","--disable-dev-shm-usage"]}
    if os.environ.get("VFY_CHROMIUM"):
        browser_opts["executable_path"] = os.environ["VFY_CHROMIUM"]
        browser_opts["args"] += ["--headless=shell","--no-zygote","--single-process"]
    browser = p.chromium.launch(**browser_opts)
    page = browser.new_page(viewport={"width":1440,"height":900})
    page.on("pageerror",lambda error:errors.append(str(error)))
    page.on("console",lambda msg:errors.append(msg.text) if msg.type == "error" else None)
    page.on("request",lambda req: requests.append(req.url))
    origin = page_file.resolve().as_uri()
    page.goto(origin)
    assert page.get_by_role("heading",name="Ideas & features").count() == 1
    assert page.locator(".branch").count() == 5 and page.locator(".records").count() == 0
    assert not page.get_by_text("85 directed idea references",exact=False).is_visible()
    page.get_by_role("link",name="Features",exact=True).click()
    page.wait_for_url("**#/overview/features")
    page.mouse.move(0,0)
    page.screenshot(path=str(base/"Veraphify-Overview.png"),full_page=True)
    for group in data["groups"]:
        page.goto(origin+"#/overview/features")
        page.locator(".branch").filter(has_text=group["label"]).click()
        page.wait_for_url("**#/"+group["id"]+"/features")
        expect(page.get_by_role("heading",name=group["label"],exact=True)).to_be_visible()
        if group["id"] == "discover":
            page.mouse.move(0,0)
            page.screenshot(path=str(base/"Veraphify-Discover.png"),full_page=True)
        for mode in ("features","ideas"):
            page.goto(origin+"#/"+group["id"]+"/"+mode)
            rows = page.locator(".record")
            expect(rows).to_have_count(len(group[mode]))
            for n, record_id in enumerate(group[mode]):
                page.locator(".record").nth(n).click()
                page.wait_for_url("**/"+record_id)
                expect(page.locator("h1")).to_have_text(catalog[record_id]["title"])
                assert page.locator(".external").get_attribute("href").endswith("/"+record_id+".json")
                seen.add(record_id)
                page.go_back()
                page.wait_for_url("**#/"+group["id"]+"/"+mode)
    assert seen == set(catalog)
    page.goto(origin+"#/archive/features/FEAT-000003")
    page.locator(".relationships summary").click()
    assert page.locator(".relationships .links a").count() == len(catalog["FEAT-000003"]["origins"])
    relation_id = page.locator(".relationships .links a .mono").first.inner_text()
    page.locator(".relationships .links a").first.click()
    page.wait_for_url("**/"+relation_id)
    expect(page.locator("h1")).to_have_text(catalog[relation_id]["title"])

    page.set_viewport_size({"width":360,"height":800})
    for route in ["/overview/features",*[f'/{g["id"]}/{m}' for g in data["groups"] for m in ("ideas","features")]]:
        page.goto(origin+"#"+route)
        assert page.evaluate("document.documentElement.scrollWidth === innerWidth"),route
    page.goto(origin+"#/discover/features")
    page.screenshot(path=str(base/"Veraphify-Mobile.png"),full_page=True)
    page.goto(origin+"#/discover/features/IDEA-000001")
    expect(page.locator("h1")).to_have_text("Discover")
    assert not [r for r in requests if not r.startswith("file:")]
    assert not errors,errors
    browser.close()
print("Browser audit passed: 5 branch pages, 10 category views, 77 record pages, directed links, history, mobile overflow, and offline behavior.")

