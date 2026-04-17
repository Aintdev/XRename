import sys
import os
import re
import msvcrt
import winreg
import requests
import msvcrt
import subprocess
from pathlib import Path
VERSION = "1.2.5"

def get_base_path():
    if getattr(sys, 'frozen', False):
        # PyInstaller EXE
        return os.path.dirname(sys.executable)
    else:
        # normaler Python Run
        return os.path.dirname(os.path.abspath(__file__))

API_FILE = os.path.join(get_base_path(), "api.dat")
apiKey = None

ALLOWEDFILETYPES = ('mkv', 'mp4', 'avi', 'avm')

class AutoUpdate:
    def __init__(self, version: str, raw_version_url: str, download_url: str):
        self.current_version = version
        self.raw_version_url = raw_version_url
        self.download_url = download_url

        self.exe_path = sys.executable  # funktioniert in .exe
        self.is_frozen = getattr(sys, "frozen", False)

    def get_latest_version(self):
        try:
            r = requests.get(self.raw_version_url, timeout=5)
            return r.text.strip()
        except:
            return None

    def is_newer(self, latest, current):
        def parse(v): return [int(x) for x in v.split(".")]
        return parse(latest) > parse(current)

    def download_new_version(self, path):
        r = requests.get(self.download_url, stream=True)
        with open(path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

    def create_kill_and_replace_script(self, old_path, new_path):
        from pathlib import Path

        exe_path = Path(old_path)
        bat_path = exe_path.parent / "update.bat"

        args_str = " ".join([f'"{a}"' for a in sys.argv[1:]])

        content = f"""
timeout /t 1 > nul

:loop
del "{old_path}" > nul 2>&1
if exist "{old_path}" (
    timeout /t 1 > nul
    goto loop
)

rename "{new_path}" "{exe_path.name}"
del "%~f0"
"""

        with open(bat_path, "w") as f:
            f.write(content)

        return str(bat_path)

    def run_update(self):
        if not self.is_frozen:
            print("⚠️  Update nur in .exe Modus aktiv")
            return

        latest = self.get_latest_version()
        if not latest:
            print("❌ Konnte Version nicht prüfen")
            return

        print(f"📦 Aktuell: {self.current_version} | Neu: {latest}")

        if not self.is_newer(latest, self.current_version):
            print("✅ Kein Update nötig")
            return

        release_url = self.download_url.split("/download/")[0]

        print(f"Release Seite des Updates: {release_url}\nSoll das Update runtergeladen werden? J/N: ", flush=None)
        key = msvcrt.getch().decode().lower()
        if (key != "y" and key != "j"):
            return
        print("⬇️ Update verfügbar, lade herunter...")

        exe_dir = Path(self.exe_path).parent
        old_exe = self.exe_path
        new_exe = str(exe_dir / (Path(self.exe_path).stem + " New.exe"))

        self.download_new_version(new_exe)

        print("🧠 Starte Update-Prozess...")

        bat = self.create_kill_and_replace_script(old_exe, new_exe)

        subprocess.Popen(
            ["cmd", "/c", bat],
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )

        print("🚀 Update wird angewendet, Programm schließt...")
        sys.exit()

class XRenameContextMenu:
    def __init__(self):
        self.root_keys = [
            r"Software\Classes\*\shell\XRename",
            r"Software\Classes\Directory\shell\XRename"
        ]
        self.reg_root = winreg.HKEY_CURRENT_USER

    # =========================================================
    # CHECK
    # =========================================================

    def is_installed(self):
        try:
            with winreg.OpenKey(self.reg_root, self.root_keys[0], 0, winreg.KEY_READ):
                return True
        except FileNotFoundError:
            return False

    # =========================================================
    # INSTALL
    # =========================================================

    def install(self):
        exe = os.path.abspath(sys.argv[0])

        print("Installiere XRename Context Menu...")

        for base in self.root_keys:
            try:
                # ROOT MENU (WICHTIG: kein command!)
                with winreg.CreateKey(self.reg_root, base) as root:
                    winreg.SetValueEx(root, "MUIVerb", 0, winreg.REG_SZ, "XRename")
                    winreg.SetValueEx(root, "SubCommands", 0, winreg.REG_SZ, "")

                # SHELL CONTAINER
                with winreg.CreateKey(self.reg_root, base + r"\shell"):
                    pass

                # ================= SERIES =================
                with winreg.CreateKey(self.reg_root, base + r"\shell\Series") as s:
                    winreg.SetValue(s, "", winreg.REG_SZ, "Rename Serie/Folge")

                with winreg.CreateKey(self.reg_root, base + r"\shell\Series\command") as c:
                    winreg.SetValue(c, "", winreg.REG_SZ, f'"{exe}" --s "%L"')

                # ================= MOVIE =================
                with winreg.CreateKey(self.reg_root, base + r"\shell\Movie") as m:
                    winreg.SetValue(m, "", winreg.REG_SZ, "Rename Film")

                with winreg.CreateKey(self.reg_root, base + r"\shell\Movie\command") as c:
                    winreg.SetValue(c, "", winreg.REG_SZ, f'"{exe}" --m "%L"')

                print(f"OK: {base}")

            except PermissionError:
                print(f"Keine Rechte: {base}")

        print("Fertig.")

    # =========================================================
    # REMOVE
    # =========================================================

    def remove(self):
        for base in self.root_keys:
            try:
                winreg.DeleteKey(self.reg_root, base + r"\shell\Series\command")
                winreg.DeleteKey(self.reg_root, base + r"\shell\Series")

                winreg.DeleteKey(self.reg_root, base + r"\shell\Movie\command")
                winreg.DeleteKey(self.reg_root, base + r"\shell\Movie")

                winreg.DeleteKey(self.reg_root, base + r"\shell")
                winreg.DeleteKey(self.reg_root, base)

                print(f"Removed: {base}")

            except FileNotFoundError:
                pass

    # =========================================================
    # AUTO SETUP
    # =========================================================

    def ensure_installed(self):
        if not getattr(sys, "frozen", False): return
        if not self.is_installed():
            self.install()
            sys.exit(1)

    # =========================================================
    # UTIL PATH
    # =========================================================

    def get_path(self):
        return sys.argv[-1] if len(sys.argv) > 1 else os.getcwd()

# =========================================================
# SERIES RENAMER
# =========================================================

class SeriesRenamer:
    def __init__(self):
        self.changes = {}
        FILETYPES = ALLOWEDFILETYPES

    # =========================================================
    # PATH LOGIC (IDENTISCH)
    # =========================================================

    def configPath(self, args):
        if not os.path.exists(args[-1]):
            path = os.getcwd()
            print("No path found -- using execution path: '" + path + "'")
        else:
            path = args[-1]
            print("Path found")

        if os.path.isdir(path):
            self.dirHandler(path)
        else:
            myPath, myFileName = os.path.split(path)
            self.fileHandler(myPath, myFileName)

    def dirHandler(self, path):
        for root, _, files in os.walk(path):
            for file in files:
                self.fileHandler(root, file)

    # =========================================================
    # RENAMING LOGIC
    # =========================================================

    def makeShowName(self, basename):
        basename = str(basename).replace(".", " ").replace("_", " ").replace("-", " ")

        if basename.istitle():
            return basename
        elif basename.islower():
            return basename.title()
        elif basename.isupper():
            return basename.lower().title()
        else:
            return basename

    def fileHandler(self, path, fileName):
        
        match = re.search(r"s\d{1,2}e\d{1,2}", fileName.lower())

        if match is None:
            print(f"No match in {fileName}")
            return

        index = match.start()
        dotBackIndex = int(fileName[::-1].find("."))

        if dotBackIndex == -1:
            fileEnding = ""
        else:
            fileEnding = fileName[-dotBackIndex:]

        newFileName = f"{self.makeShowName(fileName[0:index-1])} {match.group()}.{fileEnding}"

        print(fileName, "-->", newFileName)

        self.changes[os.path.join(path, fileName)] = os.path.join(path, newFileName)

    def rename(self):
        for key, value in self.changes.items():
            if not os.path.exists(value):
                os.rename(key, value)
                print(f"Rename completed: {key} --> {value}")
            else:
                print(f"Skipped {key}, {value} existiert schon.")

    # =========================================================
    # RUN
    # =========================================================

    def run(self):
        self.configPath(sys.argv)

        if len(self.changes) > 50:
            print("More than 50 Changes. Please confirm these Changes. (y/n): ", end="", flush=True)
            key = msvcrt.getch().lower()
            if key == b"y":
                print("File renaming started.")
                self.rename()
        else:
            self.rename()

        print("Exited.")

# =========================================================
# MOVIE RENAMER
# =========================================================

class MovieRenamer:
    def __init__(self):
        self.changes = {}

    # =========================================================
    # PATH
    # =========================================================

    def getRootPath(self):
        args = sys.argv

        if not os.path.exists(args[-1]):
            path = os.getcwd()
            print("⚠️ No path found -- using execution path: '" + path + "'")
        else:
            path = args[-1]
            print("✅ Path found")

        return path

    # =========================================================
    # File Handling
    # =========================================================

    def getAllMovieLocations(self, rootPath):
        fileTypes = ALLOWEDFILETYPES
        movies = []
        if os.path.isfile(rootPath):
            return [rootPath]
        
        for root, _, files in os.walk(rootPath):
            for file in files:
                if file.endswith(fileTypes):
                    movies.append(os.path.join(root, file))
        return movies
    
    # =========================================================
    # Rename
    # =========================================================

    @staticmethod
    def extract_imdb_url(content):
        match = re.search(r"(tt\d{7,8})", content)
        
        if match:
            return match.group(1)
        
        return None

    @staticmethod
    def get_movie_data(imdb_id):
        print(f"☺️  {imdb_id=}")
        if not apiKey:
            raise ValueError("API Key nicht gesetzt")

        url = f"http://www.omdbapi.com/?i={imdb_id}&apikey={apiKey}"

        try:
            r = requests.get(url, timeout=5)
            #print(r.json())
            return r.json()
        except requests.RequestException:
            return None
 
    def tryNfoImdbReadout(self, nfoPath):
        try:
            # Datei lesen (robust gegen Encoding)
            with open(nfoPath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            # IMDb URL extrahieren
            imdb_url = MovieRenamer.extract_imdb_url(content)
            if not imdb_url:
                print("⚠️ Keine IMDb URL gefunden")
                return None

            # Daten holen
            data = MovieRenamer.get_movie_data(imdb_url)
            if not data or data.get("Response") == "False":
                print("⚠️ Keine gültigen Filmdaten")
                return None

            print(f"✅ Film gefunden:\n✅ {data.get("Title")=},\n✅ {data.get("Year")=}")
            return data

        except Exception as e:
            print("❌ Fehler beim NFO lesen:", e)
            return None
    
    def read_nfo(self, path):
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()


    def extract_from_title_line(self, content):
        # sucht "Titel (2025)"
        for line in content.splitlines():
            line = line.strip()
            
            match = re.search(r"(.+?)\s*\((\d{4})\)", line)
            if match:
                name = match.group(1).strip()
                year = match.group(2)
                
                # filter gegen Müll (ASCII-Art etc.)
                if len(name) > 2 and not name.isupper():
                    return {"Title": name, "Year": year}

        return {"Title": None, "Year": None}


    def extract_from_keywords(self, content):
        # typische Felder
        patterns = [
            r"ORIGINAL_TITLE\s*:\s*(.+)",
            r"TITLE\s*:\s*(.+)",
            r"Movie\s*Name\s*:\s*(.+)"
        ]

        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                line = match.group(1).strip()

                year_match = re.search(r"\((\d{4})\)", line)
                if year_match:
                    year = year_match.group(1)
                    name = line.replace(f"({year})", "").strip()
                    return name, year

                return line, None

        return None, None


    def extract_year_from_date(self, content):
        match = re.search(r"RELEASE\s*DATE.*?(\d{4})", content, re.IGNORECASE)
        if match:
            return match.group(1)
        return None

    def extract_name_year(self, content):
        # cleanup
        clean = re.sub(r"[^A-Za-z0-9.\- ]", "", content)

        # Fall 1: (2026)
        match = re.search(r"(.+?)\s*\((\d{4})\)", clean)
        if match:
            return {
                "Title": match.group(1).strip(),
                "Year": match.group(2)
            }

        # Fall 2: .2026.
        match = re.search(r"(.+?)\.(\d{4})\.", clean)
        if match:
            title = match.group(1).replace(".", " ").strip()
            return {
                "Title": title,
                "Year": match.group(2)
            }

        return {"Title": None, "Year": None}

    def parse_nfo(self, path):
        content = self.read_nfo(path)

        name, year = self.extract_from_title_line(content)

        if not name:
            name, year = self.extract_from_keywords(content)

        if not year:
            year = self.extract_year_from_date(content)

        result = {
            "Title": name,
            "Year": year,
            "valid": bool(name or year)
        }

        return result

    def rename(self, movieFile, extension, nfoFile, data):
        title = data.get("Title") or "Unknown"
        year = data.get("Year")

        year_part = f" ({year})" if year else ""

        new_movie = os.path.join(
            os.path.dirname(movieFile),
            f"{title}{year_part}{extension}"
        )

        new_nfo = os.path.join(
            os.path.dirname(nfoFile),
            f"{title}{year_part}.nfo"
        )

        os.rename(movieFile, new_movie)
        print(f"✅ Renamed {os.path.basename(movieFile)} -> {title}{year_part}{extension}")

        try:
            os.rename(nfoFile, new_nfo)
            print(f"✅ Renamed {os.path.basename(nfoFile)} -> {title}{year_part}.nfo")
        except FileNotFoundError as e:
            print("Konnte NFO Datei nicht finden.", e)

    def getData(self, files):
        for file in files:
            print(f"☺️  {file=}")
            oldName, extension = os.path.splitext(os.path.basename(file))

            folder = os.path.dirname(file)
            nfoPath = os.path.join(folder, oldName + ".nfo")
            if os.path.isfile(nfoPath):
                print("Failed.")
                print("☺️  Attempt 1: ", flush=False)
                data = self.tryNfoImdbReadout(nfoPath)
                if data:
                    print("SUCESS")
                    self.rename(file, extension, nfoPath, data)
                    continue
                print("☺️  Attempt 2: ", flush=False)
                print("Failed.")
                data = self.parse_nfo(nfoPath)
                if data and data.get("Title"):
                    print("SUCESS")
                    self.rename(file, extension, nfoPath, data)
                    continue
                print("Failed.")
                print("☺️  Attempt 3: ", flush=False)
                with open(nfoPath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                data = self.extract_name_year(content)
                if data and data.get("Title"):
                    print("SUCESS")
                    self.rename(file, extension, nfoPath, data)
                    continue
                print("Failed.")
                print("❌ Konnte den Namen nicht finden.")
            print("❌ Konnte keine NFO Datei finden. -> Benutze Dateinamen")
            print("☺️  Attempt 4: ", flush=False)
            data = self.extract_name_year(os.path.basename(file))
            if data and data.get("Title"):
                print("SUCESS")
                self.rename(file, extension, nfoPath, data)
                continue
            print("Failed.")
            print("☺️  Attempt 5: ", flush=False)
            data = self.extract_from_title_line(os.path.basename(file))
            if data and data.get("Title"):
                print("SUCESS")
                self.rename(file, extension, nfoPath, data)
                continue
            else:
                print("Failed.")
                print("☺️  Attempt 7: ", flush=False)
                while True:
                    try:
                        print("☺️  ---------------------------------")
                        print("☺️  "+ os.path.basename(file))
                        data = input("☺️  Konnte leider keinen Namen interpretieren. Bitte geben sie den gewünschten Dateinamen und Jahr ein (Req. Format Z.b: 'Spiderman 2, 2023') (Leer = Datei Überspringen): ")
                        if not data:
                            continue
                        data = data.split(", ", 1) 
                        data = {"Title": data[0], "Year": data[1]}
                        print("SUCESS")
                        self.rename(file, extension, nfoPath, data)
                        break
                    except: 
                        print("❌ Bitte halten sie sich an das angegebene Format.")
                continue

    # =========================================================
    # RUN
    # =========================================================

    def run(self):
        path = self.getRootPath()
        files = self.getAllMovieLocations(path)

        self.getData(files)

        print("Exited.")
        sys.exit(1)


# =========================================================
# MAIN
# =========================================================

def load_and_check_api_key():
    global apiKey

    # 1. Key aus Datei laden
    if os.path.exists(API_FILE):
        with open(API_FILE, "r", encoding="utf-8") as f:
            apiKey = f.read().strip()
    else:
        apiKey = ""

    def test_key(key: str) -> bool:
        url = f"http://www.omdbapi.com/?i=tt0111161&apikey={key}"
        try:
            r = requests.get(url, timeout=5)
            data = r.json()
            return data.get("Response") != "False"
        except:
            return False

    # 2. Wenn Key vorhanden → testen
    if apiKey:
        if test_key(apiKey):
            print("✅ API Key gültig")
            return
        else:
            print("❌ API Key ungültig.")

    while True:
        print("☺️  API Key Generieren auf: https://www.omdbapi.com/apikey.aspx")
        new_key = input("☺️  Neuen API Key eingeben (Enter = überspringen): ").strip()

        if not new_key:
            return

        if test_key(new_key):
            apiKey = new_key
            with open(API_FILE, "w", encoding="utf-8") as f:
                f.write(apiKey)
            print("✅ API Key gültig")
            return
        else:
            print("❌ Ungültig, nochmal versuchen.")



if __name__ == "__main__":
    print("☺️  VERSION:", VERSION)

    # UPDATE
    updater = AutoUpdate(
        version=VERSION,
        raw_version_url="https://raw.githubusercontent.com/Aintdev/XRename/refs/heads/main/version.txt",
        download_url="https://github.com/Aintdev/XRename/releases/latest/download/XRename.exe"
    )

    updater.run_update()

    ctx = XRenameContextMenu()

    if "--remove" in sys.argv:
        ctx.remove()
        sys.exit(0)
    ctx.ensure_installed()
    load_and_check_api_key()

    if "--m" in sys.argv:
        MovieRenamer().run()
    elif "--s" in sys.argv:
        SeriesRenamer().run()
    else:
        print("""❌ Argument ungültig oder fehlend. Bitte benutze folgende argumente:
              --s {PATH}        - um eine Serie oder Episoden umzu benennen
              --m {PATH}        - um einen Film umzu benennen""")