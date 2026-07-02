// svhotkeys.swift — Shortcut Viewer's global-hotkey daemon ("SV Hotkeys").
// A tiny menu-bar app that reads ~/.config/shortcut-viewer/hotkeys.json and registers
// each entry as a GLOBAL keyboard shortcut that runs an action (open app/URL/file,
// run shell, AppleScript, paste text). This is the "our app directly SETS global
// shortcuts" backend — the viewer finds a conflict-free combo, this makes it real.
//
// Two mechanisms (hotkey mechanism proven in ~/dev/maverything):
//   • Carbon RegisterEventHotKey — DEFAULT, needs NO Accessibility permission. Works
//     for ⌘/⌥/⌃-based combos (what the viewer's free-combo finder recommends).
//   • CGEventTap — opt-in ("anyCombo": true or --tap), needs Accessibility, but can
//     grab combos other apps also claim (⇧Space, plain F-keys…) and CONSUME them.
//
// Build (universal, Apple Silicon + Intel):  ./build.sh
// Self-test without a GUI:                    ./svhotkeys --list      (prints parsed config)
import AppKit
import Carbon.HIToolbox
import ApplicationServices

// ─────────────────────────── key-name → Carbon virtual keycode ───────────────────────────
// Names match the viewer's key vocabulary (A–Z, 0–9, punctuation, Space/Return/…, arrows, F1–F20)
// so a hotkeys.json exported from viewer.html round-trips exactly.
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
let MODSYM: [String: String] = ["cmd":"⌘","opt":"⌥","ctrl":"⌃","shift":"⇧"]

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
func comboLabel(_ mods: [String], _ key: String) -> String {
    (["ctrl","opt","shift","cmd"].filter { mods.contains($0) }.map { MODSYM[$0]! }.joined()) + key
}

// ─────────────────────────── config model ───────────────────────────
struct Action: Decodable { let type: String; let value: String }
struct Hotkey: Decodable {
    let id: String?; let title: String?
    let mods: [String]; let key: String
    let action: Action
    let enabled: Bool?
    let anyCombo: Bool?
}
struct Config: Decodable { let version: Int?; let hotkeys: [Hotkey] }

let CONFIG_PATH = ("~/.config/shortcut-viewer/hotkeys.json" as NSString).expandingTildeInPath

func loadConfig() -> Config {
    guard let data = FileManager.default.contents(atPath: CONFIG_PATH) else {
        return Config(version: 1, hotkeys: [])
    }
    do { return try JSONDecoder().decode(Config.self, from: data) }
    catch { FileHandle.standardError.write("⚠️ hotkeys.json 파싱 실패: \(error)\n".data(using: .utf8)!)
            return Config(version: 1, hotkeys: []) }
}

// ─────────────────────────── action execution ───────────────────────────
enum Runner {
    static func run(_ a: Action) {
        switch a.type {
        case "open_app":
            // value = app name / path / bundle id
            if a.value.hasPrefix("/") { NSWorkspace.shared.open(URL(fileURLWithPath: a.value)) }
            else if a.value.contains(".") && !a.value.contains(" ") { // looks like a bundle id
                if let url = NSWorkspace.shared.urlForApplication(withBundleIdentifier: a.value) {
                    NSWorkspace.shared.openApplication(at: url, configuration: .init())
                } else { shell("open -a \(q(a.value))") }
            } else { shell("open -a \(q(a.value))") }
        case "open_url":
            if let url = URL(string: a.value) { NSWorkspace.shared.open(url) }
        case "open_file", "open_folder":
            NSWorkspace.shared.open(URL(fileURLWithPath: (a.value as NSString).expandingTildeInPath))
        case "run_shell":
            shell(a.value)
        case "applescript":
            shell("osascript -e \(q(a.value))")
        case "paste_text":
            paste(a.value)
        case "show_viewer":
            // open the Shortcut Viewer HTML if present
            let p = (a.value.isEmpty ? "~/dev/shortcut-viewer/viewer.html" : a.value) as NSString
            NSWorkspace.shared.open(URL(fileURLWithPath: p.expandingTildeInPath))
        default:
            FileHandle.standardError.write("⚠️ 알 수 없는 action type: \(a.type)\n".data(using: .utf8)!)
        }
    }
    static func q(_ s: String) -> String { "'" + s.replacingOccurrences(of: "'", with: "'\\''") + "'" }
    static func shell(_ cmd: String) {
        let p = Process(); p.launchPath = "/bin/zsh"; p.arguments = ["-lc", cmd]
        do { try p.run() } catch { FileHandle.standardError.write("shell 실패: \(error)\n".data(using: .utf8)!) }
    }
    // Set clipboard then synthesize ⌘V (needs Accessibility to post into the frontmost app).
    static func paste(_ text: String) {
        let pb = NSPasteboard.general; pb.clearContents(); pb.setString(text, forType: .string)
        let src = CGEventSource(stateID: .combinedSessionState)
        let vKey = CGKeyCode(kVK_ANSI_V)
        let down = CGEvent(keyboardEventSource: src, virtualKey: vKey, keyDown: true)
        let up   = CGEvent(keyboardEventSource: src, virtualKey: vKey, keyDown: false)
        down?.flags = .maskCommand; up?.flags = .maskCommand
        down?.post(tap: .cgAnnotatedSessionEventTap); up?.post(tap: .cgAnnotatedSessionEventTap)
    }
}

// ─────────────────────────── Carbon multi-hotkey (no Accessibility) ───────────────────────────
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
        let id = nextID
        var ref: EventHotKeyRef?
        let hkid = EventHotKeyID(signature: OSType(0x5356_4859), id: id)   // 'SVHY'
        let st = RegisterEventHotKey(UInt32(keyCode), mods, hkid, GetApplicationEventTarget(), 0, &ref)
        guard st == noErr, let ref else { return false }
        refs.append(ref); actions[id] = action; nextID += 1; return true
    }
    func unregisterAll() {
        for r in refs { if let r { UnregisterEventHotKey(r) } }
        refs = []; actions = [:]; nextID = 1
    }
}

// ─────────────────────────── CGEventTap multi-hotkey (any combo; needs Accessibility) ───────────────────────────
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
                DispatchQueue.main.async { b.action() }
                return nil   // consume
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

// ─────────────────────────── menu-bar app ───────────────────────────
final class AppDelegate: NSObject, NSApplicationDelegate {
    var status: NSStatusItem!
    var config = Config(version: 1, hotkeys: [])
    var registered = 0, failed: [String] = []
    var watch: DispatchSourceFileSystemObject?

    func applicationDidFinishLaunching(_ n: Notification) {
        status = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        status.button?.title = "⌘"
        reload()
        watchConfig()
    }

    func reload() {
        HotKeyCenter.shared.unregisterAll(); EventTapCenter.shared.disable()
        config = loadConfig(); registered = 0; failed = []
        var tapBinds: [(CGKeyCode, NSEvent.ModifierFlags, () -> Void)] = []
        for hk in config.hotkeys where (hk.enabled ?? true) {
            guard let kc = KEYCODE[hk.key] else { failed.append("\(comboLabel(hk.mods, hk.key)) (알 수 없는 키)"); continue }
            let act: () -> Void = { Runner.run(hk.action) }
            if hk.anyCombo == true {
                tapBinds.append((CGKeyCode(kc), cocoaFlags(hk.mods), act)); registered += 1
            } else {
                if HotKeyCenter.shared.register(keyCode: kc, mods: carbonMods(hk.mods), action: act) { registered += 1 }
                else { failed.append("\(comboLabel(hk.mods, hk.key)) (예약됨/사용중)") }
            }
        }
        if !tapBinds.isEmpty {
            EventTapCenter.shared.setBinds(tapBinds)
            if !EventTapCenter.shared.enable() {
                failed.append("\(tapBinds.count)개 anyCombo — Accessibility 권한 필요")
            }
        }
        rebuildMenu()
    }

    func rebuildMenu() {
        let menu = NSMenu()
        let header = NSMenuItem(title: "SV Hotkeys — \(registered)개 활성", action: nil, keyEquivalent: "")
        header.isEnabled = false; menu.addItem(header)
        menu.addItem(.separator())
        if config.hotkeys.isEmpty {
            let m = NSMenuItem(title: "설정된 핫키 없음 — 뷰어에서 만들어 내보내세요", action: nil, keyEquivalent: "")
            m.isEnabled = false; menu.addItem(m)
        }
        for hk in config.hotkeys {
            let on = hk.enabled ?? true
            let label = "\(on ? "●" : "○") \(comboLabel(hk.mods, hk.key))   \(hk.title ?? hk.action.value)"
            let m = NSMenuItem(title: label, action: #selector(fireNow(_:)), keyEquivalent: "")
            m.representedObject = hk.action; m.target = self
            menu.addItem(m)
        }
        if !failed.isEmpty {
            menu.addItem(.separator())
            for f in failed {
                let m = NSMenuItem(title: "⚠️ \(f)", action: nil, keyEquivalent: ""); m.isEnabled = false; menu.addItem(m)
            }
        }
        menu.addItem(.separator())
        let ax = NSMenuItem(title: Accessibility.isTrusted ? "any-combo: 켜짐 (Accessibility ✓)" : "any-combo 켜기 (Accessibility…)",
                            action: Accessibility.isTrusted ? nil : #selector(enableAX), keyEquivalent: "")
        ax.target = self; if Accessibility.isTrusted { ax.isEnabled = false }; menu.addItem(ax)
        menu.addItem(NSMenuItem(title: "설정 파일 열기 (hotkeys.json)", action: #selector(openConfig), keyEquivalent: ""))
        menu.addItem(NSMenuItem(title: "다시 읽기 (Reload)", action: #selector(reloadMenu), keyEquivalent: "r"))
        menu.addItem(NSMenuItem(title: "Shortcut Viewer 열기", action: #selector(openViewer), keyEquivalent: ""))
        menu.addItem(.separator())
        menu.addItem(NSMenuItem(title: "종료 (Quit)", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q"))
        for it in menu.items where it.action != nil && it.target == nil { it.target = self }
        status.menu = menu
    }
    @objc func fireNow(_ s: NSMenuItem) { if let a = s.representedObject as? Action { Runner.run(a) } }
    @objc func reloadMenu() { reload() }
    @objc func openConfig() {
        let dir = (CONFIG_PATH as NSString).deletingLastPathComponent
        try? FileManager.default.createDirectory(atPath: dir, withIntermediateDirectories: true)
        if !FileManager.default.fileExists(atPath: CONFIG_PATH) {
            try? "{\n \"version\": 1,\n \"hotkeys\": []\n}\n".write(toFile: CONFIG_PATH, atomically: true, encoding: .utf8)
        }
        NSWorkspace.shared.open(URL(fileURLWithPath: CONFIG_PATH))
    }
    @objc func openViewer() {
        NSWorkspace.shared.open(URL(fileURLWithPath: ("~/dev/shortcut-viewer/viewer.html" as NSString).expandingTildeInPath))
    }
    @objc func enableAX() { Accessibility.requestTrust(); Accessibility.openSettings() }

    func watchConfig() {   // live-reload when hotkeys.json changes (viewer re-exports it)
        let dir = (CONFIG_PATH as NSString).deletingLastPathComponent
        try? FileManager.default.createDirectory(atPath: dir, withIntermediateDirectories: true)
        let fd = open(dir, O_EVTONLY); guard fd >= 0 else { return }
        let src = DispatchSource.makeFileSystemObjectSource(fileDescriptor: fd, eventMask: [.write, .rename, .delete], queue: .main)
        src.setEventHandler { [weak self] in DispatchQueue.main.asyncAfter(deadline: .now() + 0.2) { self?.reload() } }
        src.setCancelHandler { close(fd) }
        src.resume(); watch = src
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

// ─────────────────────────── entry ───────────────────────────
let args = CommandLine.arguments
if args.contains("--list") || args.contains("--selftest") {
    // Headless verification: parse config, resolve keys, report — no GUI, no registration.
    let c = loadConfig()
    print("hotkeys.json: \(CONFIG_PATH)")
    print("항목 \(c.hotkeys.count)개:")
    for hk in c.hotkeys {
        let known = KEYCODE[hk.key] != nil ? "✓" : "✗(알 수 없는 키)"
        let mech = (hk.anyCombo == true) ? "eventtap" : "carbon"
        let on = (hk.enabled ?? true) ? "on" : "off"
        print("  [\(on)|\(mech)|\(known)] \(comboLabel(hk.mods, hk.key))  →  \(hk.action.type): \(hk.action.value)   (\(hk.title ?? ""))")
    }
    exit(0)
}
let app = NSApplication.shared
app.setActivationPolicy(.accessory)   // menu-bar only, no Dock icon
let delegate = AppDelegate()
app.delegate = delegate
app.run()
