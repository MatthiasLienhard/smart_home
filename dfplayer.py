from machine import UART, Pin
from utime import sleep_ms, ticks_ms, ticks_diff

Start_Byte = 0x7E
Version_Byte = 0xFF
Command_Length = 0x06
Acknowledge = 0x00
End_Byte = 0xEF

# inherent delays in DFPlayer
#todo:asyncio
CONFIG_LATENCY = 1000
PLAY_LATENCY =   500
VOLUME_LATENCY = 500

def clamp(x, minimum, maximum):
    return max(minimum, min(x, maximum))

def split(num):
    return num >> 8, num & 0xFF

def kill_time(stamp_ms, kill_ms):
    diff_ms = ticks_diff(ticks_ms(), stamp_ms)
    if diff_ms < kill_ms:
        snooze_ms = kill_ms - diff_ms
        sleep_ms(snooze_ms)
        return snooze_ms
    else:
        return 0

class Player():
    def __init__(self, uart=None, busy_pin=None, config=True, volume=0.5):
        self._volume = None
        if uart is None:
            self.uart = UART(1, 9600) # UART on 
            self.uart.init(9600, bits=8, parity=None, stop=1)
        else:
            self.uart = uart
        if busy_pin is not None:
            busy_pin.init(mode=Pin.IN, pull=Pin.PULL_UP)
        self.playtime = None
        self.busy_pin = busy_pin
        if config:
            self.config()
        if volume is not None:
            self.volume(volume)

    def command(self, CMD, Par1=0, Par2=0):
        self.awaitconfig()
        Checksum = -(Version_Byte + Command_Length + CMD + Acknowledge + Par1 + Par2)
        HighByte, LowByte = split(Checksum)
        CommandLine = bytes([b & 0xFF for b in [
            Start_Byte, Version_Byte, Command_Length, CMD, Acknowledge,
            Par1, Par2, HighByte, LowByte, End_Byte
        ]])
        self.uart.write(CommandLine)

    def config(self):
        self.configtime = ticks_ms()
        #self.reset()
        self.command(0x3F, 0x00, 0x00)

    def play(self, folderNum, trackNum):
        self.awaitconfig()
        self.playtime = ticks_ms()
        self.command(0x0F, folderNum, trackNum)

    def finish(self, folderNum, trackNum):
        self.play(folderNum, trackNum)
        while self.playing():
            sleep_ms(50)

    def playing(self):
        if self.busy_pin is not None:
            self.awaitplay()
            return self.busy_pin.value() == 0
        else:
            raise AssertionError("No busy pin provided, cannot detect play status")

    def awaitconfig(self):
        if self.configtime is not None:
            kill_time(self.configtime, CONFIG_LATENCY)
        self.configtime = None

    def awaitplay(self):
        if self.playtime is not None: # handle delay between playing and registering
            kill_time(self.playtime, PLAY_LATENCY)
        self.playtime = None

    def awaitvolume(self):
        if self.volumetime is not None: # handle delay between playing and registering
            kill_time(self.volumetime, VOLUME_LATENCY)
        self.volumetime = None

    def repeat(self, repeat=True):
        self.awaitconfig()
        val = 1 if repeat else 0
        self.command(0x11, 0, val)

    def _gain(self, gain=1.0):
        self.awaitconfig()
        gain = float(clamp(gain, 0, 1.0))
        val = int(30.0 * gain)
        self.command(0x10,0 ,val)  

    def volume(self, volume=None):
        self.awaitconfig()
        if volume is None:
            return self._volume
        else:
            self._volume = float(clamp(volume, 0, 1.0))
            val = int(30.0 * self._volume)
            self.command(0x06,0 ,val)
            self.volumetime = ticks_ms()

    def standby(self):
        self.awaitconfig()
        self.command(0x0A, 0x00, 0x00)

    def wake(self):
        self.awaitconfig()
        self.command(0x0B, 0x00, 0x00)

    def reset(self):
        self.awaitconfig()
        self.command(0x0C, 0x00, 0x00)

def main():
    from time import sleep
    player = Player(busy_pin=Pin(0))
    player.volume(0.5)
    player.awaitvolume()
    for folder in range(0,3):
        for track in range(0, 2):
            player.play(folder, track)
            while player.playing():
                sleep(0.01)


# 01 Spielt die nächste Datei
# 02 Spielt die vorherige Datei
# 03 Spielt eine Datei aus dem Hauptverzeichnis (1-3000)
# 04 Lautstärke um 1 erhöhen
# 05 Lautstärke um 1 verringern
# 06 Lautstärke setzen (0-30)
# 07 Equalizer setzen (0-5
# 08 Spiele eine Datei wiederholend aus dem Hauptverzeichnis (1-3000)
# 09 Setzt die zu verwendente Datenquelle fest (0-4)
# 0A Das Modul wird in den Standby-Modus versetzt
# 0B Das Modul wird in den Normal-Modus versetzt (aufgeweckt)
# 0C Setzt das Modul zurück und gibt den Status zurück
# 0D Spielt einen pausierten Track weiter oder startet den aktuellen Track
# 0E Pausiert die gerade abgespielte Datei
# 0F Spielt eine Datei aus dem Ordner 01 - 99
# 10 Schaltet den Verstärker ein oder aus und setzt den Verstärkungsfaktor
# 11 Schaltet das wiederholende Abspielen aller Datein ein oder aus
# 12 Spielt eine Datei aus dem Ordner MP3 ab (1-9999)
# 13 Unterbricht die laufende Datei, spielt eine Werbeunterbrechung aus ADVERT und setzt das Abspielen fort (1-9999)
# 14 Spielt eine Datei aus einem "großen" Ordner ab (1-15)
# 15 Beendet das abspielen einer ADVERT-Datei und setzt danach das abspielen der zuvor unterbrochenen Datei wieder fort
# 16 Beendet das abspielen der laufenden Datei
# 17 Wiederholt die Dateien aus dem Ordner (1-99)
# 18 Spielt alle Dateien des Mediums zufaellig ab
# 19 Spielt eine laufende Datei wiederholend ab
# 1A Schalte den Verstaerker stumm
# Abfragen:
# 3F Gibt das aktuelle Speichermedium zurück (1-4)
# 42 Gibt den aktuellen Status zurück
# 43 Gibt den aktuellen Lautstärkepegel zurück
# 44 Gibt den aktuellen Equalizer-Modus zurück
# 45 Gibt den aktuellen Abspiel-Modus zurück
# 46 Gibt die aktuelle Softwareversion zurück
# 47 Gibt die Anzahl der Dateien vom Medium USB-Speicherstick zurück
# 48 Gibt die Anzahl der Dateien vom Medium SD-Karte zurück
# 49 Gibt die Anzahl der Dateien vom Medium Flash zurück
# 4A Keep On, dieser Befehl wird in einigen Datenblättern erwähnt, die genaue Funktion ist allerdings unbekannt
# 4B Gibt die momentan gespielte Datei vom Medium SD-Karte zurück
# 4C Gibt die momentan gespielte Datei vom Medium USB-Speicherstick zurück
# 4D Gibt die momentan gespielte Datei vom Medium Flash zurück
# 4E Gibt die Anzahl der Dateien im abgefragten Ordner zuruck
# 4F Gibt die Anzahl der Ordner auf dem Medium zurueck
# Unabhängige Statusmeldungen:
# 3A Speichermedium wurde angeschlossen: 1=USB-Stick, 2=CD-Card, 4=PC-Mode
# 3B Speichermedium wurde entfernt: 1=USB-Stick, 2=CD-Card, 4=PC-Mode
# 3C Datei wurde beendet auf USB-Speicherstick
# 3D Datei wurde beendet auf SD-Karte
# 3E Datei wurde beendet auf Flash-Speicher
# Systemmeldungen:
# 40 Fehlermeldungen, 1=nicht bereit, 2=Sleepmode, 3=Fehler RS232, 4K=Checksumerror, 5=ungültige Dateinummer, 6=Datei nicht gefunden, 7=Inter-cut error, 8=SD-Card error, 10=in Sleepmode
# 41 Feedback, Modul bestätigt Datenempfang