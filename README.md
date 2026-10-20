# Repack Archive Extractor (FitGirl / DODI)

A high-performance command-line tool with a real-time console progress bar to extract selective and optional archives (`.bin` / `.doi` files) directly from **FitGirl** and **DODI** repacks without downloading or installing the full 30–70 GB base game.

---

## 🌟 Why Use This?

Repack installers usually lock components and force you to download the entire base game even if you only want:
* 🎵 Soundtracks (MP3 / FLAC)
* 🎨 Digital Artbooks (CBZ / PDF)
* 📖 Digital Comics & Strategy Guides (CBR / PDF)
* 🗣️ Selective Voice / Language Packs

This tool extracts the internal FreeArc and pre-compression codec plugins directly from the repack's `setup.exe` (~6 MB) and uses Python to decompress only your chosen `.bin` or `.doi` archive, **saving tens of gigabytes of download bandwidth and disk space**.

---

## ⚡ Maximum Performance & Headless Architecture

Repack installers typically throttle thread usage (to 75%) and cap memory consumption (e.g. `Memory=80%-512m` or 2GB limits) so background PCs don't freeze during installations. 

This tool unlocks your system's full hardware potential:
* 🚀 **100% CPU Multithreading:** Automatically detects all logical CPU cores and threads (`os.cpu_count()`), removing thread throttles across all decompression engines (`lolz`, `srep`, `xtool`, `pzlib`, `reflate`, `ztool`).
* 🧠 **Uncapped RAM Allocation:** Unleashes the 64-bit pre-compressor engines with 100% memory allocation, keeping decompression tables in ultra-fast system RAM.
* ⚡ **Optimized I/O Pipe Buffers:** Quadruples stream buffers (`transfer_ReadBufSize=8m` and `transfer_WriteBufSize=8m`) to eliminate I/O pipe bottlenecks and system call overhead.
* 🔇 **Silent Headless Sub-processes:** Decompression engines run inside a headless background worker (`CREATE_NO_WINDOW = 0x08000000`), completely muting sub-process console spam (`mpz`, `precomp`, `lolz` banners) and boosting execution speed by eliminating console I/O locks.
* 🎯 **Windows High-Priority Scheduling:** Sets the process priority class to `HIGH_PRIORITY_CLASS` (`0x00000080`), ensuring the Windows kernel dedicates maximum CPU cycles to the extraction pipeline.

---

## ✨ Features

* **Pure Command Prompt (CMD):** Clean terminal interface with zero popups or GUI bloat.
* **Live Console Progress Bar:** Shows real-time percentage and throughput:
  ```text
  ┌─────────────────────────────────────────────────────────────────┐
  │            Repack Archive Extractor (FitGirl / DODI)            │
  ├─────────────────────────────────────────────────────────────────┤
  │ Archive   : fg-optional-bonus-content.bin                       │
  │ Size      : 627.2 MB                                            │
  │ Hardware  : 16 Cores/Threads | Max RAM | High Priority          │
  │ Output    : ...\Bonus_Extracted                                 │
  └─────────────────────────────────────────────────────────────────┘
  [*] Unpacking installer codecs (innoextract)...
  [*] Extracting files (Max Hardware Acceleration Active)...

    [  0%] [  1] Bonus Content
    [  0%] [  2] Bonus Content\Soundtracks
    [ 72%] [ 13] Bonus Content\The Art of The Last of Us (Digital).cbz
    [ 98%] [ 85] Bonus Content\Soundtracks\MP3\25. Left Behind.mp3
    [████████████████████████████] 100% (627 MB / 627 MB)

  ┌─────────────────────────────────────────────────────────────────┐
  │ [+] Extraction Complete in 93.8s (6.7 MB/s)                     │
  │ [*] Total Files Extracted : 89                                  │
  │ [*] Output Directory      : ...\Bonus_Extracted                 │
  └─────────────────────────────────────────────────────────────────┘
  ```
* **Real-Time File Stream:** Prints each individual file with file counters as it is decoded to disk.
* **Drag & Drop:** Simply drag any `.bin` or `.doi` file onto `Extract_BIN_Drag_Drop.bat`.
* **No Administrator Rights Required:** Automatically patches IPC memory mappings in memory from `Global\` to `Local\`, preventing permission hangs without needing UAC elevation.
* **Universal Compatibility:** Supports both FitGirl (`.bin`) and DODI (`.doi` / `.bin`) repacks.

---

## 📋 Prerequisites

1. **Python 3.x (32-bit recommended for native `unarc.dll` compatibility):**
   * Installed from [python.org](https://www.python.org/) or via `py`.
   * *Note: The script automatically auto-detects and re-delegates to 32-bit Python if launched from 64-bit Python.*
2. **`innoextract`:**
   * Used to unpack the installer's internal codec suite.
   * Install easily via Windows Package Manager:
     ```powershell
     winget install dscharrer.innoextract
     ```

---

## 🚀 How to Use

### Method 1: Drag & Drop (Batch File)
1. Keep `Extract_BIN_Drag_Drop.bat` and `extract_fitgirl_bin.py` in the same directory.
2. Drag any `.bin` or `.doi` file and drop it directly onto `Extract_BIN_Drag_Drop.bat`.
3. The CMD window opens, displays your hardware specs, streams each extracted file with real-time percentage, and outputs your content into `<ArchiveName>_Extracted`.

### Method 2: Command Line (CLI)
```powershell
py extract_fitgirl_bin.py "<path_to_setup.exe>" "<path_to_archive.bin>" "<output_directory>"
```

---

## 👤 Author

**Mohamed Moslem Allouch**
* GitHub: [@Mohamed-Moslem-Allouch](https://github.com/Mohamed-Moslem-Allouch)

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
