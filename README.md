# Static Site Mirror

Static Site Mirror je aplikace pro stažení a úpravu statických verzí webových stránek pomocí `wget2`. Umožňuje stahování webu a následné úpravy HTML souborů pro kompatibilitu s jinými platformami.

## 🚀 Funkce

- **Stahování webu** pomocí `wget2`
- **Úprava HTML souborů** – změna cest k assetům a URL
- **Jednoduché GUI** postavené na `Kivy`
- **Automatické generování `.exe` přes GitHub Actions**

## 🛠️ Instalace

### 1️⃣ Lokální spuštění (Linux & macOS)

Pokud chceš spustit aplikaci bez kompilace:

```sh
pip install -r requirements.txt
python main.py
```

### 2️⃣ Spuštění na Windows

Pro Windows můžeš použít předkompilovaný `.exe`, který je generován v GitHub Actions.

## 🏗️ Jak sestavit `.exe`

GitHub Actions automaticky generuje `.exe` soubor. Stačí pushnout kód do repozitáře a stáhnout výstup:

### ✅ Manuální sestavení `.exe` na Windows

Pokud chceš sestavit `.exe` ručně, proveď následující kroky:

```sh
pip install nuitka kivy
nuitka --onefile --windows-icon-from-ico=icon.ico \
       --include-package=kivy \
       --include-data-files=wget2.exe=wget2.exe \
       --output-dir=dist \
       main.py
```

Výsledný `.exe` se objeví ve složce `dist/`.

## 📦 Použití GitHub Actions pro generování `.exe`

Pokud chceš `.exe` generovat automaticky bez Windows, použij GitHub Actions:

1. Ujisti se, že repozitář je **public** (pro bezplatné buildy).
2. Vytvoř soubor `.github/workflows/build.yml` s tímto obsahem:

```yaml
name: Build EXE with Nuitka

on:
  push:
    branches:
      - main

jobs:
  build:
    runs-on: windows-latest
    steps:
      - name: Checkout repo
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.10"

      - name: Install Nuitka and dependencies
        run: |
          python -m pip install --upgrade pip
          pip install nuitka kivy

      - name: Build EXE with Nuitka
        shell: cmd
        run: |
          nuitka --onefile --windows-icon-from-ico=icon.ico ^
                 --include-package=kivy ^
                 --include-data-files=wget2.exe=wget2.exe ^
                 --output-dir=dist ^
                 main.py

      - name: Upload EXE
        uses: actions/upload-artifact@v4
        with:
          name: built-exe
          path: dist/main.exe
```

3. **Commitni a pushni kód**. Po chvíli GitHub Actions sestaví `.exe`.
4. **Stáhni hotový `.exe` z Actions → built-exe → Download artifact**.

## ⚠️ Známé problémy

- Na **Linuxu** a **macOS** potřebuješ nainstalovat `xclip` a `xsel` pro clipboard.
  ```sh
  sudo apt install xclip xsel -y  # Debian/Ubuntu
  sudo pacman -S xclip xsel       # Arch
  sudo dnf install xclip xsel     # Fedora
  ```
- Na **Windows 10+** můžeš `.bin` soubor normálně spustit jako `.exe`. Pokud ne, přejmenuj ho na `.exe`.

## 📜 Licence

MIT – můžeš používat, upravovat a distribuovat bez omezení.

---

🔥 **Pokud máš problém, otevři issue nebo forkní repozitář a vylepši ho!** 🚀

