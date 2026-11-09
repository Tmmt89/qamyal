"""Всё, что отличается в Windows и macOS: процессы, сон, уведомления, открытие файлов, пути к программам.
Остальной код зовёт только эти функции и не проверяет систему сам."""
import os
import shutil
import subprocess
import sys
from pathlib import Path

IS_WIN = sys.platform == "win32"
IS_MAC = sys.platform == "darwin"

# subprocess без мелькающего чёрного окна (в Windows); в macOS окна у консольных программ и так нет
HIDDEN = {"creationflags": 0x08000000} if IS_WIN else {}


def pid_alive(pid: int) -> bool:
    if not pid:
        return False
    if IS_WIN:
        import ctypes
        k = ctypes.windll.kernel32
        h = k.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not h:
            return False
        code = ctypes.c_ulong()
        ok = k.GetExitCodeProcess(h, ctypes.byref(code))
        k.CloseHandle(h)
        return bool(ok) and code.value == 259  # STILL_ACTIVE
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def gui_python() -> str:
    """Python без консольного окна: pythonw в Windows, обычный в macOS."""
    if IS_WIN:
        return str(Path(sys.executable).with_name("pythonw.exe"))
    return sys.executable


def pipe_python() -> str:
    """Python для дочернего процесса на трубах stdin/stdout: python.exe в Windows (у pythonw их может не быть)."""
    if IS_WIN:
        return str(Path(sys.executable).with_name("python.exe"))
    return sys.executable


def spawn_detached(args: list, cwd: Path) -> None:
    """Процесс, который живёт сам по себе (обработчик очереди переживает закрытие окна)."""
    if IS_WIN:
        subprocess.Popen(args, cwd=cwd, creationflags=0x08000000 | 0x00000008, close_fds=True)
    else:
        subprocess.Popen(args, cwd=cwd, start_new_session=True, close_fds=True,
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


_caffeinate = [None]


def keep_awake(on: bool) -> None:
    """Не даём компьютеру уснуть, пока идёт обработка (экран может гаснуть)."""
    if IS_WIN:
        import ctypes
        ES_CONTINUOUS, ES_SYSTEM_REQUIRED = 0x80000000, 0x00000001
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | (ES_SYSTEM_REQUIRED if on else 0))
    elif IS_MAC:
        p = _caffeinate[0]
        if on and (p is None or p.poll() is not None):
            # -i: не засыпать от бездействия; -w: сам выключится, если наш процесс завершится
            _caffeinate[0] = subprocess.Popen(["/usr/bin/caffeinate", "-i", "-w", str(os.getpid())])
        elif not on and p is not None:
            p.terminate()
            _caffeinate[0] = None


def low_priority() -> None:
    """Пониженный приоритет: окно программы и диктофон не должны тормозить."""
    if IS_WIN:
        import ctypes
        k = ctypes.windll.kernel32
        k.SetPriorityClass(k.GetCurrentProcess(), 0x00004000)  # BELOW_NORMAL_PRIORITY_CLASS
    else:
        try:
            os.nice(10)
        except OSError:
            pass


def _osa(text: str) -> str:
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def notify(title: str, text: str, target: Path = None, icon: Path = None) -> None:
    """Системное уведомление; в Windows щелчок по нему открывает target."""
    if IS_WIN:
        from winotify import Notification
        Notification(app_id="Qamyal", title=title, msg=text, launch=str(target or ""),
                     icon=str(icon or "")).show()
    elif IS_MAC:
        subprocess.run(["/usr/bin/osascript", "-e", f"display notification {_osa(text)} with title {_osa(title)}"],
                       capture_output=True, timeout=10)


def open_path(path: Path) -> None:
    """Открыть файл или папку программой по умолчанию (Word, Finder/Проводник)."""
    if IS_WIN:
        os.startfile(str(path))
    elif IS_MAC:
        subprocess.Popen(["/usr/bin/open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


def open_console(args: list, title: str) -> None:
    """Видимое окно терминала с командой (например, вход в ChatGPT — пользователь видит, что происходит)."""
    if IS_WIN:
        subprocess.Popen(["cmd", "/c", f"title {title} & " + subprocess.list2cmdline(args) +
                          " & echo. & echo Можно закрыть это окно. & pause"],
                         creationflags=subprocess.CREATE_NEW_CONSOLE)
    elif IS_MAC:
        import shlex
        cmd = " ".join(shlex.quote(a) for a in args)
        subprocess.Popen(["/usr/bin/osascript", "-e", f'tell application "Terminal" to do script {_osa(cmd)}',
                          "-e", 'tell application "Terminal" to activate'])


# ---------- окна программы в Windows: Chrome без адресной строки ----------
# На Mac окна рисует оболочка Qamyal.app (mac/QamyalApp.swift), там эти функции не нужны.

MINI_TITLE = "Qamyal · "          # заголовок мини-окна начинается так; у основного — ровно «Qamyal»


def chrome_exe():
    import winreg
    key = r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe"
    for root in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        try:
            p = winreg.QueryValue(root, key)
            if p and Path(p).exists():
                return p
        except OSError:
            pass
    for p in (Path.home() / "AppData/Local/Google/Chrome/Application/chrome.exe",
              Path("C:/Program Files/Google/Chrome/Application/chrome.exe"),
              Path("C:/Program Files (x86)/Google/Chrome/Application/chrome.exe")):
        if p.exists():
            return str(p)
    return None


def open_app_window(url: str, profile: Path, extra: list = ()):
    """Окно Chrome-приложения (без вкладок и адресной строки) с отдельным профилем программы."""
    exe = chrome_exe()
    if not exe:
        raise RuntimeError("Не найден Google Chrome")
    return subprocess.Popen([exe, f"--app={url}", f"--user-data-dir={profile}", *extra,
                             "--no-first-run", "--no-default-browser-check",
                             "--disable-features=Translate,MediaRouter", "--disable-sync"])


def find_window(title: str = "Qamyal", prefix: bool = False):
    """Видимое окно Chrome-приложения с этим заголовком (prefix — заголовок только начинается так)."""
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    found = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def each(h, _):
        if user32.IsWindowVisible(h):
            t, cls = ctypes.create_unicode_buffer(128), ctypes.create_unicode_buffer(64)
            user32.GetWindowTextW(h, t, 128)
            user32.GetClassNameW(h, cls, 64)
            if (t.value.startswith(title) if prefix else t.value == title) and cls.value.startswith("Chrome_WidgetWin"):
                found.append(h)
        return True

    user32.EnumWindows(each, 0)
    return found[0] if found else None


def focus_window(h) -> None:
    import ctypes
    user32 = ctypes.windll.user32
    if user32.IsIconic(h):
        user32.ShowWindow(h, 9)                                       # SW_RESTORE
    if not user32.SetForegroundWindow(h):
        user32.keybd_event(0x12, 0, 0, 0)                             # Alt снимает запрет Windows
        user32.keybd_event(0x12, 0, 2, 0)                             # на перевод окна вперёд
        user32.SetForegroundWindow(h)


def _set_topmost(h, on: bool) -> None:
    import ctypes
    from ctypes import wintypes
    # HWND_TOPMOST / HWND_NOTOPMOST; SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE
    ctypes.windll.user32.SetWindowPos(wintypes.HWND(h), wintypes.HWND(-1 if on else -2), 0, 0, 0, 0, 0x0013)


def show_main_window(url: str, profile: Path) -> None:
    h = find_window()
    if h:
        focus_window(h)
    else:
        open_app_window(url, profile)


def set_mini_top(on: bool) -> None:
    h = find_window(MINI_TITLE, prefix=True)
    if h:
        _set_topmost(h, on)


def fix_mini_size(w: int, hh: int) -> None:
    """Мини-окно постоянного размера: без растягивания за края и без «Развернуть»."""
    import ctypes
    from ctypes import wintypes
    h = find_window(MINI_TITLE, prefix=True)
    if not h or not (200 <= w <= 900 and 100 <= hh <= 700):
        return
    user32 = ctypes.windll.user32
    if user32.IsZoomed(wintypes.HWND(h)):
        user32.ShowWindow(wintypes.HWND(h), 9)                        # SW_RESTORE
    style = user32.GetWindowLongW(wintypes.HWND(h), -16)              # GWL_STYLE
    user32.SetWindowLongW(wintypes.HWND(h), -16, style & ~(0x00040000 | 0x00010000))  # WS_THICKFRAME, WS_MAXIMIZEBOX
    # SWP_NOMOVE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED
    user32.SetWindowPos(wintypes.HWND(h), None, 0, 0, w, hh, 0x0002 | 0x0004 | 0x0010 | 0x0020)


def open_mini_window(url: str, profile: Path, top: bool, rect=None) -> None:
    """Мини-окно: уже открыто — показываем; иначе открываем там, где его оставили (rect — x, y, ширина,
    высота в точках экрана; окно само сообщает их программе), а в первый раз — в правом нижнем углу."""
    h = find_window(MINI_TITLE, prefix=True)
    if h:
        focus_window(h)
        _set_topmost(h, top)
        return
    open_app_window(url, profile, ["--window-size=274,126"])

    def place():
        import ctypes
        import time
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        for _ in range(60):                       # окно получает заголовок, когда страница загрузилась
            time.sleep(0.25)
            h = find_window(MINI_TITLE, prefix=True)
            if h:
                break
        else:
            return
        sx, sy = user32.GetSystemMetrics(76), user32.GetSystemMetrics(77)          # все мониторы вместе
        sw, sh = user32.GetSystemMetrics(78), user32.GetSystemMetrics(79)
        if rect and len(rect) == 4 and sx <= rect[0] and sy <= rect[1] and \
                rect[0] + rect[2] <= sx + sw and rect[1] + rect[3] <= sy + sh and min(rect[2:]) > 100:
            x, y, w, hh = (int(v) for v in rect)
        else:                                    # первый раз или того монитора больше нет
            wa = wintypes.RECT()
            user32.SystemParametersInfoW(0x30, 0, ctypes.byref(wa), 0)  # SPI_GETWORKAREA
            w, hh = 274, 126                      # 260×88 внутри + рамка Chrome
            x, y = wa.right - w - 16, wa.bottom - hh - 16
        user32.SetWindowPos(wintypes.HWND(h), None, x, y, w, hh, 0x0014)       # SWP_NOZORDER | SWP_NOACTIVATE
        _set_topmost(h, top)

    import threading
    threading.Thread(target=place, daemon=True).start()


def find_program(name: str, extra: list = ()) -> str:
    """Путь к программе: PATH, затем привычные места. Программу из Dock в macOS запускают с коротким PATH,
    поэтому Homebrew и ~/.local/bin проверяем явно."""
    exe = name + ".exe" if IS_WIN else name
    found = shutil.which(exe)
    if found:
        return found
    home = Path.home()
    places = list(extra) + [home / ".local" / "bin" / exe]
    if IS_MAC:
        places += [Path("/opt/homebrew/bin") / exe, Path("/usr/local/bin") / exe,
                   home / ".npm-global" / "bin" / exe, home / ".claude" / "local" / exe]
    if IS_WIN:
        places += [home / "AppData/Local/Microsoft/WinGet/Links" / exe, Path(os.environ.get("APPDATA", "")) / "npm" / (name + ".cmd"),
                   Path(os.environ.get("LOCALAPPDATA", "")) / "Programs/OpenAI/Codex/bin" / exe]   # установщик Codex
    for p in places:
        if p and Path(p).exists():
            return str(p)
    return ""


_machine = {}


def machine_info() -> dict:
    """Что за компьютер: модель, процессор, память (ГБ), ядра — чтобы посоветовать вариант Whisper."""
    if _machine:
        return _machine
    info = {"model": "", "chip": "", "ram_gb": 0, "cores": os.cpu_count() or 0}
    try:
        if IS_MAC:
            import json
            out = subprocess.run(["/usr/sbin/system_profiler", "SPHardwareDataType", "-json"],
                                 capture_output=True, text=True, timeout=20).stdout
            hw = json.loads(out)["SPHardwareDataType"][0]
            info["model"] = hw.get("machine_name", "")
            info["chip"] = hw.get("chip_type") or hw.get("cpu_type", "")
            info["ram_gb"] = int(str(hw.get("physical_memory", "0")).split()[0])
        elif IS_WIN:
            import ctypes
            import winreg

            def reg(path, name):
                try:
                    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path) as k:
                        return str(winreg.QueryValueEx(k, name)[0]).strip()
                except OSError:
                    return ""
            bios = r"HARDWARE\DESCRIPTION\System\BIOS"
            maker = reg(bios, "SystemManufacturer").replace(" Inc.", "").replace(" Corporation", "")
            info["model"] = " ".join(x for x in (maker, reg(bios, "SystemProductName")) if x)
            import re
            cpu = reg(r"HARDWARE\DESCRIPTION\System\CentralProcessor\0", "ProcessorNameString")
            cpu = re.sub(r"\((R|TM)\)|\bCPU\b|@.*$|\d+(th|st|nd|rd) Gen", " ", cpu, flags=re.I)   # «Intel Core i5-4300U»
            info["chip"] = " ".join(cpu.split())

            class MEM(ctypes.Structure):
                _fields_ = [("len", ctypes.c_ulong), ("load", ctypes.c_ulong), ("total", ctypes.c_ulonglong),
                            ("avail", ctypes.c_ulonglong), ("pf", ctypes.c_ulonglong), ("pfa", ctypes.c_ulonglong),
                            ("vt", ctypes.c_ulonglong), ("va", ctypes.c_ulonglong), ("ve", ctypes.c_ulonglong)]
            m = MEM(len=ctypes.sizeof(MEM))
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
            info["ram_gb"] = round(m.total / 2 ** 30)
    except Exception:  # noqa: BLE001 — без сведений просто не будет совета
        pass
    _machine.update(info)
    return _machine


def claude_desktop_configs() -> list:
    """Файлы настроек Claude Desktop, куда вписывают MCP-серверы. Обычное место — папка Claude
    (%APPDATA% в Windows, Application Support в macOS); если приложение держит данные в отдельной
    папке (Claude-Data\\claude_…), настройки там. Пусто — Claude Desktop не установлен."""
    if IS_WIN:
        base, other = Path(os.environ.get("APPDATA", "")), Path(os.environ.get("LOCALAPPDATA", ""))
    elif IS_MAC:
        base = other = Path.home() / "Library" / "Application Support"
    else:
        base = other = Path.home() / ".config"
    dirs = [base / "Claude"] + sorted((other / "Claude-Data").glob("claude_*"))
    found = [d / "claude_desktop_config.json" for d in dirs if (d / "claude_desktop_config.json").exists()]
    return found or ([dirs[0] / "claude_desktop_config.json"] if dirs[0].is_dir() else [])


def records_dir(root: Path) -> Path:
    """Где лежат записи: на Mac — в «Документах» (~/Documents/Qamyal), в Windows — рядом с программой."""
    if IS_MAC:
        return Path.home() / "Documents" / "Qamyal"
    return root / "Записи"


def os_name() -> str:
    """«macOS 26.2» / «Windows 10» — для карточки «О программе»."""
    import platform
    if IS_MAC:
        return "macOS " + platform.mac_ver()[0]
    if IS_WIN:
        return "Windows " + platform.release()
    return platform.platform()


def default_threads() -> int:
    """Сколько потоков отдавать моделям: на этом ноутбуке 2 физических ядра, на Mac M-серии — 4 больших."""
    if IS_MAC:
        return max(2, min(4, (os.cpu_count() or 4) // 2))
    return 2


# ---------- запись экрана: Windows — ffmpeg, macOS — помощник QamyalScreen (ScreenCaptureKit) ----------

MAC_SCREEN = Path(__file__).with_name("mac") / "QamyalScreen"     # собирает install.sh / setup.sh из mac/QamyalScreen.swift


def screen_supported() -> bool:
    """Windows — ffmpeg; macOS — помощник QamyalScreen (разрешение «Запись экрана» macOS спросит сама)."""
    return IS_WIN or (IS_MAC and MAC_SCREEN.exists())


def screen_helper(height: int, fps: int, quality: int):
    """macOS: команда помощника без имени файла. Он и снимает экран, и рисует рамку, и понимает «q» в stdin,
    и пишет «out_time_us=…» в stdout — как ffmpeg в Windows. В Windows — None."""
    if not IS_MAC:
        return None
    return [str(MAC_SCREEN), "--fps", str(fps), "--height", str(height), "--quality", str(quality)]


def screen_monitors() -> list:
    """Мониторы в настоящих пикселях (без масштаба Windows): [{x, y, w, h, primary}], основной — первым."""
    if not IS_WIN:
        return []
    import ctypes
    from ctypes import wintypes
    u = ctypes.windll.user32
    try:
        old = u.SetThreadDpiAwarenessContext(ctypes.c_void_p(-4))     # PER_MONITOR_AWARE_V2: координаты без масштаба
    except AttributeError:
        old = None

    class MONITORINFO(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT), ("rcWork", wintypes.RECT),
                    ("dwFlags", wintypes.DWORD)]

    out = []
    proc = ctypes.WINFUNCTYPE(ctypes.c_int, wintypes.HMONITOR, wintypes.HDC, ctypes.POINTER(wintypes.RECT),
                              wintypes.LPARAM)

    def cb(h, _dc, _rc, _lp):
        mi = MONITORINFO()
        mi.cbSize = ctypes.sizeof(MONITORINFO)
        if u.GetMonitorInfoW(h, ctypes.byref(mi)):
            r = mi.rcMonitor
            out.append({"x": r.left, "y": r.top, "w": r.right - r.left, "h": r.bottom - r.top,
                        "primary": bool(mi.dwFlags & 1)})
        return 1

    try:
        u.EnumDisplayMonitors(None, None, proc(cb), 0)
    finally:
        if old:
            u.SetThreadDpiAwarenessContext(ctypes.c_void_p(old))
    out.sort(key=lambda m: (not m["primary"], m["x"], m["y"]))
    return out


def screen_inputs(fps: int, monitor: int = 0) -> list:
    """Способы снять экран для ffmpeg, лучший — первым: (аргументы до -i включительно, фильтр в начало цепочки)."""
    if not IS_WIN:
        return []
    mons = screen_monitors()
    m = mons[monitor] if 0 <= monitor < len(mons) else (mons[0] if mons else None)
    out = []
    if len(mons) <= 1:    # Desktop Duplication: почти не грузит процессор (номер выхода DXGI = основной монитор)
        out.append((["-f", "lavfi", "-i", f"ddagrab=framerate={fps}:output_idx=0"], "hwdownload,format=bgra"))
    rect = ["-offset_x", str(m["x"]), "-offset_y", str(m["y"]), "-video_size", f"{m['w']}x{m['h']}"] if m else []
    out.append((["-f", "gdigrab", "-framerate", str(fps), *rect, "-i", "desktop"], ""))
    return out


def screen_encoders(quality: int, fps: int) -> list:
    """Кодеры видео, лучший — первым: (аргументы, формат кадра). Аппаратный Intel Quick Sync почти не тратит процессор."""
    gop = ["-g", str(max(2, fps * 2))]
    out = []
    if IS_WIN:
        out.append((["-c:v", "h264_qsv", "-global_quality", str(quality), "-look_ahead", "0", "-async_depth", "1", *gop],
                    "nv12"))
    # zerolatency: кодер не копит кадры — иначе время первого кадра (по нему сводится звук) уезжает на секунды
    out.append((["-c:v", "libx264", "-preset", "ultrafast" if fps > 5 else "veryfast", "-crf", str(quality),
                 "-tune", "zerolatency", *gop], "yuv420p"))
    return out


_kill_job = None


def kill_with_parent(proc) -> None:
    """Windows: дочерний процесс (ffmpeg) закрывается вместе с программой, даже если она упала.
    Job Object с KILL_ON_JOB_CLOSE: его описатель живёт, пока жива программа."""
    global _kill_job
    if not IS_WIN:
        return
    import ctypes
    from ctypes import wintypes
    k = ctypes.windll.kernel32
    k.CreateJobObjectW.restype = wintypes.HANDLE
    if _kill_job is None:
        class IO(ctypes.Structure):
            _fields_ = [(n, ctypes.c_ulonglong) for n in ("r", "w", "o", "rb", "wb", "ob")]

        class BASIC(ctypes.Structure):
            _fields_ = [("PerProcessUserTimeLimit", ctypes.c_longlong), ("PerJobUserTimeLimit", ctypes.c_longlong),
                        ("LimitFlags", wintypes.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
                        ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wintypes.DWORD),
                        ("Affinity", ctypes.c_size_t), ("PriorityClass", wintypes.DWORD),
                        ("SchedulingClass", wintypes.DWORD)]

        class EXT(ctypes.Structure):
            _fields_ = [("Basic", BASIC), ("Io", IO), ("ProcessMemoryLimit", ctypes.c_size_t),
                        ("JobMemoryLimit", ctypes.c_size_t), ("PeakProcessMemoryUsed", ctypes.c_size_t),
                        ("PeakJobMemoryUsed", ctypes.c_size_t)]

        job = k.CreateJobObjectW(None, None)
        info = EXT()
        info.Basic.LimitFlags = 0x2000                       # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not job or not k.SetInformationJobObject(wintypes.HANDLE(job), 9, ctypes.byref(info), ctypes.sizeof(info)):
            return
        _kill_job = job
    k.AssignProcessToJobObject(wintypes.HANDLE(_kill_job), wintypes.HANDLE(int(proc._handle)))


def show_screen_frame(monitor: int = 0):
    """Красная рамка по краю снимаемого монитора (в запись не попадает). Возвращает процесс или None."""
    if not IS_WIN:
        return None
    mons = screen_monitors()
    m = mons[monitor] if 0 <= monitor < len(mons) else (mons[0] if mons else None)
    if not m:
        return None
    try:
        p = subprocess.Popen([gui_python(), str(Path(__file__).with_name("frame_overlay.py")),
                              str(m["x"]), str(m["y"]), str(m["w"]), str(m["h"])],
                             stdin=subprocess.PIPE, **HIDDEN)
    except OSError:
        return None
    kill_with_parent(p)
    return p


def hide_screen_frame(p) -> None:
    if not p:
        return
    try:
        p.stdin.close()                  # рамка ждёт конца трубы и закрывается сама
        p.wait(timeout=3)
    except (OSError, subprocess.TimeoutExpired):
        p.kill()


_locks = []


def single_instance(path: Path) -> bool:
    """Только один процесс с этим замком: True — замок наш (держим до выхода), False — уже занят.
    Замок держит система: если процесс упал, он снимается сам, «зависших» замков не бывает."""
    f = open(path, "a+b")
    try:
        if IS_WIN:
            import msvcrt
            f.seek(0)
            msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        f.close()
        return False
    _locks.append(f)
    return True
