// svhotkeys.swift — SV Hotkeys: Shortcut Viewer's OWN global-hotkey app (self-contained,
// no third-party tool needed). A menu-bar app that lets you set global keyboard shortcuts
// that run an action (open app/URL/folder/file, run shell, AppleScript, paste text) from
// anywhere. It has its own visual editor (record a combo, pick an app, choose an action),
// reads/writes ~/.config/shortcut-viewer/hotkeys.json, and the Shortcut Viewer web UI can
// also produce that file with conflict-free-combo detection.
//
// Hotkey mechanism (proven in ~/dev/maverything):
//   • Carbon RegisterEventHotKey — DEFAULT, needs NO permission. ⌘/⌥/⌃ combos.
//   • CGEventTap — opt-in per hotkey ("anyCombo"), needs Accessibility, grabs & consumes
//     combos other apps also claim (⇧Space, plain F-keys…).
//
// Build (universal):  ./build.sh          Self-test (no GUI):  ./svhotkeys --list
import AppKit
import SwiftUI
import Carbon.HIToolbox
import ApplicationServices

// ══════════════════════ key-name ⇄ Carbon virtual keycode ══════════════════════
let KEYCODE: [String: Int] = [
    "A":kVK_ANSI_A,"B":kVK_ANSI_B,"C":kVK_ANSI_C,"D":kVK_ANSI_D,"E":kVK_ANSI_E,"F":kVK_ANSI_F,
    "G":kVK_ANSI_G,"H":kVK_ANSI_H,"I":kVK_ANSI_I,"J":kVK_ANSI_J,"K":kVK_ANSI_K,"L":kVK_ANSI_L,
    "M":kVK_ANSI_M,"N":kVK_ANSI_N,"O":kVK_ANSI_O,"P":kVK_ANSI_P,"Q":kVK_ANSI_Q,"R":kVK_ANSI_R,
    "S":kVK_ANSI_S,"T":kVK_ANSI_T,"U":kVK_ANSI_U,"V":kVK_ANSI_V,"W":kVK_ANSI_W,"X":kVK_ANSI_X,
    "Y":kVK_ANSI_Y,"Z":kVK_ANSI_Z,
    "0":kVK_ANSI_0,"1":kVK_ANSI_1,"2":kVK_ANSI_2,"3":kVK_ANSI_3,"4":kVK_ANSI_4,
    "5":kVK_ANSI_5,"6":kVK_ANSI_6,"7":kVK_ANSI_7,"8":kVK_ANSI_8,"9":kVK_ANSI_9,
    "-":kVK_ANSI_Minus,"=":kVK_ANSI_Equal,"[":kVK_ANSI_LeftBracket,"]":kVK_ANSI_RightBracket,
    "\\":kVK_ANSI_Backslash,";":kVK_ANSI_Semicolon,"'":kVK_ANSI_Quote,",":kVK_ANSI_Comma,
    ".":kVK_ANSI_Period,"/":kVK_ANSI_Slash,"`":kVK_ANSI_Grave,
    "Space":kVK_Space,"Return":kVK_Return,"Tab":kVK_Tab,"Escape":kVK_Escape,
    "Delete":kVK_Delete,"ForwardDelete":kVK_ForwardDelete,
    "Left":kVK_LeftArrow,"Right":kVK_RightArrow,"Up":kVK_UpArrow,"Down":kVK_DownArrow,
    "Home":kVK_Home,"End":kVK_End,"PageUp":kVK_PageUp,"PageDown":kVK_PageDown,
    "F1":kVK_F1,"F2":kVK_F2,"F3":kVK_F3,"F4":kVK_F4,"F5":kVK_F5,"F6":kVK_F6,"F7":kVK_F7,
    "F8":kVK_F8,"F9":kVK_F9,"F10":kVK_F10,"F11":kVK_F11,"F12":kVK_F12,"F13":kVK_F13,
    "F14":kVK_F14,"F15":kVK_F15,"F16":kVK_F16,"F17":kVK_F17,"F18":kVK_F18,"F19":kVK_F19,"F20":kVK_F20,
]
let NAMEFOR: [Int: String] = { var m = [Int: String](); for (k, v) in KEYCODE { m[v] = k }; return m }()
let MODSYM: [String: String] = ["cmd":"⌘","opt":"⌥","ctrl":"⌃","shift":"⇧"]
let MOD_ORDER = ["ctrl","opt","shift","cmd"]

func carbonMods(_ mods: [String]) -> UInt32 {
    var m: UInt32 = 0
    if mods.contains("cmd")   { m |= UInt32(cmdKey) }
    if mods.contains("opt")   { m |= UInt32(optionKey) }
    if mods.contains("ctrl")  { m |= UInt32(controlKey) }
    if mods.contains("shift") { m |= UInt32(shiftKey) }
    return m
}
func cocoaFlags(_ mods: [String]) -> NSEvent.ModifierFlags {
    var f: NSEvent.ModifierFlags = []
    if mods.contains("cmd")   { f.insert(.command) }
    if mods.contains("opt")   { f.insert(.option) }
    if mods.contains("ctrl")  { f.insert(.control) }
    if mods.contains("shift") { f.insert(.shift) }
    return f
}
func modsFrom(_ f: NSEvent.ModifierFlags) -> [String] {
    var m = [String]()
    if f.contains(.control) { m.append("ctrl") }
    if f.contains(.option)  { m.append("opt") }
    if f.contains(.shift)   { m.append("shift") }
    if f.contains(.command) { m.append("cmd") }
    return m
}
func comboLabel(_ mods: [String], _ key: String) -> String {
    (MOD_ORDER.filter { mods.contains($0) }.map { MODSYM[$0]! }.joined()) + key
}

// ══════════════════════ config model (read + write) ══════════════════════
struct HKAction: Codable { var type: String; var value: String }
struct Hotkey: Codable, Identifiable {
    var id: String
    var title: String
    var mods: [String]
    var key: String
    var action: HKAction
    var enabled: Bool
    var anyCombo: Bool

    init(id: String? = nil, title: String = "", mods: [String] = [], key: String = "",
         action: HKAction = HKAction(type: "open_app", value: ""), enabled: Bool = true, anyCombo: Bool = false) {
        self.id = id ?? "h" + String(UInt32.random(in: 0..<0xFFFFFF), radix: 16)
        self.title = title; self.mods = mods; self.key = key
        self.action = action; self.enabled = enabled; self.anyCombo = anyCombo
    }
    enum CK: String, CodingKey { case id, title, mods, key, action, enabled, anyCombo }
    init(from d: Decoder) throws {   // tolerant: missing fields get defaults
        let c = try d.container(keyedBy: CK.self)
        id = (try? c.decode(String.self, forKey: .id)) ?? ("h" + String(UInt32.random(in: 0..<0xFFFFFF), radix: 16))
        title = (try? c.decode(String.self, forKey: .title)) ?? ""
        mods = (try? c.decode([String].self, forKey: .mods)) ?? []
        key = (try? c.decode(String.self, forKey: .key)) ?? ""
        action = (try? c.decode(HKAction.self, forKey: .action)) ?? HKAction(type: "open_app", value: "")
        enabled = (try? c.decode(Bool.self, forKey: .enabled)) ?? true
        anyCombo = (try? c.decode(Bool.self, forKey: .anyCombo)) ?? false
    }
}
struct ConfigFile: Codable { var version: Int; var hotkeys: [Hotkey] }

let CONFIG_PATH = ("~/.config/shortcut-viewer/hotkeys.json" as NSString).expandingTildeInPath

final class Store: ObservableObject {
    static let shared = Store()
    @Published var hotkeys: [Hotkey] = []
    var onChange: () -> Void = {}   // AppDelegate hooks re-registration here

    func load() {
        guard let data = FileManager.default.contents(atPath: CONFIG_PATH) else { hotkeys = []; return }
        do { hotkeys = try JSONDecoder().decode(ConfigFile.self, from: data).hotkeys }
        catch { NSLog("hotkeys.json parse failed: \(error)"); hotkeys = [] }
    }
    func saveToDisk() {
        let dir = (CONFIG_PATH as NSString).deletingLastPathComponent
        try? FileManager.default.createDirectory(atPath: dir, withIntermediateDirectories: true)
        let enc = JSONEncoder(); enc.outputFormatting = [.prettyPrinted, .withoutEscapingSlashes]
        if let data = try? enc.encode(ConfigFile(version: 1, hotkeys: hotkeys)) {
            try? data.write(to: URL(fileURLWithPath: CONFIG_PATH), options: .atomic)
        }
    }
    func commit() { saveToDisk(); onChange() }   // persist + re-register live
}

// Conflict awareness: read the Shortcut Viewer's scanned dataset (shortcuts.json) so the editor
// can warn "this combo is already used by …" and suggest free keys — the same superpower the web
// viewer has, brought into the native app.
func comboKey(_ mods: [String], _ key: String) -> String { mods.sorted().joined(separator: ",") + "|" + key }
struct SVEntry: Decodable { let mods: [String]; let key: String; let action: String?; let scope: String? }
final class KnownShortcuts {
    static let shared = KnownShortcuts()
    private(set) var byCombo: [String: [(action: String, scope: String)]] = [:]
    private var loaded = false
    func load() {
        guard !loaded else { return }; loaded = true
        let p = ("~/dev/shortcut-viewer/shortcuts.json" as NSString).expandingTildeInPath
        guard let data = FileManager.default.contents(atPath: p) else { return }
        struct Doc: Decodable { let entries: [SVEntry] }
        guard let doc = try? JSONDecoder().decode(Doc.self, from: data) else { return }
        for e in doc.entries {
            byCombo[comboKey(e.mods, e.key), default: []].append((e.action ?? "", e.scope ?? "global"))
        }
    }
    func usersOf(_ mods: [String], _ key: String) -> [(action: String, scope: String)] { byCombo[comboKey(mods, key)] ?? [] }
    /// A free key in the given modifier layer, preferring easy-to-reach ones.
    func freeKey(mods: [String], avoiding taken: Set<String>) -> String? {
        let pref = ["J","K","L","U","I","O","H","N","Y","P","B","G","R","E",";","M"]
        let used = { (k: String) -> Bool in taken.contains(k) || !self.usersOf(mods, k).isEmpty }
        return pref.first { !used($0) } ?? "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789".map { String($0) }.first { !used($0) }
    }
}

// ══════════════════════ action execution ══════════════════════
enum Runner {
    static func run(_ a: HKAction) {
        switch a.type {
        case "open_app":
            if a.value.hasPrefix("/") { NSWorkspace.shared.open(URL(fileURLWithPath: a.value)) }
            else if a.value.contains(".") && !a.value.contains(" "),
                    let url = NSWorkspace.shared.urlForApplication(withBundleIdentifier: a.value) {
                NSWorkspace.shared.openApplication(at: url, configuration: .init())
            } else { shell("open -a \(q(a.value))") }
        case "open_url":  if let u = URL(string: a.value) { NSWorkspace.shared.open(u) }
        case "open_file", "open_folder":
            NSWorkspace.shared.open(URL(fileURLWithPath: (a.value as NSString).expandingTildeInPath))
        case "run_shell":   shell(a.value)
        case "applescript": shell("osascript -e \(q(a.value))")
        case "paste_text":  paste(a.value)
        case "show_viewer":
            let p = (a.value.isEmpty ? "~/dev/shortcut-viewer/viewer.html" : a.value) as NSString
            NSWorkspace.shared.open(URL(fileURLWithPath: p.expandingTildeInPath))
        default: NSLog("unknown action type: \(a.type)")
        }
    }
    static func q(_ s: String) -> String { "'" + s.replacingOccurrences(of: "'", with: "'\\''") + "'" }
    static func shell(_ cmd: String) {
        let p = Process(); p.launchPath = "/bin/zsh"; p.arguments = ["-lc", cmd]
        do { try p.run() } catch { NSLog("shell failed: \(error)") }
    }
    static func paste(_ text: String) {
        let pb = NSPasteboard.general; pb.clearContents(); pb.setString(text, forType: .string)
        let src = CGEventSource(stateID: .combinedSessionState)
        let v = CGKeyCode(kVK_ANSI_V)
        let down = CGEvent(keyboardEventSource: src, virtualKey: v, keyDown: true)
        let up   = CGEvent(keyboardEventSource: src, virtualKey: v, keyDown: false)
        down?.flags = .maskCommand; up?.flags = .maskCommand
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.05) {
            down?.post(tap: .cgAnnotatedSessionEventTap); up?.post(tap: .cgAnnotatedSessionEventTap)
        }
    }
}

// ══════════════════════ Carbon multi-hotkey (no Accessibility) ══════════════════════
final class HotKeyCenter {
    static let shared = HotKeyCenter()
    private var refs: [EventHotKeyRef?] = []
    private var actions: [UInt32: () -> Void] = [:]
    private var nextID: UInt32 = 1
    private var installed = false
    private func installHandler() {
        guard !installed else { return }; installed = true
        var spec = EventTypeSpec(eventClass: OSType(kEventClassKeyboard), eventKind: UInt32(kEventHotKeyPressed))
        InstallEventHandler(GetApplicationEventTarget(), { _, evt, _ -> OSStatus in
            var hkid = EventHotKeyID()
            GetEventParameter(evt, EventParamName(kEventParamDirectObject), EventParamType(typeEventHotKeyID),
                              nil, MemoryLayout<EventHotKeyID>.size, nil, &hkid)
            HotKeyCenter.shared.actions[hkid.id]?()
            return noErr
        }, 1, &spec, nil, nil)
    }
    @discardableResult
    func register(keyCode: Int, mods: UInt32, action: @escaping () -> Void) -> Bool {
        installHandler()
        var ref: EventHotKeyRef?
        let hkid = EventHotKeyID(signature: OSType(0x5356_4859), id: nextID)   // 'SVHY'
        let st = RegisterEventHotKey(UInt32(keyCode), mods, hkid, GetApplicationEventTarget(), 0, &ref)
        guard st == noErr, let ref else { return false }
        refs.append(ref); actions[nextID] = action; nextID += 1; return true
    }
    func unregisterAll() { for r in refs { if let r { UnregisterEventHotKey(r) } }; refs = []; actions = [:]; nextID = 1 }
}

// ══════════════════════ CGEventTap multi-hotkey (any combo; needs Accessibility) ══════════════════════
final class EventTapCenter {
    static let shared = EventTapCenter()
    private var tap: CFMachPort?
    private var source: CFRunLoopSource?
    private var binds: [(kc: CGKeyCode, mods: NSEvent.ModifierFlags, action: () -> Void)] = []
    func setBinds(_ b: [(CGKeyCode, NSEvent.ModifierFlags, () -> Void)]) {
        binds = b.map { (kc: $0.0, mods: $0.1.intersection([.command,.option,.control,.shift]), action: $0.2) }
    }
    @discardableResult
    func enable() -> Bool {
        if tap != nil { return true }
        let mask: CGEventMask = (1 << CGEventType.keyDown.rawValue) | (1 << CGEventType.tapDisabledByTimeout.rawValue)
        let info = Unmanaged.passUnretained(self).toOpaque()
        guard let t = CGEvent.tapCreate(tap: .cgSessionEventTap, place: .headInsertEventTap, options: .defaultTap,
              eventsOfInterest: mask, callback: { _, type, event, refcon in
                  guard let refcon else { return Unmanaged.passUnretained(event) }
                  return Unmanaged<EventTapCenter>.fromOpaque(refcon).takeUnretainedValue().handle(type, event)
              }, userInfo: info) else { return false }
        tap = t
        source = CFMachPortCreateRunLoopSource(kCFAllocatorDefault, t, 0)
        CFRunLoopAddSource(CFRunLoopGetMain(), source, .commonModes)
        CGEvent.tapEnable(tap: t, enable: true)
        return true
    }
    private func handle(_ type: CGEventType, _ event: CGEvent) -> Unmanaged<CGEvent>? {
        if type == .tapDisabledByTimeout || type == .tapDisabledByUserInput {
            if let tap { CGEvent.tapEnable(tap: tap, enable: true) }; return Unmanaged.passUnretained(event)
        }
        if type == .keyDown, event.getIntegerValueField(.keyboardEventAutorepeat) == 0 {
            let kc = CGKeyCode(event.getIntegerValueField(.keyboardEventKeycode))
            var f: NSEvent.ModifierFlags = []
            let cg = event.flags
            if cg.contains(.maskCommand)   { f.insert(.command) }
            if cg.contains(.maskAlternate) { f.insert(.option) }
            if cg.contains(.maskControl)   { f.insert(.control) }
            if cg.contains(.maskShift)     { f.insert(.shift) }
            for b in binds where b.kc == kc && b.mods == f {
                DispatchQueue.main.async { b.action() }; return nil   // consume
            }
        }
        return Unmanaged.passUnretained(event)
    }
    func disable() {
        if let tap { CGEvent.tapEnable(tap: tap, enable: false) }
        if let source { CFRunLoopRemoveSource(CFRunLoopGetMain(), source, .commonModes) }
        tap = nil; source = nil
    }
}

enum Accessibility {
    static var isTrusted: Bool { AXIsProcessTrusted() }
    @discardableResult static func requestTrust() -> Bool {
        AXIsProcessTrustedWithOptions([kAXTrustedCheckOptionPrompt.takeUnretainedValue() as String: true] as CFDictionary)
    }
    static func openSettings() {
        if let u = URL(string: "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility") { NSWorkspace.shared.open(u) }
    }
}

// Global hooks so the recorder can pause hotkeys while you type a new combo.
enum HK {
    static var suspend: () -> Void = {}
    static var resume: () -> Void = {}
}

// ══════════════════════ installed-app list (for the app picker) ══════════════════════
func installedApps() -> [String] {
    var names = Set<String>()
    for dir in ["/Applications", "/System/Applications", ("~/Applications" as NSString).expandingTildeInPath] {
        if let items = try? FileManager.default.contentsOfDirectory(atPath: dir) {
            for it in items where it.hasSuffix(".app") { names.insert(String(it.dropLast(4))) }
        }
    }
    return names.sorted { $0.lowercased() < $1.lowercased() }
}

// ══════════════════════ hotkey recorder (AppKit, hosted in SwiftUI) ══════════════════════
final class RecorderNSView: NSView {
    var display = "클릭 후 조합 입력"
    var onCapture: (([String], String) -> Void)?
    private var recording = false
    override var acceptsFirstResponder: Bool { true }
    override var intrinsicContentSize: NSSize { NSSize(width: 150, height: 26) }
    override func mouseDown(with e: NSEvent) { recording = true; HK.suspend(); window?.makeFirstResponder(self); needsDisplay = true }
    override func resignFirstResponder() -> Bool { if recording { recording = false; HK.resume() }; needsDisplay = true; return true }
    override func keyDown(with e: NSEvent) {
        guard recording else { super.keyDown(with: e); return }
        if e.keyCode == UInt32(kVK_Escape) { recording = false; HK.resume(); window?.makeFirstResponder(nil); needsDisplay = true; return }
        guard let name = NAMEFOR[Int(e.keyCode)] else { NSSound.beep(); return }
        let mods = modsFrom(e.modifierFlags)
        recording = false
        display = comboLabel(mods, name)
        onCapture?(mods, name)
        HK.resume(); window?.makeFirstResponder(nil); needsDisplay = true
    }
    override func draw(_ r: NSRect) {
        let b = bounds.insetBy(dx: 1, dy: 1)
        let path = NSBezierPath(roundedRect: b, xRadius: 6, yRadius: 6)
        (recording ? NSColor.controlAccentColor.withAlphaComponent(0.15) : NSColor.controlBackgroundColor).setFill(); path.fill()
        (recording ? NSColor.controlAccentColor : NSColor.separatorColor).setStroke(); path.lineWidth = recording ? 2 : 1; path.stroke()
        let text = recording ? "조합을 누르세요…" : display
        let attrs: [NSAttributedString.Key: Any] = [.font: NSFont.systemFont(ofSize: 13),
            .foregroundColor: recording ? NSColor.controlAccentColor : NSColor.labelColor]
        let sz = (text as NSString).size(withAttributes: attrs)
        (text as NSString).draw(at: NSPoint(x: (bounds.width - sz.width)/2, y: (bounds.height - sz.height)/2), withAttributes: attrs)
    }
}
struct RecorderField: NSViewRepresentable {
    @Binding var display: String
    var onCapture: ([String], String) -> Void
    func makeNSView(context: Context) -> RecorderNSView { let v = RecorderNSView(); v.display = display; v.onCapture = { m,k in display = comboLabel(m,k); onCapture(m,k) }; return v }
    func updateNSView(_ v: RecorderNSView, context: Context) { if !v.display.isEmpty { v.display = display }; v.needsDisplay = true }
}

// ══════════════════════ SwiftUI editor ══════════════════════
let ACCENT = Color(red: 0.55, green: 0.36, blue: 0.96)
let ACTION_TYPES: [(String, String)] = [
    ("open_app","앱 열기"), ("open_url","웹사이트 열기"), ("open_folder","폴더 열기"),
    ("open_file","파일 열기"), ("run_shell","명령 실행 (zsh)"), ("applescript","AppleScript"),
    ("paste_text","텍스트 붙여넣기"), ("show_viewer","단축키 뷰어 열기")]
func actionLabel(_ t: String) -> String { ACTION_TYPES.first { $0.0 == t }?.1 ?? t }
func actionMeta(_ t: String) -> (icon: String, color: Color) {
    switch t {
    case "open_app":    return ("app.fill", .blue)
    case "open_url":    return ("globe", .teal)
    case "open_folder": return ("folder.fill", .orange)
    case "open_file":   return ("doc.fill", .gray)
    case "run_shell":   return ("terminal.fill", .indigo)
    case "applescript": return ("wand.and.stars", .purple)
    case "paste_text":  return ("doc.on.clipboard.fill", .pink)
    case "show_viewer": return ("keyboard.fill", .green)
    default:            return ("bolt.fill", .secondary)
    }
}

// One shortcut, as a card row.
struct HotkeyCard: View {
    let hk: Hotkey
    var onToggle: (Bool) -> Void
    var onEdit: () -> Void
    var onDelete: () -> Void
    @State private var hover = false
    var body: some View {
        let meta = actionMeta(hk.action.type)
        HStack(spacing: 12) {
            Toggle("", isOn: Binding(get: { hk.enabled }, set: onToggle))
                .labelsHidden().toggleStyle(.switch).controlSize(.small).tint(ACCENT)
            Text(comboLabel(hk.mods, hk.key))
                .font(.system(size: 14, weight: .bold, design: .rounded)).foregroundColor(ACCENT)
                .padding(.horizontal, 10).padding(.vertical, 5)
                .background(Capsule().fill(ACCENT.opacity(0.14)))
                .frame(minWidth: 76)
            ZStack { Circle().fill(meta.color.gradient).frame(width: 30, height: 30)
                     Image(systemName: meta.icon).font(.system(size: 13, weight: .semibold)).foregroundColor(.white) }
            VStack(alignment: .leading, spacing: 2) {
                Text(hk.title.isEmpty ? actionLabel(hk.action.type) : hk.title).fontWeight(.medium)
                Text(hk.action.value.isEmpty ? actionLabel(hk.action.type) : hk.action.value)
                    .font(.caption).foregroundColor(.secondary).lineLimit(1).truncationMode(.middle)
            }
            Spacer(minLength: 4)
            if hover {
                Button(action: onEdit) { Image(systemName: "pencil") }.buttonStyle(.borderless).help("편집")
                Button(action: onDelete) { Image(systemName: "trash") }.buttonStyle(.borderless).foregroundColor(.red).help("삭제")
            }
        }
        .padding(.horizontal, 14).padding(.vertical, 10)
        .background(RoundedRectangle(cornerRadius: 12).fill(Color(nsColor: .controlBackgroundColor)))
        .overlay(RoundedRectangle(cornerRadius: 12).strokeBorder(hover ? ACCENT.opacity(0.5) : Color.primary.opacity(0.08)))
        .shadow(color: .black.opacity(hover ? 0.12 : 0.05), radius: hover ? 5 : 2, y: 1)
        .opacity(hk.enabled ? 1 : 0.5)
        .animation(.easeOut(duration: 0.12), value: hover)
        .onHover { hover = $0 }
    }
}

struct EditorView: View {
    @ObservedObject var store = Store.shared
    @State private var editing: Hotkey? = nil
    @State private var isNew = false
    func newHotkey() { editing = Hotkey(mods: ["opt"]); isNew = true }
    var body: some View {
        VStack(spacing: 0) {
            // header
            HStack(spacing: 12) {
                RoundedRectangle(cornerRadius: 10)
                    .fill(LinearGradient(colors: [ACCENT, ACCENT.opacity(0.65)], startPoint: .topLeading, endPoint: .bottomTrailing))
                    .frame(width: 40, height: 40)
                    .overlay(Image(systemName: "command").font(.system(size: 19, weight: .bold)).foregroundColor(.white))
                    .shadow(color: ACCENT.opacity(0.4), radius: 6, y: 2)
                VStack(alignment: .leading, spacing: 1) {
                    Text("SV Hotkeys").font(.system(size: 17, weight: .bold))
                    Text("어디서나 실행되는 글로벌 단축키").font(.caption).foregroundColor(.secondary)
                }
                Spacer()
                Button(action: newHotkey) { Label("핫키 추가", systemImage: "plus") }
                    .buttonStyle(.borderedProminent).tint(ACCENT).controlSize(.large)
            }.padding(16)
            Divider()
            // content
            if store.hotkeys.isEmpty {
                VStack(spacing: 15) {
                    ZStack { Circle().fill(ACCENT.opacity(0.12)).frame(width: 92, height: 92)
                             Image(systemName: "keyboard").font(.system(size: 40)).foregroundColor(ACCENT) }
                    Text("아직 글로벌 핫키가 없어요").font(.title3).fontWeight(.semibold)
                    Text("‘핫키 추가’를 눌러 첫 단축키를 만들어 보세요.\n예: ⌥F → Finder 열기 · ⌃⌥T → 터미널")
                        .font(.callout).foregroundColor(.secondary).multilineTextAlignment(.center)
                    Button(action: newHotkey) { Label("첫 핫키 만들기", systemImage: "plus") }
                        .buttonStyle(.borderedProminent).tint(ACCENT).controlSize(.large)
                }.frame(maxWidth: .infinity, maxHeight: .infinity).padding(40)
            } else {
                ScrollView {
                    LazyVStack(spacing: 8) {
                        ForEach(store.hotkeys) { hk in
                            HotkeyCard(hk: hk,
                                onToggle: { v in if let i = store.hotkeys.firstIndex(where: { $0.id == hk.id }) { store.hotkeys[i].enabled = v; store.commit() } },
                                onEdit: { editing = hk; isNew = false },
                                onDelete: { store.hotkeys.removeAll { $0.id == hk.id }; store.commit() })
                        }
                    }.padding(16)
                }
            }
            Divider()
            // footer
            HStack(spacing: 6) {
                Image(systemName: Accessibility.isTrusted ? "checkmark.seal.fill" : "lock.open.fill")
                    .foregroundColor(Accessibility.isTrusted ? .green : .secondary).font(.caption)
                Text(Accessibility.isTrusted ? "any-combo 켜짐 (손쉬운 사용)" : "일반 조합(⌘⌥⌃)은 권한 없이 바로 작동")
                    .font(.caption).foregroundColor(.secondary)
                Spacer()
                Text("\(store.hotkeys.filter { $0.enabled }.count) / \(store.hotkeys.count) 활성")
                    .font(.caption.monospacedDigit()).foregroundColor(.secondary)
            }.padding(.horizontal, 16).padding(.vertical, 10)
        }
        .frame(width: 600, height: 520)
        .sheet(item: $editing) { hk in
            EditSheet(hotkey: hk, isNew: isNew) { saved in
                if let idx = store.hotkeys.firstIndex(where: { $0.id == saved.id }) { store.hotkeys[idx] = saved }
                else { store.hotkeys.append(saved) }
                store.commit(); editing = nil
            } onCancel: { editing = nil }
        }
    }
}

struct EditSheet: View {
    @State var hotkey: Hotkey
    let isNew: Bool
    var onSave: (Hotkey) -> Void
    var onCancel: () -> Void
    @State private var comboDisplay = ""
    @State private var apps: [String] = []
    @State private var conflictText = ""
    @State private var conflictBad = false
    func updateConflict() {
        guard !hotkey.key.isEmpty else { conflictText = ""; return }
        KnownShortcuts.shared.load()
        let users = KnownShortcuts.shared.usersOf(hotkey.mods, hotkey.key)
        let combo = comboLabel(hotkey.mods, hotkey.key)
        if users.isEmpty { conflictBad = false; conflictText = "\(combo) — 완전히 빈 조합. 안전하게 쓸 수 있어요." }
        else {
            let glob = users.filter { $0.scope == "global" }
            let apps = Array(Set(users.filter { $0.scope != "global" }.map { $0.scope })).prefix(4)
            conflictBad = true
            conflictText = glob.isEmpty
                ? "\(combo) — 앱에서 사용 중: \(apps.joined(separator: ", ")). 글로벌로 잡으면 그 앱에선 못 씁니다."
                : "\(combo) — 시스템/글로벌에서 사용: \(glob.prefix(2).map { $0.action }.joined(separator: ", ")). 충돌 위험."
        }
    }
    func suggestFree() {
        KnownShortcuts.shared.load()
        if hotkey.mods.isEmpty { hotkey.mods = ["opt"] }
        let taken = Set(Store.shared.hotkeys.filter { $0.mods.sorted() == hotkey.mods.sorted() }.map { $0.key })
        if let k = KnownShortcuts.shared.freeKey(mods: hotkey.mods, avoiding: taken) {
            hotkey.key = k; comboDisplay = comboLabel(hotkey.mods, k); updateConflict()
        }
    }
    var needsApp: Bool { hotkey.action.type == "open_app" }
    var valuePlaceholder: String {
        switch hotkey.action.type {
        case "open_url": return "https://google.com"
        case "open_folder": return "~/Downloads"
        case "open_file": return "~/Documents/todo.md"
        case "run_shell": return "screencapture -i -c"
        case "applescript": return "tell application \"Notes\" to make new note"
        case "paste_text": return "붙여넣을 텍스트"
        default: return ""
        }
    }
    var canSave: Bool { !hotkey.key.isEmpty && (hotkey.action.type == "show_viewer" || !hotkey.action.value.isEmpty) }
    @ViewBuilder func field<T: View>(_ label: String, @ViewBuilder _ content: () -> T) -> some View {
        VStack(alignment: .leading, spacing: 5) {
            Text(label).font(.caption.weight(.semibold)).foregroundColor(.secondary)
            content()
        }
    }
    var body: some View {
        VStack(spacing: 0) {
            // header
            HStack(spacing: 10) {
                Image(systemName: isNew ? "plus.circle.fill" : "pencil.circle.fill").font(.title2).foregroundColor(ACCENT)
                Text(isNew ? "새 글로벌 핫키" : "핫키 편집").font(.headline)
                Spacer()
            }.padding(16)
            Divider()
            VStack(alignment: .leading, spacing: 15) {
                field("제목") { TextField("예: Finder 열기", text: $hotkey.title).textFieldStyle(.roundedBorder) }
                field("단축키 조합") {
                    HStack(spacing: 10) {
                        RecorderField(display: $comboDisplay) { mods, key in hotkey.mods = mods; hotkey.key = key; updateConflict() }
                            .frame(width: 172, height: 30)
                        Button { suggestFree() } label: { Label("빈 키 추천", systemImage: "sparkles") }.buttonStyle(.bordered)
                        Spacer()
                    }
                }
                if !conflictText.isEmpty {
                    HStack(spacing: 8) {
                        Image(systemName: conflictBad ? "exclamationmark.triangle.fill" : "checkmark.circle.fill")
                        Text(conflictText).font(.callout).fixedSize(horizontal: false, vertical: true)
                        Spacer(minLength: 0)
                    }
                    .padding(10)
                    .background(RoundedRectangle(cornerRadius: 9).fill((conflictBad ? Color.orange : Color.green).opacity(0.15)))
                    .foregroundColor(conflictBad ? .orange : .green)
                }
                field("동작") {
                    Picker("", selection: $hotkey.action.type) {
                        ForEach(ACTION_TYPES, id: \.0) { t in
                            Label(t.1, systemImage: actionMeta(t.0).icon).tag(t.0)
                        }
                    }.labelsHidden().pickerStyle(.menu)
                }
                if needsApp {
                    field("앱 선택") {
                        Picker("", selection: $hotkey.action.value) {
                            Text("— 앱을 고르세요 —").tag("")
                            ForEach(apps, id: \.self) { Text($0).tag($0) }
                        }.labelsHidden()
                    }
                } else if hotkey.action.type != "show_viewer" {
                    field("값") { TextField(valuePlaceholder, text: $hotkey.action.value).textFieldStyle(.roundedBorder) }
                }
                Toggle(isOn: $hotkey.anyCombo) {
                    VStack(alignment: .leading, spacing: 1) {
                        Text("다른 앱도 잡기 (anyCombo)")
                        Text("⇧Space 처럼 다른 앱과 겹치는 조합까지 가로챕니다 · 손쉬운 사용 권한 필요")
                            .font(.caption).foregroundColor(.secondary)
                    }
                }.tint(ACCENT)
            }.padding(18)
            Divider()
            // footer
            HStack {
                if hotkey.anyCombo && !Accessibility.isTrusted {
                    Button { Accessibility.requestTrust(); Accessibility.openSettings() } label: { Label("권한 열기", systemImage: "lock.open") }.font(.caption)
                }
                Spacer()
                Button("취소") { onCancel() }.controlSize(.large)
                Button("저장") { onSave(hotkey) }.keyboardShortcut(.defaultAction).buttonStyle(.borderedProminent).tint(ACCENT).controlSize(.large).disabled(!canSave)
            }.padding(16)
        }
        .frame(width: 480)
        .onAppear { comboDisplay = hotkey.key.isEmpty ? "" : comboLabel(hotkey.mods, hotkey.key); apps = installedApps(); updateConflict() }
    }
}

// ══════════════════════ menu-bar app ══════════════════════
final class AppDelegate: NSObject, NSApplicationDelegate, NSWindowDelegate {
    var status: NSStatusItem!
    var registered = 0
    var failed: [String] = []
    var watch: DispatchSourceFileSystemObject?
    var editorWindow: NSWindow?

    func applicationDidFinishLaunching(_ n: Notification) {
        status = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        if let img = NSImage(systemSymbolName: "command.square", accessibilityDescription: "SV Hotkeys") { status.button?.image = img }
        else { status.button?.title = "⌘" }
        HK.suspend = { [weak self] in self?.suspendHotkeys() }
        HK.resume  = { [weak self] in self?.reregister() }
        Store.shared.onChange = { [weak self] in self?.reregister() }
        // URL scheme: let the web viewer apply hotkeys directly (svhotkeys://apply?b64=…)
        NSAppleEventManager.shared().setEventHandler(self, andSelector: #selector(handleGetURL(_:reply:)),
            forEventClass: AEEventClass(kInternetEventClass), andEventID: AEEventID(kAEGetURL))
        let firstRun = !FileManager.default.fileExists(atPath: CONFIG_PATH)
        Store.shared.load()
        reregister()
        watchConfig()
        if firstRun || Store.shared.hotkeys.isEmpty || CommandLine.arguments.contains("--editor") {
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.3) { self.openEditor() }
        }
    }

    func suspendHotkeys() { HotKeyCenter.shared.unregisterAll(); EventTapCenter.shared.disable() }

    func reregister() {
        HotKeyCenter.shared.unregisterAll(); EventTapCenter.shared.disable()
        registered = 0; failed = []
        var tapBinds: [(CGKeyCode, NSEvent.ModifierFlags, () -> Void)] = []
        for hk in Store.shared.hotkeys where hk.enabled {
            guard let kc = KEYCODE[hk.key] else { failed.append("\(comboLabel(hk.mods, hk.key)) (알 수 없는 키)"); continue }
            let act: () -> Void = { Runner.run(hk.action) }
            if hk.anyCombo { tapBinds.append((CGKeyCode(kc), cocoaFlags(hk.mods), act)); registered += 1 }
            else if HotKeyCenter.shared.register(keyCode: kc, mods: carbonMods(hk.mods), action: act) { registered += 1 }
            else { failed.append("\(comboLabel(hk.mods, hk.key)) (예약됨/사용중)") }
        }
        if !tapBinds.isEmpty {
            EventTapCenter.shared.setBinds(tapBinds)
            if !EventTapCenter.shared.enable() { failed.append("\(tapBinds.count)개 anyCombo — 손쉬운 사용 권한 필요") }
        }
        rebuildMenu()
    }

    func rebuildMenu() {
        let menu = NSMenu()
        let head = NSMenuItem(title: "SV Hotkeys — \(registered)개 활성", action: nil, keyEquivalent: ""); head.isEnabled = false; menu.addItem(head)
        menu.addItem(.separator())
        menu.addItem(mk("핫키 편집기 열기…", #selector(openEditor)))
        menu.addItem(mk("＋ 새 핫키", #selector(openEditor)))
        menu.addItem(.separator())
        if Store.shared.hotkeys.isEmpty {
            let m = NSMenuItem(title: "설정된 핫키 없음 — ‘핫키 편집기’에서 추가", action: nil, keyEquivalent: ""); m.isEnabled = false; menu.addItem(m)
        }
        for hk in Store.shared.hotkeys {
            let m = NSMenuItem(title: "\(hk.enabled ? "●" : "○") \(comboLabel(hk.mods, hk.key))   \(hk.title.isEmpty ? hk.action.value : hk.title)", action: #selector(fireNow(_:)), keyEquivalent: "")
            m.representedObject = hk.action; m.target = self; menu.addItem(m)
        }
        if !failed.isEmpty { menu.addItem(.separator()); for f in failed { let m = NSMenuItem(title: "⚠️ \(f)", action: nil, keyEquivalent: ""); m.isEnabled = false; menu.addItem(m) } }
        menu.addItem(.separator())
        if !Accessibility.isTrusted { menu.addItem(mk("any-combo 켜기 (손쉬운 사용…)", #selector(enableAX))) }
        menu.addItem(mk("설정 파일 열기 (hotkeys.json)", #selector(openConfig)))
        menu.addItem(mk("Shortcut Viewer 열기", #selector(openViewer)))
        menu.addItem(mk("다시 읽기 (Reload)", #selector(reloadNow)))
        menu.addItem(.separator())
        menu.addItem(mk("종료", #selector(NSApplication.terminate(_:))))
        status.menu = menu
    }
    func mk(_ t: String, _ s: Selector) -> NSMenuItem { let m = NSMenuItem(title: t, action: s, keyEquivalent: ""); m.target = self; return m }

    @objc func fireNow(_ s: NSMenuItem) { if let a = s.representedObject as? HKAction { Runner.run(a) } }
    @objc func reloadNow() { Store.shared.load(); reregister() }
    @objc func openConfig() {
        if !FileManager.default.fileExists(atPath: CONFIG_PATH) { Store.shared.saveToDisk() }
        NSWorkspace.shared.open(URL(fileURLWithPath: CONFIG_PATH))
    }
    @objc func openViewer() { NSWorkspace.shared.open(URL(fileURLWithPath: ("~/dev/shortcut-viewer/viewer.html" as NSString).expandingTildeInPath)) }
    @objc func enableAX() { Accessibility.requestTrust(); Accessibility.openSettings() }

    @objc func openEditor() {
        if editorWindow == nil {
            let w = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 560, height: 460),
                             styleMask: [.titled, .closable, .miniaturizable], backing: .buffered, defer: false)
            w.title = "SV Hotkeys"
            w.contentViewController = NSHostingController(rootView: EditorView())
            w.center(); w.isReleasedWhenClosed = false; w.delegate = self
            editorWindow = w
        }
        NSApp.setActivationPolicy(.regular)
        NSApp.activate(ignoringOtherApps: true)
        editorWindow?.makeKeyAndOrderFront(nil)
    }
    func windowWillClose(_ n: Notification) { NSApp.setActivationPolicy(.accessory) }

    // ── receive svhotkeys:// URLs from the web viewer ──
    @objc func handleGetURL(_ event: NSAppleEventDescriptor, reply: NSAppleEventDescriptor) {
        if let s = event.paramDescriptor(forKeyword: AEKeyword(keyDirectObject))?.stringValue,
           let url = URL(string: s) { handle(url) }
    }
    func application(_ application: NSApplication, open urls: [URL]) { urls.forEach { handle($0) } }
    func handle(_ url: URL) {
        guard url.scheme == "svhotkeys" else { return }
        switch url.host {
        case "open": openEditor()
        case "apply":
            let comps = URLComponents(url: url, resolvingAgainstBaseURL: false)
            guard let b64 = comps?.queryItems?.first(where: { $0.name == "b64" })?.value,
                  let data = Data(base64Encoded: b64),
                  let cfg = try? JSONDecoder().decode(ConfigFile.self, from: data) else {
                NSSound.beep(); return
            }
            applyFromViewer(cfg.hotkeys)
        default: break
        }
    }
    func applyFromViewer(_ hks: [Hotkey]) {
        NSApp.setActivationPolicy(.regular); NSApp.activate(ignoringOtherApps: true)
        let a = NSAlert()
        a.messageText = "뷰어에서 \(hks.count)개 글로벌 핫키를 적용할까요?"
        a.informativeText = "SV Hotkeys의 현재 설정을 뷰어에서 만든 것으로 대체합니다."
        a.addButton(withTitle: "적용"); a.addButton(withTitle: "취소")
        if a.runModal() == .alertFirstButtonReturn {
            Store.shared.hotkeys = hks; Store.shared.commit(); openEditor()
        } else { NSApp.setActivationPolicy(.accessory) }
    }

    func watchConfig() {
        let dir = (CONFIG_PATH as NSString).deletingLastPathComponent
        try? FileManager.default.createDirectory(atPath: dir, withIntermediateDirectories: true)
        let fd = open(dir, O_EVTONLY); guard fd >= 0 else { return }
        let src = DispatchSource.makeFileSystemObjectSource(fileDescriptor: fd, eventMask: [.write, .rename, .delete], queue: .main)
        src.setEventHandler { [weak self] in DispatchQueue.main.asyncAfter(deadline: .now() + 0.2) { Store.shared.load(); self?.reregister() } }
        src.setCancelHandler { close(fd) }
        src.resume(); watch = src
    }
}

// ══════════════════════ entry ══════════════════════
if CommandLine.arguments.contains("--list") || CommandLine.arguments.contains("--selftest") {
    Store.shared.load()
    print("hotkeys.json: \(CONFIG_PATH)\n항목 \(Store.shared.hotkeys.count)개:")
    for hk in Store.shared.hotkeys {
        let known = KEYCODE[hk.key] != nil ? "✓" : "✗(알 수 없는 키)"
        print("  [\(hk.enabled ? "on":"off")|\(hk.anyCombo ? "eventtap":"carbon")|\(known)] \(comboLabel(hk.mods, hk.key))  →  \(hk.action.type): \(hk.action.value)   (\(hk.title))")
    }
    exit(0)
}
let app = NSApplication.shared
app.setActivationPolicy(.accessory)
let delegate = AppDelegate()
app.delegate = delegate
app.run()
