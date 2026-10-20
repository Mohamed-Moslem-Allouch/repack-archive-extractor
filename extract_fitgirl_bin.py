import os
import sys
import time
import shutil
import ctypes
import subprocess
import tempfile
import re

# 1. 32-bit Architecture Guard
# unarc.dll is a 32-bit native library; if running on 64-bit Python, auto-delegate to 32-bit
if sys.maxsize > 2**32:
    py_bin = shutil.which("py")
    if py_bin:
        try:
            res = subprocess.run([py_bin, "-3-32", "-c", "import sys; sys.exit(0 if sys.maxsize <= 2**32 else 1)"], capture_output=True)
            if res.returncode == 0:
                sys.exit(subprocess.call([py_bin, "-3-32", os.path.abspath(__file__)] + sys.argv[1:]))
        except Exception:
            pass

# 2. Maximum CPU & Threading Priority
try:
    # Set Windows Process Priority to HIGH_PRIORITY_CLASS (0x00000080)
    # Child processes (cls-lolz_x64, cls-srep_x64, xtool, etc.) inherit this priority
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x00000080)
except Exception:
    pass

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

def format_bytes(b):
    if b >= 1024 * 1024 * 1024:
        return f"{b / (1024**3):.2f} GB"
    return f"{b / (1024**2):.1f} MB"

def optimize_configs(toolchain_dir, output_dir, cores):
    """
    Tuning arc.ini and CLS.ini to utilize 100% of all CPU cores/threads,
    remove RAM allocation caps, and enlarge I/O pipe buffers.
    """
    # Optimize CLS.ini / cls.ini
    for ininame in ["cls.ini", "CLS.ini"]:
        p = os.path.join(toolchain_dir, ininame)
        if os.path.isfile(p):
            try:
                with open(p, "r", encoding="latin1") as f:
                    c = f.read()
                c = c.replace("{app}", output_dir)
                # Maximize thread usage across all engines
                c = re.sub(r"MaxThreadsUsage=\d+%", "MaxThreadsUsage=100%", c)
                c = re.sub(r"MaxMemoryUsage=\d+%", "MaxMemoryUsage=100%", c)
                c = re.sub(r"Memory=\d+.*", "Memory=100%", c)
                c = re.sub(r"ldmfMaxMemoryUsage=\d+.*", "ldmfMaxMemoryUsage=100%", c)
                # Optimize pipe buffer sizes for faster throughput
                c = re.sub(r"transfer_ReadBufSize=\d+\w*", "transfer_ReadBufSize=4m", c)
                c = re.sub(r"transfer_WriteBufSize=\d+\w*", "transfer_WriteBufSize=4m", c)
                with open(p, "w", encoding="latin1") as f:
                    f.write(c)
            except Exception:
                pass

    # Optimize arc.ini
    for ininame in ["arc.ini", "ARC.ini"]:
        p = os.path.join(toolchain_dir, ininame)
        if os.path.isfile(p):
            try:
                with open(p, "r", encoding="latin1") as f:
                    a = f.read()
                a = a.replace("{app}", output_dir)
                # Set all external compressor threads to 100%
                a = re.sub(r"-t\d+p", "-t100p", a)
                a = re.sub(r":t\d+p", ":t100p", a)
                a = re.sub(r"-t[1-9]\b", f"-t{cores}", a)
                if "[FreeArc]" not in a:
                    a = f"[FreeArc]\nthreads = {cores}\n\n" + a
                with open(p, "w", encoding="latin1") as f:
                    f.write(a)
            except Exception:
                pass

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

    print("=================================================================")
    print("        Repack Archive Extractor (FitGirl / DODI)")
    print("=================================================================")
    print(f"[*] Installer : {os.path.basename(setup_exe)}")
    print(f"[*] Archive   : {os.path.basename(archive_file)}")
    print(f"[*] Output    : {output_dir}")
    print(f"[*] Hardware  : {cores} Cores/Threads | Uncapped RAM | High Priority")
    print("=================================================================")
    print("[*] Unpacking installer codecs (innoextract)...", flush=True)

    start_time = time.time()

    try:
        # Step 1: Extract setup.exe internal helper files
        cmd = [innoextract, "-e", "-s", "-d", temp_dir, setup_exe]
        subprocess.run(cmd, check=True)

        toolchain_dir = os.path.join(temp_dir, "tmp")
        if not os.path.isdir(toolchain_dir):
            toolchain_dir = temp_dir

        unarc_dll = os.path.join(toolchain_dir, "unarc.dll")
        arc_ini = os.path.join(toolchain_dir, "arc.ini")

        if not os.path.isfile(unarc_dll):
            print("[!] Error: unarc.dll was not found inside the installer.")
            return False

        # Step 2: Configure decompression paths & apply hardware maximum tuning
        optimize_configs(toolchain_dir, output_dir, cores)

        # Step 3: Patch binaries from Global\ to Local\ IPC (bypasses Administrator requirement)
        for f in os.listdir(toolchain_dir):
            p = os.path.join(toolchain_dir, f)
            if os.path.isfile(p):
                try:
                    with open(p, "rb") as fp:
                        data = fp.read()
                    if b"Global\\\x00" in data:
                        patched = data.replace(b"Global\\\x00", b"Local\\\x00\x00")
                        with open(p, "wb") as fp:
                            fp.write(patched)
                except Exception:
                    pass

        # Step 4: Decompress with real-time CMD progress
        print("[*] Extracting files (Multithreaded Acceleration Active)...\n", flush=True)
        os.environ["PATH"] = toolchain_dir + ";" + os.environ.get("PATH", "")
        os.chdir(toolchain_dir)

        unarc = ctypes.cdll.LoadLibrary(unarc_dll)
        CALLBACK_TYPE = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_int, ctypes.c_char_p)

        file_size_mb = max(1, os.path.getsize(archive_file) // (1024 * 1024))
        stats = {
            "total_mb": file_size_mb,
            "read_mb": 0,
            "percent": 0,
            "file_count": 0,
            "current_file": ""
        }

        def unarc_callback(what, int1, int2, str_arg):
            if what == b"total":
                if int1 > 0:
                    stats["total_mb"] = int1
            elif what == b"read":
                stats["read_mb"] = int1
                tot = stats["total_mb"]
                if int2 > 0:
                    tot = int2
                    stats["total_mb"] = tot
                pct = min(100, int((int1 / max(1, tot)) * 100))
                stats["percent"] = pct
                bar = draw_bar(pct, 26)
                sys.stdout.write(f"\r  [{bar}] {pct:3d}% ({int1} MB / {tot} MB)")
                sys.stdout.flush()
            elif what == b"filename":
                fname = str_arg.decode("latin1", "ignore").strip()
                if fname:
                    stats["current_file"] = fname
                    stats["file_count"] += 1
                    bar = draw_bar(stats["percent"], 26)
                    # Clear progress line, print the file, then re-render bar
                    sys.stdout.write(f"\r{' ' * 78}\r")
                    print(f"  [{stats['percent']:3d}%] -> {fname}")
                    sys.stdout.write(f"  [{bar}] {stats['percent']:3d}% ({stats['read_mb']} MB / {stats['total_mb']} MB)")
                    sys.stdout.flush()
            elif what == b"error":
                err = str_arg.decode("latin1", "ignore").strip()
                print(f"\n  [!] Extraction Error: {err}")
            return 0

        cb = CALLBACK_TYPE(unarc_callback)
        dest_arg = ("-dp" + output_dir).encode("latin1")
        cfg_arg = ("-cfg" + arc_ini).encode("latin1")
        archive_arg = archive_file.encode("latin1")

        result = unarc.FreeArcExtract(
            cb,
            b"x",
            b"-o+",
            dest_arg,
            cfg_arg,
            b"--noarcext",
            b"--",
            archive_arg,
            None
        )

        elapsed = max(0.1, time.time() - start_time)
        sys.stdout.write(f"\r{' ' * 78}\r")
        bar = draw_bar(100, 26)
        print(f"  [{bar}] 100% ({stats['total_mb']} MB / {stats['total_mb']} MB)")

        if result == 0:
            speed_mb = stats['total_mb'] / elapsed
            print("\n=================================================================")
            print(f"[+] Extraction Complete! ({elapsed:.1f}s, ~{speed_mb:.1f} MB/s)")
            print(f"[*] Files Extracted : {stats['file_count']}")
            print(f"[*] Target Location : {output_dir}")
            print("=================================================================")
            return True
        else:
            print(f"\n[!] Extraction finished with exit code: {result}")
            return False

    finally:
        os.chdir(os.path.expanduser("~"))
        shutil.rmtree(temp_dir, ignore_errors=True)

def main():
    if len(sys.argv) == 2:
        # Drag & Drop onto script: archive path provided
        archive_path = os.path.abspath(sys.argv[1])
        if os.path.isfile(archive_path):
            folder = os.path.dirname(archive_path)
            base = os.path.splitext(os.path.basename(archive_path))[0]
            out_dir = os.path.join(folder, f"{base}_Extracted")

            # Check for setup.exe or Setup.exe in same folder
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

    # No arguments: prompt directly in console
    print("=================================================================")
    print("        Repack Archive Extractor (FitGirl / DODI)")
    print("=================================================================\n")
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
