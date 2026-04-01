# ESP-KH

Repozytorium do wspolnej pracy nad projektami ESPHome i firmware dla modulow ESP.

## Cel

To repo sluzy do:

- tworzenia konfiguracji ESPHome
- kompilowania firmware dla ESP32 i ESP8266
- zapisywania ustalen projektowych, pinow i zaleznosci
- dalszej pracy z innego komputera lub z innym Codexem

## Struktura

- `esphome/` - pliki YAML urzadzen
- `docs/` - notatki o sprzecie, pinach i wymaganiach
- `scripts/` - lokalne skrypty pomocnicze do walidacji i kompilacji

## Aktualny stan

Obecnie aktywnym plikiem roboczym jest:

- `esphome/kh-aeration-min.yaml`

Jest to minimalna wersja KH Keeper budowana od nowa jako kontrolowany punkt startowy do dalszego rozwoju.

Ta wersja zawiera:

- ESP32 `esp32dev`
- framework `esp-idf`
- lokalny `web_server`
- dwa wejscia pH z ADC ESP32:
  - `GPIO32` jako `ph_a0_v`
  - `GPIO33` jako `ph_a1_v`
- dwie pompki:
  - `GPIO25` jako `pump_p1_in`
  - `GPIO26` jako `pump_p2_out`
- pompke powietrza:
  - `GPIO27` jako `air_pump`
- kalibracje pH dla punktu 7.00
- kalibracje pompek na podstawie testu 30 s
- podstawowa procedure KH:
  - oproznienie
  - napelnienie
  - stabilizacja
  - aeracja
  - stabilizacja
  - odczyt pH i wyliczenie KH
  - powrot probki
- minimalne WebGUI oparte o `web_server` bez zewnetrznego JS

Ta wersja nie zawiera jeszcze:

- ADS1115
- DS18B20
- trzeciej pompki
- PWM / LEDC
- lokalnego pliku `khv1.js`
- docelowego modelu produktowego

## Jak pracowac

1. Pracuj na `esphome/kh-aeration-min.yaml`, dopoki nie ustalimy kolejnego etapu migracji.
2. Wprowadzaj male, kontrolowane zmiany.
3. Po kazdej zmianie uruchom walidacje lokalnie.
4. Dla wiekszych zmian dopisz krotka notatke w `docs/session-notes.md`.
5. Jesli zmienia sie hardware lub piny, dopisz to do `docs/hardware-notes.md`.
6. Commituj po malych, logicznych etapach i wypychaj na GitHub.

## Lokalne komendy

Przy zalozeniu, ze masz zainstalowany Python 3.13 i ESPHome:

```powershell
python -m esphome config .\esphome\kh-aeration-min.yaml
python -m esphome compile .\esphome\kh-aeration-min.yaml
```

Mozna tez uzywac skryptow z katalogu `scripts/`.

Przy pracy w tym repo najwygodniej:

```powershell
.\scripts\esphome.cmd config .\esphome\kh-aeration-min.yaml
.\scripts\esphome.cmd compile .\esphome\kh-aeration-min.yaml
```

Jesli chcesz wgrac firmware po sieci:

```powershell
.\scripts\esphome.cmd upload .\esphome\kh-aeration-min.yaml
```

## Ustalenia dla kolejnych sesji

Jesli kolejny komputer lub kolejny Codex ma przejac prace:

- najpierw przeczytaj `README.md`
- potem sprawdz `docs/hardware-notes.md`
- potem przeczytaj `docs/session-notes.md`
- nastepnie otworz `esphome/kh-aeration-min.yaml`

Dzieki temu rozmowa nie musi byc jedynym zrodlem wiedzy o projekcie.
