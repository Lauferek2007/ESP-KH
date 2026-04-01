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

## Dodatkowe ustalenia teoretyczne

- Dodano dokument `docs/kh-methodology.md`
- Ustalono kierunek pomiaru KH:
  - pH przed aeracja jako diagnostyka procesu
  - pH po aeracji jako glowny parametr do obliczenia KH
- Ustalono kierunek obliczeniowy:
  - `PyCO2SYS / CO2SYS` jako model referencyjny offline
  - brak Pythona na ESP32
  - docelowo uproszczony solver albo lookup table na urzadzeniu
- Ustalono trzy tryby pracy:
  - `full measurement`
  - `quick measurement`
  - `service test`
- Ustalono, ze kalibracja pompek ma byc oparta o:
  - zadany czas kalibracji
  - wpisany wynik w ml
  - przeliczenie `ml_per_s`
  - wyznaczanie czasu dozowania z docelowej objetosci
- Ustalono, ze jednym z najwazniejszych tematow dalszego researchu jest:
  - zrodlo i stabilnosc CO2 gazu aerujacego

## Zalozenia firmware ESP

- Dodano dokument `docs/esp-project-spec.md`
- Ustalono, ze firmware ma byc:
  - lokalne
  - stanowe
  - przewidywalne
  - przerywalne przez `STOP`
- Ustalono podstawowe tryby pracy:
  - `full measurement`
  - `quick measurement`
  - `service test`
  - `pump calibration`
  - `pH calibration`
- Ustalono, ze procedura KH ma byc oparta o jawne stany:
  - `idle`
  - `flush`
  - `sample_fill`
  - `measure_before`
  - `aeration`
  - `measure_after`
  - `calculate`
  - `return_sample`
  - `completed`
  - `aborted`
  - `error`
- Ustalono, ze testy fizyczne z preparatami KH beda traktowane jako referencja do walidacji modelu

## Zamkniecie dnia

- Dodano dokument `docs/project-target-architecture.md`
- Ustalono docelowa strukture projektu:
  - glowny plik YAML
  - pakiety `core`, `ui`, `ph`, `temperature`, `pumps`, `pump_calibration`, `kh_procedure`, `kh_model`, `diagnostics`
  - docelowy lokalny plik `www/khv1.js`
- Ustalono, ze obecny `esphome/kh-aeration-min.yaml` jest wersja test bench do jutrzejszych testow fizycznych
- Ustalono, ze rozbijanie jednego duzego YAML-a na pakiety ma sens, ale dopiero po ustabilizowaniu logiki
- Ustalono kolejnosc:
  - najpierw testy fizyczne
  - potem dane referencyjne
  - potem stabilizacja procedury
  - potem migracja hardware
  - potem podzial na pakiety
  - dopiero pozniej finalne UI
- Potwierdzono, ze kolejne testy maja byc prowadzone z wykorzystaniem preparatow referencyjnych KH
