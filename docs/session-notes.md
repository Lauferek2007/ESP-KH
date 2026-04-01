# Session Notes

To miejsce na krotkie ustalenia projektowe, zeby latwo bylo wznowic prace z innego komputera.

## 2026-04-01

- Utworzono bazowa strukture repo pod ESPHome
- Dodano przykladowy modul `test-esp32`
- Dodano skrypty pomocnicze do walidacji i kompilacji
- Ustalono, ze wczesniejszy kod nie byl jeszcze zapisany w repo i trzeba zaczac od kontrolowanej wersji minimalnej
- Dodano nowy plik `esphome/kh-aeration-min.yaml`
- Zbudowano minimalna wersje KH Keeper z:
  - lokalnym `web_server`
  - prostym WebGUI
  - dwoma pompkami
  - pompka powietrza
  - odczytem pH z ADC ESP32
  - kalibracja pH 7.00
  - kalibracja pompek na podstawie 30 s
  - procedura KH full i quick
- Dodano status procesu `KH • status` do panelu
- Walidacja `esphome config` dla `kh-aeration-min.yaml` przechodzi poprawnie
- Commit startowy minimalnej wersji:
  - `ac2c3d2` - `Add minimal KH aeration firmware with web UI`
- Commit zostal wypchniety na `origin/main`

## Co robic dalej

- Kolejny komputer powinien zaczac od pliku `esphome/kh-aeration-min.yaml`
- Pracujemy malymi krokami i po kazdym etapie robimy walidacje
- Najbardziej prawdopodobne kolejne etapy:
  - dodanie statusow pomocniczych typu uptime i Wi-Fi
  - dodanie 3 pompki
  - migracja pH z ADC ESP32 na ADS1115
  - dodanie DS18B20
  - przejscie na output PWM / LEDC
  - dopiero pozniej lokalny JS `khv1.js`
