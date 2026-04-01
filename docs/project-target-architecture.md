# Project Target Architecture

Ten dokument opisuje docelowa strukture projektu KH Keeper CO2 i plan dojscia do wersji finalnej.

Ma sluzyc jako:

- instrukcja dla kolejnych sesji
- plan porzadkowania projektu
- opis efektu finalnego, do ktorego dazymy

## Stan na dzis

Na ten moment projekt jest w fazie kontrolowanego prototypu.

Mamy:

- repo GitHub
- dzialajacy minimalny firmware testowy
- lokalne WebGUI przez ESPHome
- dwa wejscia pH z ADC ESP32
- dwie pompki sterowane jako `gpio switch`
- jedna pompke powietrza
- kalibracje pH 7.00
- kalibracje pompek na podstawie czasu i wpisanej objetosci
- tryby:
  - `full`
  - `quick`
  - `service test`
- statusy procesu
- dokumentacje metodologii i zalozen firmware
- testowa kompilacje firmware zakonczona sukcesem

Na ten moment nie ma jeszcze:

- ADS1115
- DS18B20
- 3 pompki
- PWM / LEDC
- lokalnego `khv1.js`
- finalnego modelu obliczania KH opartego o walidacje referencyjna

## Co zrobilismy do tej pory

### 1. Uporzadkowalismy projekt

- projekt jest juz w repo
- mamy historie commitow
- mamy dokumentacje robocza

### 2. Zbudowalismy minimalny firmware

Aktywny plik:

- `esphome/kh-aeration-min.yaml`

To jest test bench, a nie finalna architektura produktu.

### 3. Ustalilismy metode pomiaru KH

Założenie:

- `pH_before` jako diagnostyka
- aeracja probki
- `pH_after` jako glowny parametr do wyliczenia KH
- walidacja wyniku na podstawie testow referencyjnych KH

### 4. Ustalilismy podejscie do obliczen

- `PyCO2SYS / CO2SYS` jako model referencyjny offline
- brak Pythona na ESP32
- docelowo uproszczony solver albo lookup table na ESP

### 5. Ustalilismy podejscie do kalibracji pompek

- czas kalibracji ustawiany przez usera
- user wpisuje ile ml podala pompka
- firmware liczy `ml_per_s`
- dozowanie liczymy przez `target_ml / ml_per_s`

### 6. Ustalilismy role testow referencyjnych

To jest bardzo wazne:

- fizyczne testy KH przy uzyciu preparatow sa referencja
- firmware i model beda stroione wzgledem tych wynikow

## Co ma byc efektem finalnym

Docelowo system ma byc lokalnym sterownikiem i miernikiem KH dla akwarium morskiego, opartym o ESP32, z lokalnym panelem WWW i stabilna procedura pomiarowa.

Finalny efekt ma miec:

- stabilny hardware
- stabilna procedure KH
- lokalne UI
- powtarzalne kalibracje
- bezpieczne sterowanie pompkami
- mozliwosc dalszej rozbudowy produktowej

## Docelowa struktura plikow

Docelowo projekt nie powinien zostac jednym wielkim YAML-em.

Najlepszy docelowy uklad:

```text
ESP-KH/
├─ README.md
├─ docs/
│  ├─ hardware-notes.md
│  ├─ session-notes.md
│  ├─ kh-methodology.md
│  ├─ esp-project-spec.md
│  └─ project-target-architecture.md
├─ esphome/
│  ├─ kh-keeper-main.yaml
│  ├─ secrets.yaml
│  ├─ packages/
│  │  ├─ core.yaml
│  │  ├─ ui.yaml
│  │  ├─ ph.yaml
│  │  ├─ temperature.yaml
│  │  ├─ pumps.yaml
│  │  ├─ pump_calibration.yaml
│  │  ├─ kh_procedure.yaml
│  │  ├─ kh_model.yaml
│  │  └─ diagnostics.yaml
│  └─ www/
│     └─ khv1.js
└─ scripts/
   ├─ esphome.cmd
   ├─ validate-test.cmd
   └─ compile-test.cmd
```

## Rola poszczegolnych plikow docelowych

### `esphome/kh-keeper-main.yaml`

Glowny plik urzadzenia.

Powinien zawierac tylko:

- dane urzadzenia
- `esp32`
- `wifi`
- `api`
- `ota`
- `web_server`
- odwolania do `packages`

Nie powinien zawierac calej logiki procesu.

### `esphome/packages/core.yaml`

Podstawy systemu:

- `logger`
- `time`
- `globals`
- bezpieczny `on_boot`
- podstawowe stale systemowe

### `esphome/packages/ui.yaml`

Warstwa UI:

- `number`
- `button`
- `select`
- `text_sensor`
- grupy `web_server`
- porzadek panelu WWW

### `esphome/packages/ph.yaml`

Logika pH:

- ADS1115 albo tymczasowo ADC
- kanaly pomiarowe
- glowny sensor pH
- kalibracja pH
- status glownego kanalu

### `esphome/packages/temperature.yaml`

Temperatura:

- DS18B20
- sensory temperatury
- dane do modelu KH

### `esphome/packages/pumps.yaml`

Sterowanie pompkami:

- outputy
- PWM / LEDC
- stale poziomy pracy
- reczne testy pompek
- interlocki

### `esphome/packages/pump_calibration.yaml`

Kalibracje pompek:

- zadany czas kalibracji
- wpisywanie realnej objetosci
- przeliczanie `ml_per_s`
- zapis wartosci trwałych

### `esphome/packages/kh_procedure.yaml`

Najwazniejszy pakiet procesu:

- skrypty
- maszyna stanow
- `full`
- `quick`
- `service test`
- `STOP`

### `esphome/packages/kh_model.yaml`

Model obliczeniowy:

- parametry chemiczne
- wzor lub lookup table
- logika liczenia KH
- wersjonowanie modelu

### `esphome/packages/diagnostics.yaml`

Diagnostyka:

- uptime
- Wi-Fi RSSI
- IP
- wersja
- bledy
- dane pomocnicze do serwisu

### `esphome/www/khv1.js`

Docelowy lokalny frontend.

Powinien byc dodany dopiero wtedy, gdy:

- encje beda stabilne
- proces bedzie stabilny
- bedziemy wiedzieli, jakie UI ma byc finalnie potrzebne

## Docelowy plan dzialania

### Etap 1. Stabilny test bench

Cel:

- miec dzialajacy firmware do realnych testow na stole

Zakres:

- obecny `kh-aeration-min.yaml`
- testy start/stop
- testy pompek
- testy pH
- testy przeplywu

### Etap 2. Dane referencyjne

Cel:

- zebrac pierwsze dane z fizycznych testow KH

Zakres:

- pomiary z preparatami referencyjnymi
- porownania z wynikiem z urzadzenia
- notowanie odchylen

### Etap 3. Ustabilizowanie procedury

Cel:

- dopracowac kolejnosc procedury i czasy

Zakres:

- flush
- sample fill
- settle before
- aeration
- settle after
- return
- warunki konca procedury

### Etap 4. Migracja hardware

Cel:

- przejsc z wersji minimalnej na hardware blizszy docelowemu

Zakres:

- ADS1115
- DS18B20
- 3 pompki
- PWM / LEDC

### Etap 5. Rozbicie YAML-a na pakiety

Cel:

- przejsc z jednego duzego pliku na architekture modulowa

Wazna zasada:

- rozbijamy dopiero wtedy, gdy obecna logika bedzie wystarczajaco stabilna
- nie rozbijamy "dla samego rozbicia"

### Etap 6. Model KH v2

Cel:

- przejsc z prostego modelu do modelu strojonego na danych referencyjnych

Zakres:

- analiza offline
- lookup table lub uproszczony solver
- walidacja na realnych pomiarach

### Etap 7. Finalne UI

Cel:

- dopracowac lokalny panel WWW

Zakres:

- `khv1.js`
- lepszy panel statusow
- szybsze sterowanie
- czytelny workflow kalibracji i pomiaru

## Jak chcemy, zeby wygladal efekt finalny

Docelowa wersja ma byc:

- lokalna
- stabilna
- modularna
- zrozumiala dla kolejnych sesji i kolejnych osob
- gotowa do dalszej rozbudowy bez chaosu

Firmware finalny powinien miec:

- jeden glowny plik YAML
- logiczny podzial na pakiety
- stabilna procedure KH
- jasne statusy
- dobra kalibracje pompek
- osobne tryby:
  - pomiar pelny
  - pomiar szybki
  - test serwisowy
- wynik KH walidowany wzgledem testow referencyjnych

## Co ma wiedziec kolejny Codex

Jesli inny Codex przejmie projekt, powinien wiedziec:

1. To nie jest nowy projekt od zera, tylko kontrolowanie budowany firmware KH Keeper.
2. Obecny aktywny firmware to:
   - `esphome/kh-aeration-min.yaml`
3. Obecna wersja jest test bench do realnych prob, nie finalna wersja produktu.
4. Prawda referencyjna dla KH ma pochodzic z fizycznych testow preparatami KH.
5. `PyCO2SYS` sluzy jako model referencyjny offline, nie jako runtime na ESP.
6. Projekt ma docelowo zostac rozbity na pakiety YAML, ale dopiero po ustabilizowaniu logiki.
7. Priorytet:
   - stabilnosc procesu
   - walidacja
   - dopiero potem wyglad i rozbudowane UI

## Co robic jutro

Najlepszy nastepny krok:

1. Podpiac fizyczne ESP32.
2. Wgrac obecny firmware testowy.
3. Sprawdzic:
   - czy panel dziala
   - czy pH odczytuje sensownie
   - czy pompki ruszaja
   - czy aeracja dziala
   - czy `STOP` dziala z kazdego miejsca
4. Wykonac pierwsze kalibracje pompek.
5. Zaczac zbierac pierwsze dane do porownania z testami referencyjnymi KH.
