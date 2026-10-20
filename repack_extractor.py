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

def run_extraction(setup_exe, archive_file, output_dir, log_func=print):
    setup_exe = os.path.abspath(setup_exe)
    archive_file = os.path.abspath(archive_file)
    output_dir = os.path.abspath(output_dir)

    if not os.path.isfile(setup_exe):
        log_func(f"[!] Error: setup.exe not found at:\n    {setup_exe}")
        return False

    if not os.path.isfile(archive_file):
        log_func(f"[!] Error: Archive file not found at:\n    {archive_file}")
        return False

    innoextract = find_innoextract()
    if not innoextract:
        log_func("[!] Error: innoextract is not installed.\n    Run: winget install dscharrer.innoextract")
        return False

    os.makedirs(output_dir, exist_ok=True)
    temp_dir = tempfile.mkdtemp(prefix="fg_extractor_")
    log_func(f"[*] Analyzing installer: {os.path.basename(setup_exe)}...")

    try:
        # Step 1: Extract setup.exe internal helper tools
        cmd = [innoextract, "-e", "-s", "-d", temp_dir, setup_exe]
        subprocess.run(cmd, check=True)

        toolchain_dir = os.path.join(temp_dir, "tmp")
        if not os.path.isdir(toolchain_dir):
            toolchain_dir = temp_dir

        unarc_dll = os.path.join(toolchain_dir, "unarc.dll")
        arc_ini = os.path.join(toolchain_dir, "arc.ini")

        if not os.path.isfile(unarc_dll):
            log_func("[!] Error: unarc.dll was not found inside setup.exe.")
            return False

        # Step 2: Replace {app} with output directory in configuration files
        log_func("[*] Configuring decompression blueprints...")
        for ininame in ["CLS.ini", "arc.ini"]:
            p = os.path.join(toolchain_dir, ininame)
            if os.path.exists(p):
                with open(p, "r", encoding="latin1") as f:
                    content = f.read()
                content = content.replace("{app}", output_dir)
                with open(p, "w", encoding="latin1") as f:
                    f.write(content)

        # Step 3: Patch helper tools from Global\ to Local\ IPC (bypasses Administrator requirement)
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

        # Step 4: Load unarc.dll and extract
        log_func(f"[*] Extracting: {os.path.basename(archive_file)}")
        log_func(f"[*] Target Directory: {output_dir}")
        os.environ["PATH"] = toolchain_dir + ";" + os.environ.get("PATH", "")
        os.chdir(toolchain_dir)

        unarc = ctypes.cdll.LoadLibrary(unarc_dll)
        CALLBACK_TYPE = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_int, ctypes.c_char_p)

        def cb_handler(what, int1, int2, str_arg):
            if what == b"filename":
                fname = str_arg.decode("latin1", "ignore")
                log_func(f"  -> {fname}")
            elif what == b"error":
                err = str_arg.decode("latin1", "ignore")
                log_func(f"  [!] Error: {err}")
            return 0

        cb = CALLBACK_TYPE(cb_handler)
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

        if result == 0:
            log_func("[+] Extraction finished successfully!")
            return True
        else:
            log_func(f"[!] Extraction finished with exit code: {result}")
            return False

    finally:
        os.chdir(os.path.expanduser("~"))
        shutil.rmtree(temp_dir, ignore_errors=True)

class ExtractorGUI(tk.Tk):
    def __init__(self, initial_archive=None):
        super().__init__()
        self.title("Repack Archive Extractor (FitGirl / DODI)")
        self.geometry("680x520")
        self.minsize(580, 420)

        # Style
        style = ttk.Style(self)
        style.theme_use("clam")

        main_frame = ttk.Frame(self, padding=16)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Archive Selection
        ttk.Label(main_frame, text="Archive File (.bin / .doi):", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 2))
        self.archive_var = tk.StringVar(value=initial_archive or "")
        self.archive_entry = ttk.Entry(main_frame, textvariable=self.archive_var, width=60)
        self.archive_entry.grid(row=1, column=0, sticky="ew", padx=(0, 8), pady=(0, 10))
        ttk.Button(main_frame, text="Browse...", command=self.browse_archive).grid(row=1, column=1, pady=(0, 10))

        # Setup Selection
        ttk.Label(main_frame, text="Installer (setup.exe):", font=("Segoe UI", 9, "bold")).grid(row=2, column=0, sticky="w", pady=(0, 2))
        self.setup_var = tk.StringVar()
        self.setup_entry = ttk.Entry(main_frame, textvariable=self.setup_var, width=60)
        self.setup_entry.grid(row=3, column=0, sticky="ew", padx=(0, 8), pady=(0, 10))
        ttk.Button(main_frame, text="Browse...", command=self.browse_setup).grid(row=3, column=1, pady=(0, 10))

        # Output Directory
        ttk.Label(main_frame, text="Destination Folder:", font=("Segoe UI", 9, "bold")).grid(row=4, column=0, sticky="w", pady=(0, 2))
        self.output_var = tk.StringVar()
        self.output_entry = ttk.Entry(main_frame, textvariable=self.output_var, width=60)
        self.output_entry.grid(row=5, column=0, sticky="ew", padx=(0, 8), pady=(0, 14))
        ttk.Button(main_frame, text="Browse...", command=self.browse_output).grid(row=5, column=1, pady=(0, 14))

        main_frame.columnconfigure(0, weight=1)

        # Auto-detect if archive is provided
        if initial_archive:
            self.auto_fill(initial_archive)

        # Extract Button
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=6, column=0, columnspan=2, pady=(0, 12), sticky="ew")

        self.extract_btn = ttk.Button(btn_frame, text="▶ Extract Archive", command=self.start_extraction)
        self.extract_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.open_folder_btn = ttk.Button(btn_frame, text="Open Output Folder", command=self.open_folder, state=tk.DISABLED)
        self.open_folder_btn.pack(side=tk.LEFT)

        self.status_label = ttk.Label(btn_frame, text="Ready", font=("Segoe UI", 9))
        self.status_label.pack(side=tk.RIGHT)

        # Log Output Box
        ttk.Label(main_frame, text="Extraction Log:", font=("Segoe UI", 9, "bold")).grid(row=7, column=0, sticky="w", pady=(0, 4))
        self.log_box = tk.Text(main_frame, height=12, wrap="word", bg="#1e1e1e", fg="#e0e0e0", font=("Consolas", 9))
        self.log_box.grid(row=8, column=0, columnspan=2, sticky="nsew")

        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=self.log_box.yview)
        scrollbar.grid(row=8, column=2, sticky="ns")
        self.log_box.configure(yscrollcommand=scrollbar.set)

        main_frame.rowconfigure(8, weight=1)

    def log(self, message):
        self.log_box.insert(tk.END, message + "\n")
        self.log_box.see(tk.END)

    def auto_fill(self, archive_path):
        if not archive_path:
            return
        archive_path = os.path.abspath(archive_path)
        folder = os.path.dirname(archive_path)
        base = os.path.splitext(os.path.basename(archive_path))[0]

        setup_path = os.path.join(folder, "setup.exe")
        if os.path.isfile(setup_path) and not self.setup_var.get():
            self.setup_var.set(setup_path)

        if not self.output_var.get():
            self.output_var.set(os.path.join(folder, f"{base}_Extracted"))

    def browse_archive(self):
        filename = filedialog.askopenfilename(
            title="Select Repack Archive",
            filetypes=[("Repack Archives (*.bin;*.doi)", "*.bin;*.doi"), ("All Files", "*.*")]
        )
        if filename:
            self.archive_var.set(filename)
            self.auto_fill(filename)

    def browse_setup(self):
        filename = filedialog.askopenfilename(
            title="Select setup.exe",
            filetypes=[("Setup Executable (setup.exe)", "*.exe"), ("All Files", "*.*")]
        )
        if filename:
            self.setup_var.set(filename)

    def browse_output(self):
        folder = filedialog.askdirectory(title="Select Destination Folder")
        if folder:
            self.output_var.set(folder)

    def open_folder(self):
        out_dir = self.output_var.get().strip()
        if os.path.isdir(out_dir):
            os.startfile(out_dir)

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
            messagebox.showerror("Error", "Please select an output folder.")
            return

        self.extract_btn.config(state=tk.DISABLED)
        self.status_label.config(text="Extracting...")
        self.log_box.delete("1.0", tk.END)

        def worker():
            success = run_extraction(setup, archive, out, log_func=self.log)
            self.extract_btn.config(state=tk.NORMAL)
            if success:
                self.status_label.config(text="Completed Successfully!")
                self.open_folder_btn.config(state=tk.NORMAL)
                messagebox.showinfo("Success", f"Extraction completed!\n\nFolder:\n{out}")
            else:
                self.status_label.config(text="Extraction Failed")
                messagebox.showerror("Failed", "Extraction encountered an error. Check log output.")

        threading.Thread(target=worker, daemon=True).start()

def main():
    # Drag and Drop / CLI Mode
    if len(sys.argv) == 2:
        # User dragged a single file onto the python script or gave 1 arg
        archive_path = os.path.abspath(sys.argv[1])
        if os.path.isfile(archive_path):
            folder = os.path.dirname(archive_path)
            setup_path = os.path.join(folder, "setup.exe")
            base = os.path.splitext(os.path.basename(archive_path))[0]
            out_path = os.path.join(folder, f"{base}_Extracted")

            if os.path.isfile(setup_path):
                print("=======================================================")
                print("   Repack Archive Extractor (CLI / Drag & Drop)")
                print("=======================================================")
                run_extraction(setup_path, archive_path, out_path)
                input("\nPress Enter to exit...")
                return
            else:
                # setup.exe not in same folder, launch GUI with archive pre-filled
                app = ExtractorGUI(initial_archive=archive_path)
                app.mainloop()
                return

    elif len(sys.argv) >= 4:
        # Full CLI mode: py script.py setup.exe archive.bin output_dir
        setup_p = sys.argv[1]
        arch_p = sys.argv[2]
        out_p = sys.argv[3]
        run_extraction(setup_p, arch_p, out_p)
        return

    # No arguments: launch full interactive GUI window
    app = ExtractorGUI()
    app.mainloop()

if __name__ == "__main__":
    main()
