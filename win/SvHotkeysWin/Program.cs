// SV Hotkeys (Windows) — 초안 skeleton.
// macOS의 SV Hotkeys(마우스 북마크 + 글로벌 핫키)에 대응하는 Windows 네이티브 앱.
// 구조는 macOS 버전과 대칭: 글로벌 핫키(Win32 RegisterHotKey) + 마우스 북마크(GetCursorPos/SetCursorPos/mouse_event)
//   + 슬롯 영속화(%APPDATA%\shortcut-viewer\mouse_bookmarks.json) + 트레이 아이콘 + 세련된 토스트 HUD.
// 기본 바인딩(사장님 BTT/맥 방식): Ctrl+Alt+<digit>=저장, Alt+<digit>=클릭+커서복귀 (슬롯 1..9,0 = 10칸).
//
// ⚠️ Windows에서만 빌드/실행됨(Win32 API). Mac에선 컴파일 안 됨 — 이 파일은 Windows용 소스.

using System.Runtime.InteropServices;
using System.Text.Json;

namespace SvHotkeysWin;

static class Program
{
    [STAThread]
    static void Main()
    {
        ApplicationConfiguration.Initialize();     // WinForms 초기화(고DPI: csproj의 PerMonitorV2)
        Application.Run(new TrayContext());        // 메시지 루프 시작 → WM_HOTKEY 디스패치
    }
}

// ── 트레이 앱(맥의 메뉴바 앱에 대응): 숨은 핫키 창 + 트레이 아이콘 + 종료 ──
sealed class TrayContext : ApplicationContext
{
    readonly HotkeyWindow _win = new();
    readonly NotifyIcon _tray;

    public TrayContext()
    {
        int ok = _win.RegisterAll();
        var menu = new ContextMenuStrip();
        menu.Items.Add($"SV Hotkeys — 마우스 북마크 {ok}칸").Enabled = false;
        menu.Items.Add(new ToolStripSeparator());
        menu.Items.Add("설정 폴더 열기", null, (_, _) => MouseBM.OpenFolder());
        menu.Items.Add("종료", null, (_, _) => { _win.UnregisterAll(); _tray!.Visible = false; ExitThread(); });
        _tray = new NotifyIcon { Icon = SystemIcons.Application, Visible = true,
                                 Text = "SV Hotkeys (마우스 북마크)", ContextMenuStrip = menu };
    }
}

// ── 숨은 메시지 전용 창: RegisterHotKey → WM_HOTKEY 수신 ──
sealed class HotkeyWindow : NativeWindow
{
    const int WM_HOTKEY = 0x0312;
    const uint MOD_ALT = 0x1, MOD_CONTROL = 0x2, MOD_SHIFT = 0x4, MOD_WIN = 0x8, MOD_NOREPEAT = 0x4000;

    [DllImport("user32.dll")] static extern bool RegisterHotKey(IntPtr hWnd, int id, uint mods, uint vk);
    [DllImport("user32.dll")] static extern bool UnregisterHotKey(IntPtr hWnd, int id);

    readonly record struct Bind(uint Mods, uint Vk, string Action, string Slot);
    readonly List<Bind> _binds = new();

    public HotkeyWindow()
    {
        CreateHandle(new CreateParams { Parent = new IntPtr(-3) });   // HWND_MESSAGE = message-only 창
    }

    // 10칸(1..9,0): Ctrl+Alt+n = 저장, Alt+n = 클릭+복귀.  ← 바꾸고 싶으면 여기만 수정
    public int RegisterAll()
    {
        foreach (char c in "1234567890")
        {
            uint vk = c;   // '0'..'9' 의 VK 코드 = 문자 코드(0x30..0x39)와 동일
            _binds.Add(new Bind(MOD_CONTROL | MOD_ALT | MOD_NOREPEAT, vk, "save", c.ToString()));
            _binds.Add(new Bind(MOD_ALT | MOD_NOREPEAT, vk, "click", c.ToString()));
        }
        int ok = 0;
        for (int i = 0; i < _binds.Count; i++)
            if (RegisterHotKey(Handle, i + 1, _binds[i].Mods, _binds[i].Vk)) ok++;
            else Console.Error.WriteLine($"RegisterHotKey 실패(예약/사용중): {_binds[i].Action} {_binds[i].Slot}");
        return ok / 2;   // 슬롯 수(저장+클릭 2개가 1칸)
    }

    public void UnregisterAll() { for (int i = 0; i < _binds.Count; i++) UnregisterHotKey(Handle, i + 1); }

    protected override void WndProc(ref Message m)
    {
        if (m.Msg == WM_HOTKEY)
        {
            int id = m.WParam.ToInt32();
            if (id >= 1 && id <= _binds.Count)
            {
                var b = _binds[id - 1];
                if (b.Action == "save") MouseBM.Save(b.Slot);
                else MouseBM.ClickBookmark(b.Slot);
            }
        }
        base.WndProc(ref m);
    }
}

// ── 마우스 북마크(맥 Mouse enum에 대응) ──
static class MouseBM
{
    [StructLayout(LayoutKind.Sequential)] public struct POINT { public int X, Y; }
    [DllImport("user32.dll")] static extern bool GetCursorPos(out POINT p);
    [DllImport("user32.dll")] static extern bool SetCursorPos(int x, int y);
    [DllImport("user32.dll")] static extern void mouse_event(uint flags, uint dx, uint dy, uint data, IntPtr extra);
    const uint LEFTDOWN = 0x0002, LEFTUP = 0x0004;   // (SendInput으로 업그레이드 가능 — 초안은 mouse_event로 단순화)

    static readonly string File = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
        "shortcut-viewer", "mouse_bookmarks.json");

    static Dictionary<string, int[]> _slots = Load();
    static Dictionary<string, int[]> Load()
    {
        try { return JsonSerializer.Deserialize<Dictionary<string, int[]>>(System.IO.File.ReadAllText(File)) ?? new(); }
        catch { return new(); }
    }
    static void Persist()
    {
        try
        {
            Directory.CreateDirectory(Path.GetDirectoryName(File)!);
            System.IO.File.WriteAllText(File, JsonSerializer.Serialize(_slots, new JsonSerializerOptions { WriteIndented = true }));
        }
        catch { }
    }

    public static void Save(string slot)   // 현재 커서 위치 → 슬롯 저장
    {
        GetCursorPos(out var p);
        _slots[slot] = new[] { p.X, p.Y }; Persist();
        Toast.Show($"🖱️ 마우스 북마크 {slot} 저장");
    }

    public static void ClickBookmark(string slot)   // 현재 위치 기억 → 슬롯으로 이동 → 클릭 → 원위치 복귀
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

    public static void OpenFolder()
    {
        Directory.CreateDirectory(Path.GetDirectoryName(File)!);
        System.Diagnostics.Process.Start("explorer.exe", Path.GetDirectoryName(File)!);
    }
}

// ── 세련된 토스트 HUD(맥 HUD에 대응): 어두운 라운드 · 하단 중앙 · 페이드 in/out · 자동 소멸 ──
static class Toast
{
    [DllImport("gdi32.dll")] static extern IntPtr CreateRoundRectRgn(int l, int t, int r, int b, int w, int h);
    const int W = 340, H = 62;

    static Form? _f; static Label? _l;
    static System.Windows.Forms.Timer? _fade; static System.Windows.Forms.Timer? _hold;
    static int _dir;   // +1 fade-in, -1 fade-out

    static void Ensure()
    {
        if (_f != null) return;
        _l = new Label { Dock = DockStyle.Fill, TextAlign = ContentAlignment.MiddleCenter,
                         ForeColor = Color.White, Font = new Font("Segoe UI", 15f, FontStyle.Bold) };
        _f = new Form
        {
            FormBorderStyle = FormBorderStyle.None, ShowInTaskbar = false, TopMost = true,
            StartPosition = FormStartPosition.Manual, BackColor = Color.FromArgb(28, 20, 52),
            Size = new Size(W, H), Opacity = 0
        };
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
        _hold = new System.Windows.Forms.Timer { Interval = 900 };   // 표시 유지 시간
        _hold.Tick += (_, _) => { _hold!.Stop(); _dir = -1; _fade!.Start(); };
    }

    public static void Show(string text)   // 핫키 핸들러(UI 스레드)에서 호출됨
    {
        Ensure();
        _l!.Text = text;
        var wa = Screen.PrimaryScreen!.WorkingArea;
        _f!.Location = new Point(wa.Left + (wa.Width - W) / 2, wa.Bottom - (int)(wa.Height * 0.16));
        _hold!.Stop(); _fade!.Stop();
        _f.Opacity = 0; _f.Show(); _f.BringToFront();
        _dir = 1; _fade.Start();   // 페이드 인 → hold → 페이드 아웃
    }
}
