"""Browser and visual smoke checks. Requires Playwright and Microsoft Edge."""

from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
URL = (ROOT / "index.html").as_uri()
PREVIEWS = ROOT / "docs"
PREVIEWS.mkdir(exist_ok=True)

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(channel="msedge", headless=True)
    for device, width, height in (("desktop", 1440, 900), ("mobile", 390, 844), ("compact", 320, 568)):
        page = browser.new_page(viewport={"width": width, "height": height}, device_scale_factor=1)
        page.emulate_media(reduced_motion="reduce")
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(URL)
        page.locator("#hero-title").wait_for()

        assert page.locator(".chapter").count() == 5
        assert page.locator("#hero-dot-grid .data-cell").count() == 100
        assert page.locator(".start-link").get_attribute("href") == "#du-doan"
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), device
        page.screenshot(path=str(PREVIEWS / f"preview-{device}.png"))

        page.locator("#du-doan").evaluate(
            "el => el.scrollIntoView({block: 'center', behavior: 'instant'})"
        )
        assert page.locator("#guess-grid span").count() == 100
        assert page.locator("#guess-grid .is-guessed").count() == 25
        page.locator(".read-progress").evaluate("el => el.style.visibility = 'hidden'")
        page.locator(".guess-card").screenshot(path=str(PREVIEWS / f"quiz-before-{device}.png"))
        page.locator("#guess-range").evaluate(
            "el => { el.value = '58'; el.dispatchEvent(new Event('input', {bubbles: true})); }"
        )
        assert page.locator("#guess-value").inner_text() == "58"
        assert page.locator("#guess-grid .is-guessed").count() == 58
        page.locator("#guess-submit").click()
        assert page.locator("#guess-result").is_visible()
        assert page.locator("#guess-yours").inner_text() == "58"
        assert page.locator("#guess-grid .is-actual").count() == 34
        assert "58%" in page.locator("#guess-compare").get_attribute("style")
        assert "cao hơn" in page.locator("#guess-feedback").inner_text()
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), device
        page.locator(".guess-card").screenshot(path=str(PREVIEWS / f"quiz-result-{device}.png"))
        page.locator("#du-doan").screenshot(path=str(PREVIEWS / f"quiz-section-{device}.png"))
        page.locator(".read-progress").evaluate("el => el.style.visibility = ''")

        page.locator("#thu-nhap").evaluate(
            "el => el.scrollIntoView({block: 'center', behavior: 'instant'})"
        )
        page.wait_for_timeout(120)
        assert page.locator(".viz--income").is_visible()
        assert page.locator("#income-guess-note").is_visible()
        assert "Bạn đoán 58%" in page.locator("#income-guess-note").inner_text()
        assert "24 điểm phần trăm" in page.locator("#income-guess-note").inner_text()
        assert page.locator("#income-axis span").all_inner_texts() == ["0", "15", "30", "45", "60%"]
        assert not page.locator("#income-guess-marker").is_hidden()
        marker_position = page.locator("#income-guess-marker").evaluate(
            "el => parseFloat(el.style.getPropertyValue('--guess-position'))"
        )
        assert abs(marker_position - 58 / 60 * 100) < 0.001
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), device
        page.screenshot(path=str(PREVIEWS / f"chart-3-personal-{device}.png"))

        page.locator("#guess-reset").click()
        assert not page.locator("#guess-result").is_visible()
        assert page.locator("#guess-value").inner_text() == "25"
        assert page.locator("#guess-grid .is-guessed").count() == 25
        assert not page.locator("#guess-range").is_disabled()
        assert page.locator("#income-guess-note").is_hidden()
        assert page.locator("#income-guess-marker").is_hidden()
        assert page.locator("#income-axis span").all_inner_texts() == ["0", "10", "20", "30", "40%"]

        page.locator("#guess-range").evaluate(
            "el => { el.value = '100'; el.dispatchEvent(new Event('input', {bubbles: true})); }"
        )
        page.locator("#guess-submit").click()
        assert page.locator("#income-axis span").all_inner_texts() == ["0", "25", "50", "75", "100%"]
        assert page.locator("#income-guess-value").inner_text() == "100%"
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), device
        page.locator("#guess-reset").click()

        for index in range(5):
            page.locator(f".chapter[data-viz='{index}']").evaluate(
                "el => el.scrollIntoView({block: 'center', behavior: 'instant'})"
            )
            page.wait_for_timeout(120)
            assert page.locator(f".viz[data-viz='{index}']").is_visible(), (device, index)
            assert page.locator("#stage-counter").inner_text() == f"{index + 1} trong 5"
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), (device, index)
            page.screenshot(path=str(PREVIEWS / f"chart-{index + 1}-{device}.png"))

        page.locator("#theo-nghe").evaluate(
            "el => el.scrollIntoView({block: 'center', behavior: 'instant'})"
        )
        page.wait_for_timeout(120)
        assert page.locator(".occupation-row").count() == 6
        assert page.locator("#theo-nghe").get_attribute("class").find("is-visible") >= 0
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), device
        page.screenshot(path=str(PREVIEWS / f"occupations-{device}.png"))

        page.locator("#hanh-dong").evaluate(
            "el => el.scrollIntoView({block: 'center', behavior: 'instant'})"
        )
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), device
        page.screenshot(path=str(PREVIEWS / f"takeaway-{device}.png"))
        page.locator("#nguon").screenshot(path=str(PREVIEWS / f"footer-{device}.png"))

        page.locator("#gioi").evaluate(
            "el => el.scrollIntoView({block: 'center', behavior: 'instant'})"
        )
        page.get_by_role("button", name="Nước thu nhập cao").click()
        assert page.locator("#female-value").inner_text() == "9,6%"
        assert page.locator("#male-value").inner_text() == "3,5%"
        assert page.get_by_role("button", name="Nước thu nhập cao").get_attribute("aria-pressed") == "true"
        page.goto((ROOT / "case-study.html").as_uri())
        page.locator("#profile-chart .profile-row").first.wait_for()
        assert page.locator("#profile-chart .profile-row").count() == 6
        assert page.locator("#count-all").inner_text() == "427"
        assert page.locator("#count-exposed").inner_text() == "112"
        assert page.locator("#qa-count").inner_text() == "426/427"
        assert page.locator("#qa-code").inner_text() == "7126"
        assert page.locator("#case-gap-value").inner_text() == "23"
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), (device, "case study")
        page.screenshot(path=str(PREVIEWS / f"case-study-{device}.png"), full_page=True)
        assert not errors, errors
        print(f"{device}: story, data case study, layout, and JavaScript OK")
        page.close()
    browser.close()
