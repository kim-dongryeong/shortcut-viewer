#!/usr/bin/env python3
import subprocess
import os
import sys

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SVG_PATH = os.path.join(PROJ, "assets", "icon.svg")

def rasterize_svg(svg_path, out_png_path, size):
    chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    if not os.path.exists(chrome_path):
        print(f"Error: Google Chrome not found at {chrome_path}", file=sys.stderr)
        sys.exit(1)
        
    tmp_html = out_png_path + ".html"
    with open(tmp_html, "w", encoding="utf-8") as f:
        f.write(f"""<!DOCTYPE html>
<html>
<head>
<style>
  html, body {{
    margin: 0;
    padding: 0;
    width: 100%;
    height: 100%;
    overflow: hidden;
    background: transparent;
  }}
  img {{
    width: 100%;
    height: 100%;
    display: block;
    object-fit: contain;
  }}
</style>
</head>
<body>
  <img src="file://{os.path.abspath(svg_path)}">
</body>
</html>""")

    try:
        cmd = [
            chrome_path,
            "--headless=new",
            "--disable-gpu",
            "--default-background-color=00000000",
            "--hide-scrollbars",
            f"--window-size={size},{size}",
            f"--screenshot={os.path.abspath(out_png_path)}",
            f"file://{os.path.abspath(tmp_html)}"
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"✓ Rendered: {os.path.relpath(out_png_path, PROJ)} ({size}x{size})")
    except subprocess.CalledProcessError as e:
        print(f"Error rendering {size}x{size} PNG: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        if os.path.exists(tmp_html):
            os.remove(tmp_html)

def main():
    if not os.path.exists(SVG_PATH):
        print(f"Error: Source SVG icon not found at {SVG_PATH}", file=sys.stderr)
        sys.exit(1)
        
    os.makedirs(os.path.join(PROJ, "assets"), exist_ok=True)
    
    print("Rasterizing SVG icon using Google Chrome...")
    rasterize_svg(SVG_PATH, os.path.join(PROJ, "assets", "icon-192.png"), 192)
    rasterize_svg(SVG_PATH, os.path.join(PROJ, "assets", "icon-256.png"), 256)
    print("Done generating raster icons.")

if __name__ == "__main__":
    main()
