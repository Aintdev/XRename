import os
import random
import shutil
import time

if os.path.exists("logs.txt"):
        print("Deleting LogFile.")
        os.remove("logs.txt")
log_file = open("logs.txt", "a")
FILECOUNT = 1000

names = [
    "Dark", "Breaking Code", "Hackers", "System X", "Void", "Binary Life",
    "Cyber.Realm", "Neon_Nights", "Quantum-Shift", "Ghost_Protocol",
    "SilentEcho", "CodeRed", "Red.Horizon", "Eclipse", "Nightfall",
    "ZeroHour", "Infinite.Loop", "DigitalFrontier", "Blackout",
    "AlphaTest", "Omega_Point", "DarkMatter", "CrimsonSky", "Parallel",
    "PhantomSignal", "GlitchCity", "IronGrid", "Pixel-Wars", "ShadowNet",
    "NeuralNetwork", "Final.Sequence", "LostSignal", "OblivionCode",
    "Spectrum", "VirtualMind", "Firewall", "DeepDive", "ExMachina",
    "TheLoop", "DataBreach", "Quantum_Code", "Signal.Lost", "Night_Grid",
    "bINaryLife", "dArk.Matter", "cyber_realmX", "Ne0nNights", "H4ckers",
    "sysTem-X", "V0id", "ghost.Protocol", "Silent_echo", "RedHorizon2",
    "Alpha-Test", "OmegaPoint", "Infinite.loop2", "digitalFrontierX",
    "Crim$onSky", "ParallelX", "Phant0mSignal", "Glitch.city", "Iron-Grid",
    "PixelWarsX", "Shadow-net", "Neural_Network", "FinalSeq", "Lost_Signal",
    "Oblivion_Code", "SpecTrum", "Virtual-Mind", "FireWallX", "Deep_Dive",
    "Ex-Machina", "The.LoopX", "Data-Breach", "QuantumCodeX", "Signal_Lost",
    "NightGridX", "Binary_life", "Dark-Matter", "CyberRealm", "NeonN1ghts",
    "Quantum_Shift2", "Ghost_ProtocolX", "SilentEcho2", "Code_Red", "Red.HorizonX",
    "Eclipse2", "NightFallX", "ZeroHour2", "InfiniteLoopX", "Digital.Frontier",
    "Black-Out", "AlphaTest2", "Omega_PointX", "DarkMatter2", "Crimson-Sky",
    "Parallel2", "Phantom.SignalX", "GlitchCity2", "Iron_GridX", "PixelWars2",
    "ShadowNet2", "NeuralNetworkX", "Final.Sequence2", "LostSignalX", "OblivionCode2",
    "SpectrumX", "VirtualMind2", "Firewall2", "DeepDiveX", "ExMachina2", "TheLoop2"
]

languages = [
    "GERMAN", "ENGLISH", "MULTi", "GERMAN DL", "ENGLISH SUBBED",
    "SPANISH", "FRENCH", "ITALIAN", "JAPANESE", "KOREAN", "PORTUGUESE",
    "RUSSIAN", "CHINESE", "ENGLISH DUBBED", "GERMAN SUBBED", "MULTi SUB",
    "DUAL AUDIO", "ENGLISH DL", "GERMAN DL SUB", "SPANISH SUBBED", "FRENCH DL",
    "ENGLISH CC", "GERMAN CC", "ENGLISH_GERMAN", "MULTi CC", "ITALIAN SUBBED"
]

qualities = [
    "720p", "1080p", "4K", "480p", "2160p", "8K", "HDR", "HDR10",
    "HDR10+", "DV", "SD", "HD", "UHD", "HD+"
]

groups = [
    "WEBRip", "BluRay", "HDTV", "WEB DL", "DVDRip", "BRRip", "CAM",
    "TS", "WEBDL", "BluRay REMUX", "HDRip", "BDRip", "HDTC", "DVDScr",
    "WEBRip REMUX", "BluRay REPACK", "HDLight", "DVDRip RERIP"
]

video_extensions = ['mkv', 'mp4', 'avi', 'avm']

def delete_files_with_logs(path="serien_files", batch_size=2000):
    if not os.path.exists(path):
        print("Path does not exist!")
        return

    # Alle Dateien und Ordner sammeln
    all_items = []
    for root, dirs, files in os.walk(path, topdown=False):
        for name in files:
            all_items.append(os.path.join(root, name))
        for name in dirs:
            all_items.append(os.path.join(root, name))

    buff = []

    for i, f in enumerate(all_items, 1):
        if os.path.isfile(f):
            os.remove(f)
        else:
            os.rmdir(f)
        incr = batch_size // 20
        if i % incr == 0: buff.append(f"{i}: Deleted {os.path.basename(f)}")
        if i % batch_size == 0 or i == len(all_items):
            os.system("cls")
            for line in buff:
                print(line)
                log_file.write(line + "\n")
            buff = []

    # Letztes Verzeichnis löschen, falls noch vorhanden
    if os.path.exists(path):
        os.rmdir(path)

    print("Done!")

def random_filename():
    spacer = "."
    name = random.choice(names)
    season = random.randint(1, 5)
    episode = random.randint(1, 12)
    
    lang = random.choice(languages)
    quality = random.choice(qualities)
    group = random.choice(groups)

    extension = random.choice(video_extensions)
    
    return f"{name}{spacer}S{season:02d}E{episode:02d}{spacer}{quality}{spacer}{group}{spacer}{lang}.{extension}"

def create_files(amount, path="."):
    print("func called")
    if os.path.exists(path):
        print("Deleting Directory -- This may take a while if directory is big.")
        delete_files_with_logs(path)
    os.makedirs(path)
    buff = []
    for i in range(amount):
        filename = random_filename()
        filepath = os.path.join(path, filename)
        
        with open(filepath, "w") as f:
            f.write("")
        if i % 10 == 0: buff.append("%s: Created Dummy file named %s!" % (i, filename))
        if i % 100 == 0: 
            os.system("cls")
            for line in buff:
                print(line)
                log_file.write(line + "\n")
            buff = []
    log_file.close()

print("Loading...")

start = time.perf_counter_ns()
print("timer started")
create_files(FILECOUNT, "serien_files")
stop = time.perf_counter_ns()

avr = (stop - start) / FILECOUNT
avr_ms = avr / 1_000_000
print(f"Creation took {avr_ms:.3f} nanoseconds average.")
input()