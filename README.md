# Repack Archive Extractor (FitGirl / DODI)

A lightweight utility to extract selective and optional archives (`.bin` / `.doi` files) directly from **FitGirl** and **DODI** repacks without downloading or installing the full base game.

---

## 🌟 Why Use This?

Repack installers usually lock components and force you to download the entire base game (often 30–70 GB) even if you only want:
* 🎵 Soundtracks (MP3 / FLAC)
* 🎨 Digital Artbooks (CBZ / PDF)
* 📖 Digital Comics & Strategy Guides (CBR / PDF)
* 🗣️ Selective Voice / Language Packs

This tool extracts the internal FreeArc and pre-compression codec plugins directly from the repack's `setup.exe` (~6 MB) and uses Python to decompress only your chosen `.bin` or `.doi` archive, **saving tens of gigabytes of download bandwidth and disk space**.

---

## ✨ Features

* **Drag & Drop Support:** Drag any `.bin` or `.doi` file onto `Drag_Drop_Extractor.bat` to unpack instantly.
* **Graphical User Interface (GUI):** Double-click `repack_extractor.py` or the batch file to open an intuitive GUI with file browsing and real-time logs.
* **No Administrator Rights Required:** Automatically patches IPC memory mappings in memory from `Global\` to `Local\`, preventing permission hangs without needing UAC elevation.
* **FitGirl & DODI Compatibility:** Supports both `.bin` and `.doi` archive containers.
* **Selective Extraction:** Only extracts the archive you select—never forces base game data.

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
1. Place `Drag_Drop_Extractor.bat` and `repack_extractor.py` in the same directory.
2. Drag any `.bin` or `.doi` archive and drop it directly onto `Drag_Drop_Extractor.bat`.
3. If `setup.exe` is in the same folder, extraction begins immediately into a `<ArchiveName>_Extracted` folder.

### Method 2: Graphical User Interface (GUI)
1. Double-click `repack_extractor.py` (or `Drag_Drop_Extractor.bat` without dropping a file).
2. Select your archive file (`.bin` or `.doi`).
3. Select the repack's `setup.exe`.
4. Choose an output directory and click **▶ Extract Archive**.

### Method 3: Command Line (CLI)
```powershell
py repack_extractor.py "<path_to_setup.exe>" "<path_to_archive.bin>" "<output_directory>"
```

---

## ⚙️ How It Works Under the Hood

1. **Toolchain Extraction:** Uses `innoextract` to unpack `unarc.dll`, `arc.ini`, `CLS.ini`, and the helper codecs (`cls-magic2`, `cls-srep`, `mpz`, `rzw`, `oodle`, etc.) embedded inside `setup.exe`.
2. **Blueprint Customization:** Updates `{app}` path references in `arc.ini` and `CLS.ini` to point to your chosen output folder.
3. **IPC Namespace Patching:** Scans codec binaries for `Global\` kernel shared memory namespaces and rewrites them to `Local\`, allowing the extraction subroutines to run under standard user permissions.
4. **Direct Invocation:** Binds to `unarc.dll` via Python's `ctypes` and calls `FreeArcExtract()` with your target archive parameters.
5. **Cleanup:** Automatically purges temporary codec files once extraction concludes.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
