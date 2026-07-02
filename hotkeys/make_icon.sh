#!/bin/zsh
# make_icon.sh — generate AppIcon.icns (a purple rounded square with ⌘) for SV Hotkeys.
# Run once; the .icns is committed and build.sh copies it into the app bundle.
set -e
cd "${0:A:h}"
cat > /tmp/mkicon.swift <<'SWIFT'
import AppKit
let S: CGFloat = 1024
let img = NSImage(size: NSSize(width: S, height: S))
img.lockFocus()
let inset = S * 0.08
let rect = NSRect(x: inset, y: inset, width: S - 2*inset, height: S - 2*inset)
let path = NSBezierPath(roundedRect: rect, xRadius: S*0.22, yRadius: S*0.22)
NSGradient(colors: [NSColor(red:0.58,green:0.40,blue:0.98,alpha:1),
                    NSColor(red:0.35,green:0.18,blue:0.70,alpha:1)])?.draw(in: path, angle: -90)
let g = "⌘" as NSString
let a: [NSAttributedString.Key: Any] = [.font: NSFont.systemFont(ofSize: S*0.52, weight: .semibold),
                                        .foregroundColor: NSColor.white]
let sz = g.size(withAttributes: a)
g.draw(at: NSPoint(x: (S - sz.width)/2, y: (S - sz.height)/2), withAttributes: a)
img.unlockFocus()
if let tiff = img.tiffRepresentation, let rep = NSBitmapImageRep(data: tiff),
   let png = rep.representation(using: .png, properties: [:]) {
    try? png.write(to: URL(fileURLWithPath: "/tmp/svicon-1024.png"))
}
SWIFT
swiftc /tmp/mkicon.swift -o /tmp/mkicon && /tmp/mkicon
SET=/tmp/AppIcon.iconset; rm -rf "$SET"; mkdir -p "$SET"
for s in 16 32 128 256 512; do
  sips -z $s $s      /tmp/svicon-1024.png --out "$SET/icon_${s}x${s}.png"    >/dev/null
  sips -z $((s*2)) $((s*2)) /tmp/svicon-1024.png --out "$SET/icon_${s}x${s}@2x.png" >/dev/null
done
iconutil -c icns "$SET" -o AppIcon.icns
echo "✓ AppIcon.icns ($(du -h AppIcon.icns | cut -f1))"
