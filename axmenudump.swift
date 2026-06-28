// axmenudump.swift — dump every running app's menu-bar keyboard shortcuts via the Accessibility API.
// Build:  swiftc axmenudump.swift -o axmenudump
// Run:    ./axmenudump   (the controlling app must have Accessibility permission)
// Output: JSON array on stdout. Exit code 2 = Accessibility not granted.
import Cocoa
import ApplicationServices

func axValue(_ element: AXUIElement, _ attr: String) -> CFTypeRef? {
    var value: CFTypeRef?
    let err = AXUIElementCopyAttributeValue(element, attr as CFString, &value)
    return err == .success ? value : nil
}

func axChildren(_ element: AXUIElement) -> [AXUIElement] {
    guard let v = axValue(element, kAXChildrenAttribute as String) else { return [] }
    return (v as? [AXUIElement]) ?? []
}

struct Entry: Codable {
    let app: String
    let bundle: String
    let path: String
    let title: String
    let cmdChar: String?
    let cmdModifiers: Int
    let cmdGlyph: Int
    let cmdVirtualKey: Int
}

var results: [Entry] = []

func traverse(_ menu: AXUIElement, app: String, bundle: String, path: [String], depth: Int) {
    if depth > 14 { return }
    for item in axChildren(menu) {
        let title = (axValue(item, kAXTitleAttribute as String) as? String) ?? ""
        let cmdChar = axValue(item, "AXMenuItemCmdChar") as? String
        let cmdMods = (axValue(item, "AXMenuItemCmdModifiers") as? Int) ?? -1
        let cmdGlyph = (axValue(item, "AXMenuItemCmdGlyph") as? Int) ?? -1
        let cmdVKey = (axValue(item, "AXMenuItemCmdVirtualKey") as? Int) ?? -1
        let hasChar = (cmdChar != nil && !cmdChar!.isEmpty)
        let newPath = title.isEmpty ? path : path + [title]
        if (hasChar || cmdGlyph >= 0 || cmdVKey >= 0) && cmdMods >= 0 {
            results.append(Entry(app: app, bundle: bundle, path: newPath.joined(separator: " ▸ "),
                                 title: title, cmdChar: cmdChar, cmdModifiers: cmdMods,
                                 cmdGlyph: cmdGlyph, cmdVirtualKey: cmdVKey))
        }
        for sub in axChildren(item) {  // a submenu shows up as a child AXMenu
            traverse(sub, app: app, bundle: bundle, path: newPath, depth: depth + 1)
        }
    }
}

guard AXIsProcessTrusted() else {
    FileHandle.standardError.write("NOT_TRUSTED\n".data(using: .utf8)!)
    print("[]")
    exit(2)
}

for app in NSWorkspace.shared.runningApplications where app.activationPolicy == .regular {
    let name = app.localizedName ?? "Unknown"
    let bundle = app.bundleIdentifier ?? ""
    let axApp = AXUIElementCreateApplication(app.processIdentifier)
    AXUIElementSetMessagingTimeout(axApp, 2.0)  // avoid hangs on slow/dynamic menus
    guard let mbRef = axValue(axApp, kAXMenuBarAttribute as String) else { continue }
    let menuBar = mbRef as! AXUIElement
    for barItem in axChildren(menuBar) {
        let barTitle = (axValue(barItem, kAXTitleAttribute as String) as? String) ?? ""
        for menu in axChildren(barItem) {
            traverse(menu, app: name, bundle: bundle, path: [barTitle], depth: 0)
        }
    }
}

let enc = JSONEncoder()
enc.outputFormatting = [.prettyPrinted, .sortedKeys]
print(String(data: try enc.encode(results), encoding: .utf8)!)
