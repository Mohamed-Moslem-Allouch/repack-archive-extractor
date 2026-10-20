import os
import sys
import time
import shutil
import ctypes
import subprocess
import tempfile
import re

# Set console encoding to UTF-8
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# =====================================================================
# WORKER MODE (Runs in background without console window: CREATE_NO_WINDOW)
# In this mode, child processes (precomp, mpz, lolz) have NO console,
# so they CANNOT print raw debug noise or interrupt the terminal.
# =====================================================================
def optimize_cls_ini(content, output_dir):
    content = content.replace("{app}", output_dir)
    lines = content.splitlines()
    out = []
    current_sec = ""
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            current_sec = stripped[1:-1].strip().lower()
            out.append(line)
            continue
        if "=" in line and not stripped.startswith(";") and not stripped.startswith("#"):
            k, v = line.split("=", 1)
            kc = k.strip()
            kl = kc.lower()
            if kl == "maxthreadsusage":
                out.append(f"{kc}=100%")
            elif kl == "maxmemoryusage":
                out.append(f"{kc}=100%")
            elif kl == "memory":
                if "precomp" in current_sec:
                    out.append(f"{kc}=2048")
                else:
                    out.append(f"{kc}=100%")
            elif kl == "ldmfmaxmemoryusage":
                out.append(f"{kc}=4096m")
            elif kl == "ldmfdeletetmp":
                out.append(f"{kc}=1")
            elif kl == "transfer_readbufsize":
                out.append(f"{kc}=8m")
            elif kl == "transfer_writebufsize":
                out.append(f"{kc}=8m")
            elif kl == "bufsize":
                if "srep" in current_sec:
                    out.append(f"{kc}=64m")
                else:
                    out.append(f"{kc}=16m")
            else:
                out.append(line)
        else:
            out.append(line)
    return "\n".join(out)

def optimize_arc_ini(content, output_dir, cores):
    content = content.replace("{app}", output_dir)
    content = re.sub(r"-t\d+p", "-t100p", content)
    content = re.sub(r":t\d+p", ":t100p", content)
    content = re.sub(r"-t[1-9]\b", f"-t{cores}", content)
    if "[FreeArc]" not in content:
        content = f"[FreeArc]\nthreads = {cores}\n\n" + content
    return content

def run_worker(setup_exe, archive_file, output_dir, toolchain_dir):
    cores = os.cpu_count() or 4
    arc_ini = os.path.join(toolchain_dir, "arc.ini")
    cls_ini = os.path.join(toolchain_dir, "CLS.ini")
    if not os.path.exists(cls_ini):
        cls_ini = os.path.join(toolchain_dir, "cls.ini")

    if os.path.exists(cls_ini):
        try:
            with open(cls_ini, "r", encoding="latin1") as f:
                c = f.read()
            with open(cls_ini, "w", encoding="latin1") as f:
                f.write(optimize_cls_ini(c, output_dir))
        except Exception:
            pass

    if os.path.exists(arc_ini):
        try:
            with open(arc_ini, "r", encoding="latin1") as f:
                a = f.read()
            with open(arc_ini, "w", encoding="latin1") as f:
                f.write(optimize_arc_ini(a, output_dir, cores))
        except Exception:
            pass

    for f in os.listdir(toolchain_dir):
        p = os.path.join(toolchain_dir, f)
        if os.path.isfile(p):
            try:
                with open(p, "rb") as fp:
                    d = fp.read()
                if b"Global\\\x00" in d:
                    with open(p, "wb") as fp:
                        fp.write(d.replace(b"Global\\\x00", b"Local\\\x00\x00"))
            except Exception:
                pass

    os.environ["PATH"] = toolchain_dir + ";" + os.environ.get("PATH", "")
    os.chdir(toolchain_dir)

    unarc = ctypes.cdll.LoadLibrary(os.path.join(toolchain_dir, "unarc.dll"))
    CALLBACK_TYPE = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_int, ctypes.c_char_p)

    def cb(what, i1, i2, s):
        if what == b"total":
            sys.stdout.write(f"TOTAL:{i1}\n")
            sys.stdout.flush()
        elif what == b"read":
            sys.stdout.write(f"READ:{i1}\n")
            sys.stdout.flush()
        elif what == b"filename":
            fn = s.decode("latin1", "ignore").strip()
            if fn:
                sys.stdout.write(f"FILE:{fn}\n")
                sys.stdout.flush()
        elif what == b"error":
            err = s.decode("latin1", "ignore").strip()
            sys.stdout.write(f"ERROR:{err}\n")
            sys.stdout.flush()
        return 0

    callback = CALLBACK_TYPE(cb)
    dest_arg = ("-dp" + output_dir).encode("latin1")
    cfg_arg = ("-cfg" + arc_ini).encode("latin1")
    archive_arg = archive_file.encode("latin1")

    res = unarc.FreeArcExtract(
        callback,
        b"x",
        b"-o+",
        dest_arg,
        cfg_arg,
        b"--noarcext",
        b"--",
        archive_arg,
        None
    )
    sys.stdout.write(f"RESULT:{res}\n")
    sys.stdout.flush()
    sys.exit(res)

# =====================================================================
# MAIN UI CONTROLLER
# Manages terminal rendering, live progress, and silent worker execution
# =====================================================================
def find_innoextract():
    cmd = shutil.which("innoextract")
    if cmd:
        return cmd
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    winget_dir = os.path.join(local_app_data, "Microsoft", "WinGet", "Packages")
    if os.path.exists(winget_dir):
        for root, _, files in os.walk(winget_dir):
            if "innoextract.exe" in files:
                return os.path.join(root, "innoextract.exe")
    return None

def draw_bar(percent, width=28):
    filled = int(width * percent / 100)
    return "█" * filled + "░" * (width - filled)

def format_size(bytes_val):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_val < 1024.0:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.1f} TB"

def extract_archive(setup_exe, archive_file, output_dir):
    setup_exe = os.path.abspath(setup_exe)
    archive_file = os.path.abspath(archive_file)
    output_dir = os.path.abspath(output_dir)

    if not os.path.isfile(setup_exe):
        print(f"\n[!] Error: setup.exe not found at:\n    {setup_exe}")
        return False

    if not os.path.isfile(archive_file):
        print(f"\n[!] Error: Archive file not found at:\n    {archive_file}")
        return False

    innoextract = find_innoextract()
    if not innoextract:
        print("\n[!] innoextract.exe was not found. Please install it with:")
        print("    winget install dscharrer.innoextract")
        return False

    cores = os.cpu_count() or 4
    os.makedirs(output_dir, exist_ok=True)
    temp_dir = tempfile.mkdtemp(prefix="repack_ext_")

    archive_size = os.path.getsize(archive_file)
    print("┌─────────────────────────────────────────────────────────────────┐")
    print("│            Repack Archive Extractor (FitGirl / DODI)            │")
    print("├─────────────────────────────────────────────────────────────────┤")
    print(f"│ Archive   : {os.path.basename(archive_file):<51} │")
    print(f"│ Size      : {format_size(archive_size):<51} │")
    print(f"│ Hardware  : {f'{cores} Cores/Threads | Max RAM | High Priority':<51} │")
    print(f"│ Output    : {output_dir:<51} │")
    print("└─────────────────────────────────────────────────────────────────┘")
    sys.stdout.write("[*] Unpacking installer codecs (innoextract)...")
    sys.stdout.flush()

    start_time = time.time()

    try:
        cmd = [innoextract, "-e", "-s", "-d", temp_dir, setup_exe]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        toolchain_dir = os.path.join(temp_dir, "tmp")
        if not os.path.isdir(toolchain_dir):
            toolchain_dir = temp_dir

        unarc_dll = os.path.join(toolchain_dir, "unarc.dll")
        if not os.path.isfile(unarc_dll):
            print("\n[!] Error: unarc.dll was not found inside the installer.")
            return False

        sys.stdout.write("\r[*] Extracting files (Max Hardware Acceleration Active)...\n\n")
        sys.stdout.flush()

        # Find 32-bit Python executable to run worker
        py_launcher = shutil.which("py")
        if py_launcher:
            worker_cmd = [py_launcher, "-3-32", "-u", os.path.abspath(__file__), "--worker", setup_exe, archive_file, output_dir, toolchain_dir]
        else:
            worker_cmd = [sys.executable, "-u", os.path.abspath(__file__), "--worker", setup_exe, archive_file, output_dir, toolchain_dir]

        # Launch worker in headless mode (CREATE_NO_WINDOW = 0x08000000)
        # This completely suppresses child process console output (mpz, precomp, lolz)
        CREATE_NO_WINDOW = 0x08000000
        proc = subprocess.Popen(
            worker_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=CREATE_NO_WINDOW,
            text=True,
            bufsize=1
        )

        total_mb = max(1, archive_size // (1024 * 1024))
        read_mb = 0
        file_count = 0
        current_pct = 0
        worker_rc = None

        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue
            if line.startswith("TOTAL:"):
                total_mb = max(1, int(line.split(":", 1)[1]))
            elif line.startswith("READ:"):
                read_mb = int(line.split(":", 1)[1])
                current_pct = min(100, int((read_mb / total_mb) * 100))
                bar = draw_bar(current_pct, 28)
                sys.stdout.write(f"\r  [{bar}] {current_pct:3d}% ({read_mb} MB / {total_mb} MB)")
                sys.stdout.flush()
            elif line.startswith("FILE:"):
                fname = line.split(":", 1)[1]
                file_count += 1
                bar = draw_bar(current_pct, 28)
                sys.stdout.write(f"\r{' ' * 78}\r")
                print(f"  [{current_pct:3d}%] [{file_count:>3d}] {fname}")
                sys.stdout.write(f"  [{bar}] {current_pct:3d}% ({read_mb} MB / {total_mb} MB)")
                sys.stdout.flush()
            elif line.startswith("ERROR:"):
                err = line.split(":", 1)[1]
                print(f"\n  [!] Error: {err}")
            elif line.startswith("RESULT:"):
                worker_rc = int(line.split(":", 1)[1])

        proc.wait()
        if worker_rc is None:
            worker_rc = proc.returncode

        elapsed = max(0.1, time.time() - start_time)
        sys.stdout.write(f"\r{' ' * 78}\r")
        bar = draw_bar(100, 28)
        print(f"  [{bar}] 100% ({total_mb} MB / {total_mb} MB)")

        if worker_rc == 0:
            speed_mb = total_mb / elapsed
            print("\n┌─────────────────────────────────────────────────────────────────┐")
            print(f"│ [+] Extraction Complete in {elapsed:.1f}s ({speed_mb:.1f} MB/s){' ' * max(0, 31 - len(f'{elapsed:.1f}s ({speed_mb:.1f} MB/s)'))} │")
            print(f"│ [*] Total Files Extracted : {file_count:<35} │")
            print(f"│ [*] Output Directory      : {output_dir:<35} │")
            print("└─────────────────────────────────────────────────────────────────┘")
            return True
        else:
            print(f"\n[!] Extraction finished with exit code: {worker_rc}")
            return False

    finally:
        os.chdir(os.path.expanduser("~"))
        shutil.rmtree(temp_dir, ignore_errors=True)

def main():
    # Check if called as internal worker
    if len(sys.argv) >= 6 and sys.argv[1] == "--worker":
        setup_exe = sys.argv[2]
        archive_file = sys.argv[3]
        output_dir = sys.argv[4]
        toolchain_dir = sys.argv[5]
        run_worker(setup_exe, archive_file, output_dir, toolchain_dir)
        return

    # Set High Process Priority for the controller and its worker
    try:
        ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x00000080)
    except Exception:
        pass

    if len(sys.argv) == 2:
        archive_path = os.path.abspath(sys.argv[1])
        if os.path.isfile(archive_path):
            folder = os.path.dirname(archive_path)
            base = os.path.splitext(os.path.basename(archive_path))[0]
            out_dir = os.path.join(folder, f"{base}_Extracted")

            setup_exe = os.path.join(folder, "setup.exe")
            if not os.path.isfile(setup_exe):
                setup_exe = os.path.join(folder, "Setup.exe")

            if not os.path.isfile(setup_exe):
                print(f"[?] setup.exe not found in: {folder}")
                setup_exe = input("Enter full path to setup.exe: ").strip(' "\'')

            extract_archive(setup_exe, archive_path, out_dir)
            return

    elif len(sys.argv) >= 4:
        setup_exe = sys.argv[1]
        archive_file = sys.argv[2]
        output_dir = sys.argv[3]
        extract_archive(setup_exe, archive_file, output_dir)
        return

    # No arguments: prompt in console
    print("┌─────────────────────────────────────────────────────────────────┐")
    print("│            Repack Archive Extractor (FitGirl / DODI)            │")
    print("└─────────────────────────────────────────────────────────────────┘\n")
    archive_file = input("Enter path to archive (.bin or .doi): ").strip(' "\'')
    if not archive_file:
        return

    folder = os.path.dirname(os.path.abspath(archive_file))
    base = os.path.splitext(os.path.basename(archive_file))[0]
    out_dir = os.path.join(folder, f"{base}_Extracted")

    setup_exe = os.path.join(folder, "setup.exe")
    if not os.path.isfile(setup_exe):
        setup_exe = os.path.join(folder, "Setup.exe")

    if not os.path.isfile(setup_exe):
        setup_exe = input("Enter path to setup.exe: ").strip(' "\'')

    extract_archive(setup_exe, archive_file, out_dir)

if __name__ == "__main__":
    main()
