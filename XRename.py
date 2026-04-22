import sys
import os
import re
import msvcrt
import winreg
import requests
import subprocess
import json
from datetime import datetime
import keyring
from pathlib import Path
from colorlog import ColoredFormatter
import logging
from typing import Callable

#
# UPDATE LOG
#
# * FIXED LOGGING IN UNDO
#

VERSION = "1.3.5"

ALLOWEDFILETYPES = ('mkv', 'mp4', 'avi', 'avm')
FORBIDDENFILENAMES = ("<", ">", ":", '"', "/", "|", "?", "*")
RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    *[f"COM{i}" for i in range(1, 10)],
    *[f"LPT{i}" for i in range(1, 10)]
}

logHandler = logging.StreamHandler()
formatter = ColoredFormatter(
    "%(asctime)s | %(log_color)s%(levelname)8s%(reset)s: %(message)s",
    datefmt="%H:%M:%S"
)

logHandler.setFormatter(formatter)

logger = logging.getLogger()
logger.addHandler(logHandler)
logger.setLevel(logging.INFO)



def log_Read(logFunc: Callable[[str], None], message: str, readFunc: Callable[[], str]):
    old_terminator = logHandler.terminator
    
    try:
        logHandler.terminator = ""
        
        logFunc(message)
        value = readFunc()
        print()
        
        return value
    finally:
        # wichtig: wieder zurücksetzen
        logHandler.terminator = old_terminator

def exit(x):
    logger.info("Exiting. CODE: %s", x)
    sys.exit(x)

def sanitize_filename(path: str) -> str:
    dirName = os.path.dirname(path)
    name = os.path.basename(path)
    for char in FORBIDDENFILENAMES:
        name = " ".join(name.replace(char, " ").split())
    name = name.rstrip(". ")
    if name.upper() in RESERVED_NAMES:
        name = f"{name}_"
    if not name:
        name = "Unknown"
    return os.path.join(dirName, name[:255])

def get_base_path():
    if getattr(sys, 'frozen', False):
        # PyInstaller EXE
        return os.path.dirname(sys.executable)
    else:
        # normaler Python Run
        return os.path.dirname(os.path.abspath(__file__))

class APIHandler:
    SERVICE = "xrename"
    KEY_NAME = "omdb"

    def __init__(self):
        self.apiKey = self.loadAPIKey()
        pass

    def saveKey(self, key: str):
        self.apiKey = key
        keyring.set_password(self.SERVICE, self.KEY_NAME, key)

    def loadAPIKey(self) -> str | None:
        return keyring.get_password(self.SERVICE, self.KEY_NAME)

    def _test_key(self, key: str) -> bool:
        url = f"http://www.omdbapi.com/?i=tt0111161&apikey={key}"
        try:
            r = requests.get(url, timeout=5)
            data = r.json()
            return data.get("Response") != "False"
        except requests.RequestException:
            return False

    def configure(self):
        if self.apiKey:
            if self._test_key(self.apiKey):
                logger.info("API Key is valid")
                return
            else:
                logger.error("API Key is invalid")

        while True:
            logger.info("Generate API Key at: https://www.omdbapi.com/apikey.aspx")
            new_key = log_Read(logger.info, "Enter new API Key (Empty = Skip): ", lambda: input().strip())

            if not new_key:
                logger.info("API Skipped")
                return

            if self._test_key(new_key):
                self.apiKey = new_key
                self.saveKey(new_key)
                logger.info("API Key is valid and was saved in Keychain")
                return
            else:
                logger.error("Invalid - Try Again")

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
        except requests.RequestException:
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
        exe_path = Path(old_path)
        bat_path = exe_path.parent / "update.bat"
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
            logger.warning("Update only active in .exe mode")
            return

        latest = self.get_latest_version()
        if not latest:
            logger.error("Could not verify version")
            return

        logger.info(f"Current: {self.current_version} | Latest: {latest}")

        if not self.is_newer(latest, self.current_version):
            logger.info("No update available")
            return

        release_url = self.download_url.split("/download/")[0]

        logger.info(f"Release URL: {release_url}" )

        key = log_Read(logger.info,
                       "Do Update? (Y/N) ",
                       lambda: msvcrt.getch().decode().lower())
        
        if (key != "y" and key != "j"):
            return
        logger.info("Update available, downloading...")

        exe_dir = Path(self.exe_path).parent
        old_exe = self.exe_path
        new_exe = str(exe_dir / (Path(self.exe_path).stem + " New.exe"))

        self.download_new_version(new_exe)

        logger.info("Installing...")

        bat = self.create_kill_and_replace_script(old_exe, new_exe)

        subprocess.Popen(
            ["cmd", "/c", bat],
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )

        logger.warning("Update is being applied, program is closing...")
        exit()

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

    def get_installed_exe(self):
        try:
            with winreg.OpenKey(
                self.reg_root,
                self.root_keys[0] + r"\shell\Series\command"
            ) as key:
                value, _ = winreg.QueryValueEx(key, "")
                return value
        except FileNotFoundError:
            return None

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

        logger.info("Installing context menu...")

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
                    winreg.SetValue(root, "", winreg.REG_SZ, "Rename Series/Episodes")

                with winreg.CreateKey(self.reg_root, base + r"\shell\Series\command") as c:
                    winreg.SetValue(c, "", winreg.REG_SZ, f'"{exe}" --s "%L"')

                # ================= MOVIE =================
                with winreg.CreateKey(self.reg_root, base + r"\shell\Movie") as m:
                    winreg.SetValue(root, "", winreg.REG_SZ, "Rename Movie")

                with winreg.CreateKey(self.reg_root, base + r"\shell\Movie\command") as c:
                    winreg.SetValue(c, "", winreg.REG_SZ, f'"{exe}" --m "%L"')

                logger.info(f"ok: {base}")

            except PermissionError:
                logger.error(f"No permissions: {base}")

        logger.info("Done.")

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

                logger.info(f"Removed: {base}")

            except FileNotFoundError:
                pass

    # =========================================================
    # AUTO SETUP
    # =========================================================

    def ensure_installed(self):
        if not getattr(sys, "frozen", False): return
        
        # Download Folder Check
        if "download" in os.path.dirname(sys.argv[0]).lower():
            logger.critical("The binary is currently located in the Downloads folder. Please confirm that the context menu shortcut should be redirected to this location. (Y/N)")
            answer = msvcrt.getch().decode().lower()
            if answer not in ("y", "j"): return

        current_exe = os.path.abspath(sys.argv[0])
        installed = self.get_installed_exe()

        if not installed or current_exe not in installed:
            logger.info("XRename context menu updating...")
            self.install()
            exit(1)

    # =========================================================
    # UTIL PATH
    # =========================================================

    def get_path(self):
        return sys.argv[-1] if len(sys.argv) > 1 else os.getcwd()

class UndoHandler:
    def __init__(self, historyPath: Path=Path(os.path.join(get_base_path(), "history.json"))):
        self.historyPath = historyPath
        self.currentSession: list[dict] = []
 
    def append(self, change: dict[str, str]):
        self.currentSession.append({
            "old": str(change["old"]),
            "new": str(change["new"])
        })

    def logChange(self):
        if not self.currentSession:
            return

        session = {
            "timestamp": datetime.now().isoformat(),
            "changes": self.currentSession
        }

        if self.historyPath.exists():
            with open(self.historyPath, "r", encoding="utf-8") as f:
                history = json.load(f)
        else:
            history = []

        history.append(session)

        with open(self.historyPath, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)

        self.currentSession = []

    @staticmethod
    def prettyPath(path):
        baseFolder = sys.argv[-1] if os.path.isdir(sys.argv[-1]) else os.path.dirname(sys.argv[-1])
        baseName = os.path.basename(baseFolder)

        return os.path.join(
                baseName,
                os.path.relpath(path, baseFolder))

    def undo(self):
        with open(self.historyPath, "r", encoding="utf-8") as f:
            history = json.load(f)

        if not history:
            logger.error("Nothing to undo")
            return

        last_session: dict = history.pop()
        last_session["changes"] = [
            change for change in last_session["changes"]
            if os.path.exists(change["new"])
        ]

        for change in last_session["changes"]:
            logger.info("Appended to undo-list: |.\\%-40s | -> |.\\%-40s |", UndoHandler.prettyPath(change["new"]), UndoHandler.prettyPath(change["old"]))

        answer = log_Read(logger.info, "Do you want to Undo these changes. (Y/N)", lambda: msvcrt.getch().decode().lower())

        if answer not in ("y", "j"):
            return

        for change in reversed(last_session["changes"]):
            if os.path.exists(change["old"]):
                logger.warning("%s File exists already. Skipping.", os.path.basename(change["old"]))
                continue

            try:
                os.rename(change["new"], change["old"])
                logger.info("Undid rename: |.\\%-40s | -> |.\\%-40s |", UndoHandler.prettyPath(change["new"]), UndoHandler.prettyPath(change["old"]))
            except FileNotFoundError:
                logger.warning("Could'nt find |.\\%40s | -> Skipped", UndoHandler.prettyPath(change["new"]))

        with open(self.historyPath, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)
        
        logger.info("Finished undoing.")

class SeriesRenamer:
    def __init__(self):
        self.changes = {}

    # =========================================================
    # PATH LOGIC (IDENTISCH)
    # =========================================================

    def configPath(self, args):
        if not os.path.exists(args[-1]):
            path = os.getcwd()
            logger.warning("No path found -- using execution path: '" + path + "'")
        else:
            path = args[-1]
            logger.info("Path found")

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
        if not fileName.lower().endswith(ALLOWEDFILETYPES):
            return
        
        match = re.search(r"s\d{1,2}e\d{1,2}", fileName.lower())

        if match is None:
            logger.error(f"No match in {fileName}")
            return

        index = match.start()
        dotBackIndex = int(fileName[::-1].find("."))

        if dotBackIndex == -1:
            fileEnding = ""
        else:
            fileEnding = fileName[-dotBackIndex:]

        newFileName = f"{self.makeShowName(fileName[0:index-1])} {match.group()}.{fileEnding}"

        logger.info("%s --> %s", fileName, newFileName)

        self.changes[os.path.join(path, fileName)] = os.path.join(path, newFileName)

    def rename(self):
        for key, value in self.changes.items():
            value = sanitize_filename(value)
            if not os.path.exists(value):
                os.rename(key, value)
                undo.append({"old": key, "new": value})
                logger.info(f"Rename completed: .\\{UndoHandler.prettyPath(key)} --> .\\{UndoHandler.prettyPath(value)}")
            else:
                logger.warning(f"Skipped .\\{UndoHandler.prettyPath(key)}, .\\{UndoHandler.prettyPath(value)} already exists.")

    # =========================================================
    # RUN
    # =========================================================

    def run(self):
        self.configPath(sys.argv)

        if len(self.changes) > 50:
            key = log_Read(logger.info, "More than 50 Changes. Please confirm these Changes. (y/n)", lambda: msvcrt.getch().decode().lower())
            if key == "y" or key == "j":
                logger.info("File renaming started.")
                self.rename()
        else:
            self.rename()

        undo.logChange()
        logger.info("Exited.")

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
            logger.warning("No path found -- using execution path: '" + path + "'")
        else:
            path = args[-1]
            logger.info("Path found")

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
        logger.info("IMDb id: %s", imdb_id)
        apiKey = APIHandler().loadAPIKey()
        if not apiKey:
            raise ValueError("API Key not found")

        url = f"http://www.omdbapi.com/?i={imdb_id}&apikey={apiKey}"

        try:
            r = requests.get(url, timeout=5)
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
                logger.warning("No IMDb URL found")
                return None

            # Daten holen
            data = MovieRenamer.get_movie_data(imdb_url)
            if not data or data.get("Response") == "False":
                logger.warning("Request invalid")
                return None

            logger.info("Found Movie:")
            logger.info(f"Title = {data.get("Title")}")
            logger.info(f"Year = {data.get("Year")}")
            return data

        except Exception as e:
            logger.error("Could'nt read NFO File: %s", e)
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
        title = sanitize_filename(data.get("Title")) or "Unknown"
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
        undo.append({"old": movieFile, "new": new_movie})
        logger.info(f"Renamed {os.path.basename(movieFile)} -> {title}{year_part}{extension}")

        try:
            os.rename(nfoFile, new_nfo)
            undo.append({"old": nfoFile, "new": new_nfo})
            logger.info(f"Renamed {os.path.basename(nfoFile)} -> {title}{year_part}.nfo")
        except FileNotFoundError as e:
            logger.error("Could'nt find NFO File: %s", e)

    def getData(self, files):
        for file in files:
            logger.info(f"{file=}")
            oldName, extension = os.path.splitext(os.path.basename(file))

            folder = os.path.dirname(file)
            nfoPath = os.path.join(folder, oldName + ".nfo")
            if os.path.isfile(nfoPath):
                data = self.tryNfoImdbReadout(nfoPath)
                if data:
                    self.rename(file, extension, nfoPath, data)
                    continue
                data = self.parse_nfo(nfoPath)
                if data and data.get("Title"):
                    self.rename(file, extension, nfoPath, data)
                    continue
                with open(nfoPath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                data = self.extract_name_year(content)
                if data and data.get("Title"):
                    self.rename(file, extension, nfoPath, data)
                    continue
                logger.error("Could'nt find data.")
            logger.error("Could not find an NFO file -> using filename instead")
            data = self.extract_name_year(os.path.basename(file))
            if data and data.get("Title"):
                self.rename(file, extension, nfoPath, data)
                continue
            data = self.extract_from_title_line(os.path.basename(file))
            if data and data.get("Title"):
                self.rename(file, extension, nfoPath, data)
                continue
            else:
                while True:
                    try:
                        logger.info("---------------------------------")
                        logger.info(os.path.basename(file))
                        data = log_Read(logger.info, "Could not interpret a valid name. Please enter the desired filename and year (required format, e.g. “Spiderman 2, 2023”). Leave empty to skip the file:", input())
                        if not data:
                            continue
                        data = data.split(", ", 1) 
                        data = {"Title": data[0], "Year": data[1]}
                        self.rename(file, extension, nfoPath, data)
                        break
                    except IndexError: 
                        logger.error("Please follow the specified format.")
                continue

    # =========================================================
    # RUN
    # =========================================================

    def run(self):
        path = self.getRootPath()
        files = self.getAllMovieLocations(path)

        self.getData(files)

        undo.logChange()
        exit(1)

# =========================================================
# MAIN
# =========================================================

def configure_Context_Menu():
    ctx = XRenameContextMenu()
    if "--remove" in sys.argv:
        ctx.remove()
        exit(0)
    ctx.ensure_installed()

def run_update():
    updater = AutoUpdate(
        version=VERSION,
        raw_version_url="https://raw.githubusercontent.com/Aintdev/XRename/refs/heads/main/version.txt",
        download_url="https://github.com/Aintdev/XRename/releases/latest/download/XRename.exe"
    )
    updater.run_update()

def invalidArgs():
    logger.critical("Argument invalid or missing. Please use the following arguments:")
    logger.critical("\t--s {PATH}\t-\tto rename a series or episodes")
    logger.critical("\t--m {PATH}\t-\tto rename a movie")
    logger.critical("\t--undo\t-\tto undo a latest change")
    logger.critical("\t--remove\t-\tto remove the registry entry.")
    exit(0)

if __name__ == "__main__":
    logger.info("VERSION: %s", VERSION)
    run_update()
    configure_Context_Menu()
    

    undo = UndoHandler()
    if sys.argv[1] == "--undo":
        undo.undo()
        exit(1)

    if len(sys.argv) < 3: invalidArgs()

    if "--m" == sys.argv[1] and os.path.exists(sys.argv[-1]):
        MovieRenamer().run()
    elif "--s" == sys.argv[1] and os.path.exists(sys.argv[-1]):
        APIHandler().configure()
        SeriesRenamer().run()
    else:
        invalidArgs()