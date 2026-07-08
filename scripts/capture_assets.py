import asyncio
import os
import subprocess
import time
from playwright.async_api import async_playwright

async def capture():
    # Start the local server
    print("Starting local server on port 8787...")
    server = subprocess.Popen(["python3", "-m", "http.server", "8787"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)  # Give the server a moment to start
    
    os.makedirs("assets/screenshots", exist_ok=True)
    
    try:
        async with async_playwright() as p:
            # Launch browser in high DPI mode for crisp screenshots
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                device_scale_factor=2 # Retina display quality
            )
            page = await context.new_page()
            
            print("Navigating to Shortcut Viewer...")
            await page.goto("http://127.0.0.1:8787/viewer.html")
            await page.wait_for_load_state("networkidle")
            
            # Wait for the UI to be fully rendered
            await page.wait_for_timeout(1000)
            
            print("Capturing Main Dashboard...")
            await page.screenshot(path="assets/screenshots/main_dashboard.png", full_page=True)
            
            print("Capturing App Selector Dropdown...")
            dropdown = await page.query_selector(".ctx-select")
            if dropdown:
                await dropdown.click()
                await page.wait_for_timeout(500)
                await page.screenshot(path="assets/screenshots/app_selector.png")
                # Close dropdown
                await page.keyboard.press("Escape")
                await page.wait_for_timeout(500)
            
            print("Capturing Diagnostics Modal...")
            diag_btn = await page.query_selector(".icon-btn")
            if diag_btn:
                await diag_btn.click()
                await page.wait_for_timeout(500)
                await page.screenshot(path="assets/screenshots/diagnostics_modal.png")
                await page.keyboard.press("Escape")
            
            await browser.close()
            print("Screenshots captured successfully in assets/screenshots/")
            
    finally:
        server.terminate()
        server.wait()

if __name__ == "__main__":
    asyncio.run(capture())
