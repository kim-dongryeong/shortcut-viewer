#!/usr/bin/env python3
import subprocess
import os
import sys

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SVG_PATH = os.path.join(PROJ, "assets", "icon.svg")

def rasterize_svg(svg_path, out_png_path, size):
    try:
        # qlmanage creates a file named "icon.svg.png" in the output directory
        tmp_dir = os.path.dirname(out_png_path)
        cmd = [
            "qlmanage",
            "-t",
            "-s", str(size),
            "-o", tmp_dir,
            svg_path
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Move the generated file to the desired output path
        gen_file = os.path.join(tmp_dir, os.path.basename(svg_path) + ".png")
        if os.path.exists(gen_file):
            os.rename(gen_file, out_png_path)
            print(f"✓ Rendered: {os.path.relpath(out_png_path, PROJ)} ({size}x{size})")
        else:
            print(f"Error: qlmanage did not generate expected file {gen_file}", file=sys.stderr)
    except subprocess.CalledProcessError as e:
        print(f"Error rendering {size}x{size} PNG: {e}", file=sys.stderr)
        sys.exit(1)

def main():
    if not os.path.exists(SVG_PATH):
        print(f"Error: Source SVG icon not found at {SVG_PATH}", file=sys.stderr)
        sys.exit(1)
        
    os.makedirs(os.path.join(PROJ, "assets"), exist_ok=True)
    
    print("Rasterizing SVG icon using macOS QuickLook...")
    rasterize_svg(SVG_PATH, os.path.join(PROJ, "assets", "icon-192.png"), 192)
    rasterize_svg(SVG_PATH, os.path.join(PROJ, "assets", "icon-256.png"), 256)
    print("Done generating raster icons.")

if __name__ == "__main__":
    main()
