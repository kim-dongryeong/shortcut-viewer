// SV Hotkeys (Windows) — 초안 skeleton.
// macOS SV Hotkeys와 **같은 hotkeys.json 스키마를 공유**해서 읽고 등록한다(크로스플랫폼 설정 공유).
//   설정 파일:  %APPDATA%\shortcut-viewer\hotkeys.json   (맥의 ~/.config/shortcut-viewer/hotkeys.json 과 동형)
//   없으면 → 마우스 북마크 10칸(⌃⌥n 저장 / ⌥n 클릭) 기본값.
// 수식키 대응(맥→윈): cmd→Win · opt→Alt · ctrl→Ctrl · shift→Shift.
// ⚠️ Windows에서만 빌드/실행됨(Win32 API). Mac에선 컴파일 안 됨.

using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Text.Json;

namespace SvHotkeysWin;

// ── 공유 hotkeys.json 스키마 (맥과 동형; 모르는 필드 anyCombo/app/trigger/sequence는 STJ가 무시) ──
sealed class HkAction { public string type { get; set; } = ""; public string value { get; set; } = ""; }
sealed class Hotkey
{
    public string id { get; set; } = "";
    public string title { get; set; } = "";
    public List<string> mods { get; set; } = new();
    public string key { get; set; } = "";
    public HkAction action { get; set; } = new();
    public bool enabled { get; set; } = true;
}
sealed class Config { public int version { get; set; } = 1; public List<Hotkey> hotkeys { get; set; } = new(); }

static class Program
{
    [STAThread]
    static void Main()
    {
        ApplicationConfiguration.Initialize();
        Application.Run(new TrayContext());
    }

    public static readonly string Dir =
        Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "shortcut-viewer");
    static readonly JsonSerializerOptions J = new() { PropertyNameCaseInsensitive = true };

    public static Config LoadConfig()
    {
        string path = Path.Combine(Dir, "hotkeys.json");
        try { if (File.Exists(path)) return JsonSerializer.Deserialize<Config>(File.ReadAllText(path), J) ?? Default(); }
        catch { }
        return Default();
    }
    // hotkeys.json 없을 때: 마우스 북마크 10칸 (사장님 맥/BTT 방식과 동일)
    static Config Default()
    {
        var c = new Config();
        foreach (char n in "1234567890")
        {
            c.hotkeys.Add(new Hotkey { id = $"mb_save_{n}", title = $"마우스 북마크 {n} 저장", mods = new() { "ctrl", "opt" }, key = n.ToString(), action = new() { type = "mouse_save", value = n.ToString() } });
            c.hotkeys.Add(new Hotkey { id = $"mb_use_{n}", title = $"마우스 북마크 {n} 클릭", mods = new() { "opt" }, key = n.ToString(), action = new() { type = "mouse_click", value = n.ToString() } });
        }
        return c;
    }

    // 액션 실행(맥 Runner.run 대응 — 공통 액션만; applescript/paste_text/show_viewer는 TODO)
    public static void Run(HkAction a)
    {
        switch (a.type)
        {
            case "mouse_save":  MouseBM.Save(a.value); break;
            case "mouse_goto":  MouseBM.Goto(a.value); break;
            case "mouse_click": MouseBM.ClickBookmark(a.value); break;
            case "open_app": case "open_url": case "open_folder": case "open_file":
                try { Process.Start(new ProcessStartInfo(a.value) { UseShellExecute = true }); } catch { } break;
            case "run_shell":
                try { Process.Start(new ProcessStartInfo("cmd.exe", "/c " + a.value) { CreateNoWindow = true }); } catch { } break;
            default: Toast.Show($"미지원 액션: {a.type}"); break;
        }
    }
}

// ── 트레이 앱 ──
sealed class TrayContext : ApplicationContext
{
    readonly HotkeyWindow _win = new();
    readonly NotifyIcon _tray;
    public TrayContext()
    {
        int ok = _win.RegisterAll();
        var menu = new ContextMenuStrip();
        menu.Items.Add($"SV Hotkeys — {ok}개 등록").Enabled = false;
        menu.Items.Add(new ToolStripSeparator());
        menu.Items.Add("설정 폴더 열기 (hotkeys.json)", null, (_, _) =>
        {
            Directory.CreateDirectory(Program.Dir);
            Process.Start("explorer.exe", Program.Dir);
        });
        menu.Items.Add("다시 읽기 (Reload)", null, (_, _) => _win.Reload());
        menu.Items.Add("종료", null, (_, _) => { _win.UnregisterAll(); _tray!.Visible = false; ExitThread(); });
        _tray = new NotifyIcon { Icon = SystemIcons.Application, Visible = true, Text = "SV Hotkeys", ContextMenuStrip = menu };
    }
}

// ── 숨은 메시지 창: hotkeys.json → RegisterHotKey → WM_HOTKEY 디스패치 ──
sealed class HotkeyWindow : NativeWindow
{
    const int WM_HOTKEY = 0x0312;
    const uint MOD_ALT = 0x1, MOD_CONTROL = 0x2, MOD_SHIFT = 0x4, MOD_WIN = 0x8, MOD_NOREPEAT = 0x4000;

    [DllImport("user32.dll")] static extern bool RegisterHotKey(IntPtr hWnd, int id, uint mods, uint vk);
    [DllImport("user32.dll")] static extern bool UnregisterHotKey(IntPtr hWnd, int id);

    readonly Dictionary<int, Hotkey> _byId = new();
    int _count;

    public HotkeyWindow() => CreateHandle(new CreateParams { Parent = new IntPtr(-3) });  // HWND_MESSAGE

    public int RegisterAll()
    {
        var cfg = Program.LoadConfig();
        int ok = 0, id = 1;
        foreach (var h in cfg.hotkeys)
        {
            if (!h.enabled) continue;
            var vk = Vk(h.key);
            if (vk is null) { Console.Error.WriteLine($"알 수 없는 키: {h.key}"); continue; }
            if (RegisterHotKey(Handle, id, ModMask(h.mods), vk.Value)) { _byId[id] = h; ok++; }
            else Console.Error.WriteLine($"RegisterHotKey 실패(예약/사용중): {h.title}");
            id++;
        }
        _count = id;
        return ok;
    }
    public void UnregisterAll() { for (int i = 1; i < _count; i++) UnregisterHotKey(Handle, i); _byId.Clear(); }
    public void Reload() { UnregisterAll(); RegisterAll(); }

    static uint ModMask(List<string> mods)
    {
        uint m = MOD_NOREPEAT;
        foreach (var x in mods)
            m |= x switch { "ctrl" => MOD_CONTROL, "opt" or "alt" => MOD_ALT, "shift" => MOD_SHIFT, "cmd" or "win" => MOD_WIN, _ => 0u };
        return m;
    }
    static uint? Vk(string key)
    {
        if (key.Length == 1)
        {
            char c = char.ToUpperInvariant(key[0]);
            if (c is >= 'A' and <= 'Z') return c;   // VK_A..VK_Z = 'A'..'Z'
            if (c is >= '0' and <= '9') return c;   // VK_0..VK_9
        }
        return key switch
        {
            "Space" => 0x20, "Return" => 0x0D, "Tab" => 0x09, "Escape" => 0x1B,
            "Delete" => 0x08, "ForwardDelete" => 0x2E,
            "Left" => 0x25, "Up" => 0x26, "Right" => 0x27, "Down" => 0x28,
            "Home" => 0x24, "End" => 0x23, "PageUp" => 0x21, "PageDown" => 0x22,
            "F1" => 0x70, "F2" => 0x71, "F3" => 0x72, "F4" => 0x73, "F5" => 0x74, "F6" => 0x75,
            "F7" => 0x76, "F8" => 0x77, "F9" => 0x78, "F10" => 0x79, "F11" => 0x7A, "F12" => 0x7B,
            "-" => 0xBD, "=" => 0xBB, "[" => 0xDB, "]" => 0xDD, "\\" => 0xDC,
            ";" => 0xBA, "'" => 0xDE, "," => 0xBC, "." => 0xBE, "/" => 0xBF, "`" => 0xC0,
            _ => (uint?)null
        };
    }

    protected override void WndProc(ref Message m)
    {
        if (m.Msg == WM_HOTKEY && _byId.TryGetValue(m.WParam.ToInt32(), out var h))
            Program.Run(h.action);
        base.WndProc(ref m);
    }
}

// ── 마우스 북마크(맥 Mouse enum 대응) ──
static class MouseBM
{
    [StructLayout(LayoutKind.Sequential)] public struct POINT { public int X, Y; }
    [DllImport("user32.dll")] static extern bool GetCursorPos(out POINT p);
    [DllImport("user32.dll")] static extern bool SetCursorPos(int x, int y);
    [DllImport("user32.dll")] static extern void mouse_event(uint flags, uint dx, uint dy, uint data, IntPtr extra);
    const uint LEFTDOWN = 0x0002, LEFTUP = 0x0004;   // TODO: SendInput으로 업그레이드

    static readonly string File = Path.Combine(Program.Dir, "mouse_bookmarks.json");
    static Dictionary<string, int[]> _slots = Load();
    static Dictionary<string, int[]> Load()
    {
        try { return JsonSerializer.Deserialize<Dictionary<string, int[]>>(System.IO.File.ReadAllText(File)) ?? new(); }
        catch { return new(); }
    }
    static void Persist()
    {
        try { Directory.CreateDirectory(Program.Dir); System.IO.File.WriteAllText(File, JsonSerializer.Serialize(_slots, new JsonSerializerOptions { WriteIndented = true })); }
        catch { }
    }

    public static void Save(string slot)
    {
        GetCursorPos(out var p); _slots[slot] = new[] { p.X, p.Y }; Persist();
        Toast.Show($"🖱️ 마우스 북마크 {slot} 저장");
    }
    public static void Goto(string slot)   // 이동만
    {
        if (!_slots.TryGetValue(slot, out var a) || a.Length != 2) { Toast.Show($"🖱️ 북마크 {slot} 없음"); return; }
        SetCursorPos(a[0], a[1]);
    }
    public static void ClickBookmark(string slot)   // 현재 기억 → 이동 → 클릭 → 복귀
    {
        if (!_slots.TryGetValue(slot, out var a) || a.Length != 2) { Toast.Show($"🖱️ 북마크 {slot} 없음"); return; }
        Toast.Show($"🖱️ 북마크 {slot} 클릭");
        Task.Run(() =>
        {
            GetCursorPos(out var orig);
            SetCursorPos(a[0], a[1]); Thread.Sleep(80);
            mouse_event(LEFTDOWN, 0, 0, 0, IntPtr.Zero); mouse_event(LEFTUP, 0, 0, 0, IntPtr.Zero);
            Thread.Sleep(60);
            SetCursorPos(orig.X, orig.Y);
        });
    }
}

// ── 세련된 토스트 HUD(맥 HUD 대응): 어두운 라운드 · 하단중앙 · 페이드 · 자동 소멸 ──
static class Toast
{
    [DllImport("gdi32.dll")] static extern IntPtr CreateRoundRectRgn(int l, int t, int r, int b, int w, int h);
    const int W = 340, H = 62;
    static Form? _f; static Label? _l;
    static System.Windows.Forms.Timer? _fade, _hold; static int _dir;

    static void Ensure()
    {
        if (_f != null) return;
        _l = new Label { Dock = DockStyle.Fill, TextAlign = ContentAlignment.MiddleCenter, ForeColor = Color.White, Font = new Font("Segoe UI", 15f, FontStyle.Bold) };
        _f = new Form { FormBorderStyle = FormBorderStyle.None, ShowInTaskbar = false, TopMost = true, StartPosition = FormStartPosition.Manual, BackColor = Color.FromArgb(28, 20, 52), Size = new Size(W, H), Opacity = 0 };
        _f.Region = Region.FromHrgn(CreateRoundRectRgn(0, 0, W + 1, H + 1, 18, 18));
        _f.Controls.Add(_l);
        _fade = new System.Windows.Forms.Timer { Interval = 15 };
        _fade.Tick += (_, _) =>
        {
            double o = _f!.Opacity + _dir * 0.10;
            if (_dir > 0 && o >= 0.96) { o = 0.96; _fade!.Stop(); _hold!.Start(); }
            if (_dir < 0 && o <= 0) { o = 0; _fade!.Stop(); _f.Hide(); }
            _f.Opacity = Math.Clamp(o, 0, 0.96);
        };
        _hold = new System.Windows.Forms.Timer { Interval = 900 };
        _hold.Tick += (_, _) => { _hold!.Stop(); _dir = -1; _fade!.Start(); };
    }
    public static void Show(string text)
    {
        Ensure();
        _l!.Text = text;
        var wa = Screen.PrimaryScreen!.WorkingArea;
        _f!.Location = new Point(wa.Left + (wa.Width - W) / 2, wa.Bottom - (int)(wa.Height * 0.16));
        _hold!.Stop(); _fade!.Stop();
        _f.Opacity = 0; _f.Show(); _f.BringToFront();
        _dir = 1; _fade.Start();
    }
}
