# Native Firmware (ESP32 C++)

Ten katalog zawiera pierwszą działającą wersję natywnego firmware bez ESPHome.

## Lokalizacja

- `firmware_native/platformio.ini`
- `firmware_native/src/main.cpp`

## Co działa (v0.1)

- Wi-Fi STA + stałe IP `192.168.1.200`
- ADS1115 (A1) po I2C (`GPIO21/22`)
- Dallas DS18B20 na `GPIO4`
- Sterowanie:
  - P1 `GPIO25`
  - P2 `GPIO26`
  - AIR `GPIO27`
- REST API kompatybilne z obecnym WebGUI:
  - sensory (`main_ph`, `a1_ph_voltage`, `wifi_rssi`, `wifi_ssid`, `dallas_temp`, `last_kh`)
  - statusy (`kh_status`, `kh_mode`, `last_error`)
  - przyciski start/stop KH
  - manual testy P1/P2/AIR
  - kalibracja pH (p1 jako główna, p2 opcjonalna)
  - kalibracja P1/P2 (60s)
  - metryki obciążenia i responsywności:
    - `/diag/metrics`
    - CPU load [%]
    - heap used/free/min/max alloc
    - loop avg/max [ms]
    - HTTP handle avg/max [ms]

## Build

```powershell
pio run -d firmware_native
```

## Flash na COM6

```powershell
$env:PYTHONIOENCODING='utf-8'
python C:\Users\Biuro\.platformio\packages\tool-esptoolpy\esptool.py --chip esp32 --port COM6 --baud 460800 --before default-reset --after hard-reset write-flash -z --flash-mode dio --flash-freq 40m --flash-size detect 0x1000 firmware_native\.pio\build\esp32_native_kh\bootloader.bin 0x8000 firmware_native\.pio\build\esp32_native_kh\partitions.bin 0xe000 C:\Users\Biuro\.platformio\packages\framework-arduinoespressif32\tools\partitions\boot_app0.bin 0x10000 firmware_native\.pio\build\esp32_native_kh\firmware.bin
```

## Test szybki

```powershell
Invoke-WebRequest http://192.168.1.200/version -UseBasicParsing
Invoke-WebRequest http://192.168.1.200/sensor/a1_ph_voltage__v_ -UseBasicParsing
Invoke-WebRequest http://192.168.1.200/sensor/dallas_temp__c_ -UseBasicParsing
Invoke-WebRequest http://192.168.1.200/text_sensor/kh_status -UseBasicParsing
Invoke-WebRequest http://192.168.1.200/diag/metrics -UseBasicParsing
```

## Ładny panel

Panel uruchamiaj przez proxy:

```powershell
cd docs
python webgui_proxy_server.py --port 8090 --esp http://192.168.1.200
```

Następnie:

- `http://127.0.0.1:8090/webgui-prototype.html`
