import os
import sys
import shutil
import ctypes
import subprocess
import tempfile
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

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

def format_progress_bar(percent, width=30):
    filled = int(width * percent / 100)
    bar = "█" * filled + "░" * (width - filled)
    return bar

def run_extraction(setup_exe, archive_file, output_dir, progress_callback=None, log_callback=None):
    setup_exe = os.path.abspath(setup_exe)
    archive_file = os.path.abspath(archive_file)
    output_dir = os.path.abspath(output_dir)

    def log(msg):
        if log_callback:
            log_callback(msg)
        else:
            print(msg, flush=True)

    if not os.path.isfile(setup_exe):
        log(f"[!] Error: setup.exe not found at: {setup_exe}")
        return False

    if not os.path.isfile(archive_file):
        log(f"[!] Error: Archive file not found at: {archive_file}")
        return False

    innoextract = find_innoextract()
    if not innoextract:
        log("[!] innoextract.exe was not found. Please install it with:")
        log("    winget install dscharrer.innoextract")
        return False

    os.makedirs(output_dir, exist_ok=True)
    temp_dir = tempfile.mkdtemp(prefix="repack_ext_")
    log(f"[*] Extracting installer toolchain from {os.path.basename(setup_exe)}...")

    try:
        # Step 1: Extract setup.exe internal helper files
        cmd = [innoextract, "-e", "-s", "-d", temp_dir, setup_exe]
        subprocess.run(cmd, check=True)

        toolchain_dir = os.path.join(temp_dir, "tmp")
        if not os.path.isdir(toolchain_dir):
            toolchain_dir = temp_dir

        unarc_dll = os.path.join(toolchain_dir, "unarc.dll")
        arc_ini = os.path.join(toolchain_dir, "arc.ini")
        cls_ini = os.path.join(toolchain_dir, "CLS.ini")

        if not os.path.isfile(unarc_dll):
            log("[!] Error: unarc.dll was not found inside the installer.")
            return False

        # Step 2: Configure decompression paths
        log("[*] Configuring decompression settings...")
        for ininame in ["CLS.ini", "arc.ini"]:
            p = os.path.join(toolchain_dir, ininame)
            if os.path.exists(p):
                with open(p, "r", encoding="latin1") as f:
                    content = f.read()
                content = content.replace("{app}", output_dir)
                with open(p, "w", encoding="latin1") as f:
                    f.write(content)

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

        # Step 4: Decompress with real-time progress and filename tracking
        log(f"[*] Starting extraction: {os.path.basename(archive_file)}")
        log(f"[*] Output Directory: {output_dir}")
        os.environ["PATH"] = toolchain_dir + ";" + os.environ.get("PATH", "")
        os.chdir(toolchain_dir)

        unarc = ctypes.cdll.LoadLibrary(unarc_dll)
        CALLBACK_TYPE = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_int, ctypes.c_char_p)

        stats = {
            "total_bytes": 0,
            "total_mb": max(1, os.path.getsize(archive_file) // (1024 * 1024)),
            "read_mb": 0,
            "percent": 0,
            "current_file": "",
            "file_count": 0
        }

        def unarc_callback(what, int1, int2, str_arg):
            if what == b"total":
                if int1 > 0:
                    stats["total_mb"] = int1
                if int2 > 0:
                    stats["total_bytes"] = int2
            elif what == b"read":
                stats["read_mb"] = int1
                tot = stats["total_mb"]
                if int2 > 0:
                    tot = int2
                    stats["total_mb"] = tot
                pct = min(100, int((int1 / max(1, tot)) * 100))
                stats["percent"] = pct
                if progress_callback:
                    progress_callback(pct, stats["read_mb"], stats["total_mb"], stats["current_file"])
                elif not log_callback:
                    # Terminal CLI progress display
                    bar = format_progress_bar(pct, 25)
                    fname = stats["current_file"][-40:] if len(stats["current_file"]) > 40 else stats["current_file"]
                    print(f"\r  [{bar}] {pct:3d}% | {int1}MB / {tot}MB | {fname}", end="", flush=True)
            elif what == b"filename":
                fname = str_arg.decode("latin1", "ignore")
                if fname:
                    stats["current_file"] = fname
                    stats["file_count"] += 1
                    log(f"  [{stats['percent']:3d}%] -> {fname}")
                    if progress_callback:
                        progress_callback(stats["percent"], stats["read_mb"], stats["total_mb"], fname)
            elif what == b"error":
                err = str_arg.decode("latin1", "ignore")
                log(f"\n  [!] Error: {err}")
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

        if not log_callback:
            print() # new line after CLI progress bar

        if result == 0:
            if progress_callback:
                progress_callback(100, stats["total_mb"], stats["total_mb"], "Completed!")
            log("[+] Extraction completed successfully!")
            return True
        else:
            log(f"[!] Extraction finished with exit code: {result}")
            return False

    finally:
        os.chdir(os.path.expanduser("~"))
        shutil.rmtree(temp_dir, ignore_errors=True)

class ExtractionWindow(tk.Tk):
    def __init__(self, archive_file="", setup_exe="", output_dir=""):
        super().__init__()
        self.title("Repack Archive Extractor (FitGirl / DODI)")
        self.geometry("720x580")
        self.minsize(620, 480)

        style = ttk.Style(self)
        style.theme_use("clam")

        main_frame = ttk.Frame(self, padding=16)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Archive Selection
        ttk.Label(main_frame, text="Archive File (.bin / .doi):", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 2))
        self.archive_var = tk.StringVar(value=archive_file)
        self.archive_entry = ttk.Entry(main_frame, textvariable=self.archive_var, width=65)
        self.archive_entry.grid(row=1, column=0, sticky="ew", padx=(0, 8), pady=(0, 8))
        ttk.Button(main_frame, text="Browse...", command=self.browse_archive).grid(row=1, column=1, pady=(0, 8))

        # Setup Selection
        ttk.Label(main_frame, text="Installer (setup.exe):", font=("Segoe UI", 9, "bold")).grid(row=2, column=0, sticky="w", pady=(0, 2))
        self.setup_var = tk.StringVar(value=setup_exe)
        self.setup_entry = ttk.Entry(main_frame, textvariable=self.setup_var, width=65)
        self.setup_entry.grid(row=3, column=0, sticky="ew", padx=(0, 8), pady=(0, 8))
        ttk.Button(main_frame, text="Browse...", command=self.browse_setup).grid(row=3, column=1, pady=(0, 8))

        # Destination Folder
        ttk.Label(main_frame, text="Destination Folder:", font=("Segoe UI", 9, "bold")).grid(row=4, column=0, sticky="w", pady=(0, 2))
        self.output_var = tk.StringVar(value=output_dir)
        self.output_entry = ttk.Entry(main_frame, textvariable=self.output_var, width=65)
        self.output_entry.grid(row=5, column=0, sticky="ew", padx=(0, 8), pady=(0, 12))
        ttk.Button(main_frame, text="Browse...", command=self.browse_output).grid(row=5, column=1, pady=(0, 12))

        main_frame.columnconfigure(0, weight=1)

        # Progress Section
        progress_frame = ttk.LabelFrame(main_frame, text=" Progress ", padding=10)
        progress_frame.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(0, 12))

        self.progress_bar = ttk.Progressbar(progress_frame, orient="horizontal", mode="determinate", length=600)
        self.progress_bar.pack(fill=tk.X, pady=(0, 6))

        info_box = ttk.Frame(progress_frame)
        info_box.pack(fill=tk.X)

        self.percent_label = ttk.Label(info_box, text="0%", font=("Segoe UI", 10, "bold"), foreground="#0078d4")
        self.percent_label.pack(side=tk.LEFT)

        self.current_file_label = ttk.Label(info_box, text="Ready", font=("Segoe UI", 9), foreground="#555555")
        self.current_file_label.pack(side=tk.RIGHT)

        # Action Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=7, column=0, columnspan=2, pady=(0, 10), sticky="ew")

        self.extract_btn = ttk.Button(btn_frame, text="▶ Start Extraction", command=self.start_extraction)
        self.extract_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.open_folder_btn = ttk.Button(btn_frame, text="Open Output Folder", command=self.open_folder, state=tk.DISABLED)
        self.open_folder_btn.pack(side=tk.LEFT)

        # Real-time Files Log
        ttk.Label(main_frame, text="Extracted Files (Live Stream):", font=("Segoe UI", 9, "bold")).grid(row=8, column=0, sticky="w", pady=(0, 4))
        self.log_box = tk.Text(main_frame, height=10, wrap="word", bg="#1e1e1e", fg="#e0e0e0", font=("Consolas", 9))
        self.log_box.grid(row=9, column=0, columnspan=2, sticky="nsew")

        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=self.log_box.yview)
        scrollbar.grid(row=9, column=2, sticky="ns")
        self.log_box.configure(yscrollcommand=scrollbar.set)
        main_frame.rowconfigure(9, weight=1)

        if archive_file:
            self.auto_fill(archive_file)

    def log(self, text):
        self.after(0, self._append_log, text)

    def _append_log(self, text):
        self.log_box.insert(tk.END, text + "\n")
        self.log_box.see(tk.END)

    def update_progress(self, percent, read_mb, total_mb, current_file):
        self.after(0, self._set_progress, percent, read_mb, total_mb, current_file)

    def _set_progress(self, percent, read_mb, total_mb, current_file):
        self.progress_bar["value"] = percent
        self.percent_label["text"] = f"{percent}%  ({read_mb} MB / {total_mb} MB)"
        short_file = current_file
        if len(short_file) > 55:
            short_file = "..." + short_file[-52:]
        self.current_file_label["text"] = short_file

    def auto_fill(self, archive_path):
        if not archive_path:
            return
        archive_path = os.path.abspath(archive_path)
        folder = os.path.dirname(archive_path)
        base = os.path.splitext(os.path.basename(archive_path))[0]

        setup_path = os.path.join(folder, "setup.exe")
        if not os.path.isfile(setup_path):
            setup_path = os.path.join(folder, "Setup.exe")
        if os.path.isfile(setup_path) and not self.setup_var.get():
            self.setup_var.set(setup_path)

        if not self.output_var.get():
            self.output_var.set(os.path.join(folder, f"{base}_Extracted"))

    def browse_archive(self):
        f = filedialog.askopenfilename(
            title="Select Archive",
            filetypes=[("Repack Archives (*.bin;*.doi)", "*.bin;*.doi"), ("All Files", "*.*")]
        )
        if f:
            self.archive_var.set(f)
            self.auto_fill(f)

    def browse_setup(self):
        f = filedialog.askopenfilename(
            title="Select setup.exe",
            filetypes=[("Setup Executable (*.exe)", "*.exe"), ("All Files", "*.*")]
        )
        if f:
            self.setup_var.set(f)

    def browse_output(self):
        f = filedialog.askdirectory(title="Select Destination Folder")
        if f:
            self.output_var.set(f)

    def open_folder(self):
        d = self.output_var.get().strip()
        if os.path.isdir(d):
            os.startfile(d)

    def start_extraction(self):
        archive = self.archive_var.get().strip()
        setup = self.setup_var.get().strip()
        out = self.output_var.get().strip()

        if not archive or not os.path.isfile(archive):
            messagebox.showerror("Error", "Please select a valid archive file (.bin or .doi).")
            return
        if not setup or not os.path.isfile(setup):
            messagebox.showerror("Error", "Please select a valid setup.exe.")
            return
        if not out:
            messagebox.showerror("Error", "Please select an output destination folder.")
            return

        self.extract_btn.config(state=tk.DISABLED)
        self.progress_bar["value"] = 0
        self.percent_label["text"] = "0%"
        self.current_file_label["text"] = "Initializing..."
        self.log_box.delete("1.0", tk.END)

        def worker():
            success = run_extraction(
                setup,
                archive,
                out,
                progress_callback=self.update_progress,
                log_callback=self.log
            )
            self.after(0, self._on_finish, success, out)

        threading.Thread(target=worker, daemon=True).start()

    def _on_finish(self, success, out):
        self.extract_btn.config(state=tk.NORMAL)
        if success:
            self.open_folder_btn.config(state=tk.NORMAL)
            self.current_file_label["text"] = "Done!"
            messagebox.showinfo("Success", f"Extraction completed successfully!\n\nLocation:\n{out}")
        else:
            self.current_file_label["text"] = "Extraction Failed"
            messagebox.showerror("Error", "Decompression failed. Please check the log messages.")

def main():
    # If launched with arguments (Drag & Drop or CLI)
    if len(sys.argv) == 2:
        target_file = os.path.abspath(sys.argv[1])
        if os.path.isfile(target_file):
            folder = os.path.dirname(target_file)
            base = os.path.splitext(os.path.basename(target_file))[0]
            out_dir = os.path.join(folder, f"{base}_Extracted")

            # Look for setup.exe or Setup.exe
            setup_exe = os.path.join(folder, "setup.exe")
            if not os.path.isfile(setup_exe):
                setup_exe = os.path.join(folder, "Setup.exe")

            # Open graphical window with progress bar and pre-loaded paths
            app = ExtractionWindow(archive_file=target_file, setup_exe=setup_exe if os.path.isfile(setup_exe) else "", output_dir=out_dir)
            # If setup.exe was found, auto-start extraction!
            if os.path.isfile(setup_exe):
                app.after(500, app.start_extraction)
            app.mainloop()
            return

    elif len(sys.argv) >= 4:
        setup_exe = sys.argv[1]
        archive_file = sys.argv[2]
        output_dir = sys.argv[3]
        run_extraction(setup_exe, archive_file, output_dir)
        return

    # No arguments: launch window
    app = ExtractionWindow()
    app.mainloop()

if __name__ == "__main__":
    main()
