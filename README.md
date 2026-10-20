# Repack Archive Extractor (FitGirl / DODI)

A lightweight command-line tool with a live console progress bar to extract selective and optional archives (`.bin` / `.doi` files) directly from **FitGirl** and **DODI** repacks without downloading or installing the full 30–70 GB base game.

---

## 🌟 Why Use This?

Repack installers usually lock components and force you to download the entire base game even if you only want:
* 🎵 Soundtracks (MP3 / FLAC)
* 🎨 Digital Artbooks (CBZ / PDF)
* 📖 Digital Comics & Strategy Guides (CBR / PDF)
* 🗣️ Selective Voice / Language Packs

This tool extracts the internal FreeArc and pre-compression codec plugins directly from the repack's `setup.exe` (~6 MB) and uses Python to decompress only your chosen `.bin` or `.doi` archive, **saving tens of gigabytes of download bandwidth and disk space**.

---

## ✨ Features

* **Pure Command Prompt (CMD):** No pop-up windows—runs directly inside your clean terminal.
* **Live Console Progress Bar:** Shows real-time progress:
  ```text
  [ 45%] -> Soundtracks/Track01.mp3
  [ 48%] -> Soundtracks/Track02.mp3
  [████████████████░░░░░░░░]  52% (120 MB / 228 MB)
  ```
* **Real-Time File Stream:** Prints each individual file as it is decoded to disk.
* **Drag & Drop:** Simply drag any `.bin` or `.doi` file onto `Extract_BIN_Drag_Drop.bat`.
* **No Administrator Rights Required:** Automatically patches IPC memory mappings in memory from `Global\` to `Local\`, preventing permission hangs without needing UAC elevation.
* **FitGirl & DODI Compatibility:** Works with both `.bin` and `.doi` formats.

---

## 📋 Prerequisites

1. **Python 3.x (32-bit recommended for DLL interoperability):**
   * Installed from [python.org](https://www.python.org/) or via `py`.
2. **`innoextract`:**
   * Used to extract the installer's internal codec suite.
   * Install easily via Windows Package Manager:
     ```powershell
     winget install dscharrer.innoextract
     ```

---

## 🚀 How to Use

### Method 1: Drag & Drop (Batch File)
1. Keep `Extract_BIN_Drag_Drop.bat` and `extract_fitgirl_bin.py` in the same directory.
2. Drag any `.bin` or `.doi` file and drop it directly onto `Extract_BIN_Drag_Drop.bat`.
3. The CMD window opens, displays the live percentage progress bar, streams each file name, and extracts your content into `<ArchiveName>_Extracted`.

### Method 2: Command Line (CLI)
```powershell
py extract_fitgirl_bin.py "<path_to_setup.exe>" "<path_to_archive.bin>" "<output_directory>"
```

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
