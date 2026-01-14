"""
Frontend tests using Playwright.

These tests validate:
- index.html loads without JavaScript console errors
- Map container exists and has non-zero dimensions
- Correct number of markers rendered
- Clicking a marker opens a popup with expected fields
- Methodology page link navigates correctly
- Legend element is visible
- Page is responsive (375px and 1200px widths)
"""

import json
from pathlib import Path

import pytest

# Try to import playwright, skip tests if not available
try:
    from playwright.sync_api import sync_playwright, Page, Browser
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False


pytestmark = pytest.mark.skipif(not HAS_PLAYWRIGHT, reason="Playwright not installed")


@pytest.fixture(scope="module")
def browser():
    """Create a browser instance for the test module."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture
def page(browser: "Browser", project_root: Path) -> "Page":
    """Create a new page and navigate to index.html."""
    context = browser.new_context()
    page = context.new_page()

    # Serve from file:// protocol
    index_path = project_root / "index.html"
    page.goto(f"file://{index_path}")

    yield page
    context.close()


@pytest.fixture
def cities_count(project_root: Path) -> int:
    """Get the expected number of city markers."""
    with open(project_root / "data" / "cities_final.json") as f:
        data = json.load(f)
    return len(data["cities"])


class TestPageLoad:
    """Tests for page loading."""

    def test_page_loads_successfully(self, page: "Page"):
        """Verify page loads without errors."""
        # Check page title
        assert "Poutine Index" in page.title()

    def test_no_console_errors(self, page: "Page"):
        """Verify no JavaScript console errors on page load."""
        errors = []

        def handle_console(msg):
            if msg.type == "error":
                errors.append(msg.text)

        page.on("console", handle_console)

        # Reload and wait for network idle
        page.reload()
        page.wait_for_load_state("networkidle")

        # Give some time for any async errors
        page.wait_for_timeout(1000)

        assert not errors, f"Console errors found: {errors}"


class TestMapContainer:
    """Tests for map container."""

    def test_map_container_exists(self, page: "Page"):
        """Verify map container element exists."""
        map_element = page.locator("#map")
        assert map_element.count() == 1, "Map container #map not found"

    def test_map_has_dimensions(self, page: "Page"):
        """Verify map container has non-zero dimensions."""
        page.wait_for_selector("#map")
        page.wait_for_timeout(1000)  # Wait for Leaflet to initialize

        box = page.locator("#map").bounding_box()
        assert box is not None, "Could not get map bounding box"
        assert box["width"] > 0, f"Map width is 0 (got {box['width']})"
        assert box["height"] > 0, f"Map height is 0 (got {box['height']})"


class TestMapMarkers:
    """Tests for map markers."""

    def test_markers_rendered(self, page: "Page", cities_count: int):
        """Verify correct number of markers are rendered."""
        page.wait_for_selector("#map")
        page.wait_for_timeout(2000)  # Wait for data load and marker rendering

        # Leaflet circle markers have class 'leaflet-interactive'
        markers = page.locator(".leaflet-interactive")
        marker_count = markers.count()

        assert marker_count == cities_count, (
            f"Expected {cities_count} markers, found {marker_count}"
        )

    def test_marker_click_opens_popup(self, page: "Page"):
        """Verify clicking a marker opens a popup."""
        page.wait_for_selector("#map")
        page.wait_for_timeout(2000)

        # Click the first marker
        markers = page.locator(".leaflet-interactive")
        if markers.count() > 0:
            markers.first.click()
            page.wait_for_timeout(500)

            # Check for popup
            popup = page.locator(".leaflet-popup-content")
            assert popup.count() > 0, "Popup did not open on marker click"

    def test_popup_has_expected_fields(self, page: "Page"):
        """Verify popup contains expected data fields."""
        page.wait_for_selector("#map")
        page.wait_for_timeout(2000)

        markers = page.locator(".leaflet-interactive")
        if markers.count() == 0:
            pytest.skip("No markers to test")

        markers.first.click()
        page.wait_for_timeout(500)

        popup_content = page.locator(".leaflet-popup-content").inner_text()

        # Check for expected content patterns
        assert "$" in popup_content, "No price information in popup"
        assert "min" in popup_content.lower(), "No affordability info in popup"


class TestNavigation:
    """Tests for navigation elements."""

    def test_methodology_link_works(self, page: "Page", project_root: Path):
        """Verify methodology page link navigates correctly."""
        # Find and click methodology link
        methodology_link = page.locator('a[href="methodology.html"]')
        assert methodology_link.count() > 0, "Methodology link not found"

        methodology_link.first.click()
        page.wait_for_load_state("domcontentloaded")

        # Verify we're on the methodology page
        assert "Methodology" in page.title() or "methodology" in page.url.lower()


class TestLegend:
    """Tests for legend element."""

    def test_legend_visible(self, page: "Page"):
        """Verify legend element is visible."""
        page.wait_for_selector("#map")
        page.wait_for_timeout(1000)

        legend = page.locator(".leaflet-legend")
        if legend.count() == 0:
            # Try alternative legend selector
            legend = page.locator(".legend")

        assert legend.count() > 0, "Legend not found"
        assert legend.first.is_visible(), "Legend is not visible"


class TestResponsiveDesign:
    """Tests for responsive design."""

    def test_mobile_viewport(self, browser: "Browser", project_root: Path):
        """Verify page works at mobile viewport (375px)."""
        context = browser.new_context(viewport={"width": 375, "height": 667})
        page = context.new_page()

        index_path = project_root / "index.html"
        page.goto(f"file://{index_path}")
        page.wait_for_load_state("domcontentloaded")

        # Map should still be visible
        map_element = page.locator("#map")
        assert map_element.is_visible(), "Map not visible at mobile viewport"

        # Check map has reasonable dimensions
        box = map_element.bounding_box()
        assert box is not None
        assert box["width"] > 300, f"Map too narrow at mobile: {box['width']}px"
        assert box["height"] > 200, f"Map too short at mobile: {box['height']}px"

        context.close()

    def test_desktop_viewport(self, browser: "Browser", project_root: Path):
        """Verify page works at desktop viewport (1200px)."""
        context = browser.new_context(viewport={"width": 1200, "height": 800})
        page = context.new_page()

        index_path = project_root / "index.html"
        page.goto(f"file://{index_path}")
        page.wait_for_load_state("domcontentloaded")

        # Map should be visible
        map_element = page.locator("#map")
        assert map_element.is_visible(), "Map not visible at desktop viewport"

        # Check map uses available space
        box = map_element.bounding_box()
        assert box is not None
        assert box["width"] > 800, f"Map not using available width: {box['width']}px"

        context.close()


class TestAccessibility:
    """Basic accessibility tests."""

    def test_page_has_main_landmark(self, page: "Page"):
        """Verify page has a main landmark."""
        main = page.locator("main")
        assert main.count() > 0, "No <main> element found"

    def test_page_has_nav_landmark(self, page: "Page"):
        """Verify page has a nav landmark."""
        nav = page.locator("nav")
        assert nav.count() > 0, "No <nav> element found"

    def test_images_have_alt_text(self, page: "Page"):
        """Verify images have alt attributes."""
        images = page.locator("img")
        for i in range(images.count()):
            img = images.nth(i)
            alt = img.get_attribute("alt")
            assert alt is not None, f"Image missing alt attribute: {img.get_attribute('src')}"
