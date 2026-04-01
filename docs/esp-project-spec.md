# ESP Project Spec

Ten dokument opisuje zalozenia firmware dla projektu KH Keeper po stronie ESP32 i ESPHome.

Jego celem jest ustalenie:

- co urzadzenie ma robic
- jakie ma miec tryby pracy
- jakie encje maja istniec
- jakie stany ma obslugiwac procedura
- jakie dane maja byc zapisywane i pokazywane

To jest specyfikacja robocza v1.

## Cel firmware

Firmware ma lokalnie realizowac:

- sterowanie pompkami
- sterowanie aeracja
- odczyt pH
- odczyt temperatury
- wykonanie sekwencji pomiarowej KH
- podstawowe liczenie wyniku KH
- prezentacje danych w lokalnym panelu WWW

System ma pracowac lokalnie na ESP32:

- bez zaleznosci od Home Assistant
- z dostepem przez `web_server`
- z mozliwoscia dalszej rozbudowy o lokalny JS

## Zasada ogolna

Firmware ma byc:

- stanowe
- przewidywalne
- zatrzymywalne w kazdej chwili
- odporne na restart
- czytelne do kalibracji i testow

## Warstwy funkcjonalne

### 1. Warstwa hardware

Odpowiada za:

- sensory
- outputy
- odczyty napięc i temperatur
- sterowanie pompkami i MOSFETami

### 2. Warstwa procesu

Odpowiada za:

- sekwencje procedury KH
- przejscia miedzy etapami
- tryby `full`, `quick`, `service-test`
- obsluge `STOP`

### 3. Warstwa kalibracji

Odpowiada za:

- kalibracje pH
- kalibracje pompek
- przechowywanie wartosci trwalych

### 4. Warstwa UI/API

Odpowiada za:

- `web_server`
- encje `number`, `button`, `sensor`, `text_sensor`, `switch`, `select`
- statusy procesu
- dane diagnostyczne i serwisowe

## Docelowy hardware

Zakladany kierunek projektu:

- ESP32 `esp32dev`
- framework `esp-idf`
- ADS1115 po I2C
- DS18B20 na one-wire
- 3 pompki perystaltyczne sterowane PWM
- 1 pompka powietrza sterowana przez MOSFET
- lokalne UI przez `web_server`

## Zakladane wejscia i wyjscia

### Wejscia pomiarowe

- `ph_main_voltage`
- `ph_aux_voltage`
- `sample_temp_c`
- opcjonalnie pozniej:
  - `gas_co2_ppm`
  - `salinity_ppt`

### Wyjscia wykonawcze

- `pump1_out`
- `pump2_out`
- `pump3_out`
- `air_pump_out`
- opcjonalnie:
  - `status_led`

## Tryby pracy

### 1. Full measurement

Tryb glowny.

Cel:

- wykonac pelna procedure i zapisac wynik KH jako docelowy pomiar

Wymagania:

- komplet danych pomiarowych
- stabilna procedura
- zapis wyniku i statusu

### 2. Quick measurement

Tryb przyspieszony.

Cel:

- uzyskac szybszy wynik orientacyjny

Wymagania:

- skrocone czasy lub lagodniejsze kryterium stabilnosci
- wynik wyraznie oznaczony jako szybki lub orientacyjny

### 3. Service test

Tryb serwisowy.

Cel:

- sprawdzic mechanike procesu bez traktowania wyniku KH jako wiarygodnego

Wymagania:

- skrocone czasy
- mozliwosc obserwacji wszystkich etapow
- brak traktowania wyniku jako finalnego

### 4. Pump calibration

Tryb serwisowy dla kazdej pompki.

Cel:

- przeliczyc wydajnosc pompki na `ml_per_s`

### 5. pH calibration

Tryb serwisowy.

Cel:

- skalibrowac odczyt pH

## Model procesu KH

Procedura powinna byc zapisana jako maszyna stanow.

Minimalny zestaw stanow:

- `idle`
- `precheck`
- `flush`
- `sample_fill`
- `settle_before`
- `measure_before`
- `aeration`
- `settle_after`
- `measure_after`
- `calculate`
- `return_sample`
- `completed`
- `aborted`
- `error`

## Zasady przejsc miedzy stanami

1. Kazdy stan powinien miec jawny poczatek i koniec.
2. Kazdy stan powinien miec tekst statusowy dla UI.
3. `STOP` ma dzialac z kazdego stanu.
4. `STOP` ma:
   - wylaczyc wszystkie outputy
   - zatrzymac sekwencje
   - ustawic status `aborted`
5. Po restarcie urzadzenia outputy maja byc ustawione na `OFF`.

## Parametry konfiguracyjne

To sa parametry, ktore user powinien moc ustawic z UI.

### Parametry procesu KH

- `flush_in_ml`
- `flush_out_ml`
- `sample_ml`
- `return_factor`
- `aeration_full_s`
- `aeration_quick_s`
- `settle_before_s`
- `settle_after_s`
- `quick_factor`

### Parametry chemiczne

- `salinity_ppt`
- `co2_gas_ppm` albo inny parametr opisujacy gaz aerujacy
- wspolczynniki modelu KH jesli beda potrzebne

### Parametry pH

- `ph_cal_v_at_7`
- opcjonalnie `ph_cal_v_at_4`
- alternatywnie:
  - `ph_offset`
  - `ph_slope`

### Parametry kalibracji pompek

- `pump1_cal_time_s`
- `pump2_cal_time_s`
- `pump3_cal_time_s`
- `pump1_measured_ml`
- `pump2_measured_ml`
- `pump3_measured_ml`

## Dane trwale

To powinno byc przechowywane persistent.

- ustawienia procesu
- ustawienia chemiczne
- kalibracja pH
- kalibracja pompek
- ostatni znany tryb pracy tylko jesli ma sens

Nie trzeba na starcie trwale zapisywac:

- chwilowego statusu procesu
- flag wykonania biezacego pomiaru

## Encje wymagane w UI

### Sensors

- biezace pH
- pH przed pomiarem
- pH po aeracji
- ostatni KH
- temperatura probki
- wydajnosc pompki P1
- wydajnosc pompki P2
- wydajnosc pompki P3
- uptime
- Wi-Fi RSSI

### Text sensors

- status procesu KH
- aktualny tryb
- aktualny krok procedury
- komunikat bledu
- wersja firmware
- IP
- SSID

### Numbers

- czasy i objetosci procedury
- wartosci kalibracyjne
- parametry chemiczne
- cele dozowania

### Buttons

- start full
- start quick
- start service test
- stop global
- kalibracja pH
- start kalibracji pompki
- zapis kalibracji pompki
- prime / test pompki

### Selects

- wybor glownego kanalu pH
- wybor trybu testowego

### Switches

- reczne wlaczenie pompki
- reczne wlaczenie aeracji

## Dane do logowania i walidacji

Kazdy pomiar powinien zostawic dane diagnostyczne.

Minimalny zestaw:

- timestamp
- tryb pomiaru
- `pH_before`
- `pH_after`
- temperatura
- czas aeracji
- czas stabilizacji
- wynik KH z urzadzenia
- status zakonczenia

Jesli to mozliwe, warto tez logowac:

- `delta_pH`
- numer wersji modelu obliczeniowego
- numer wersji firmware

## Minimalne zabezpieczenia

Firmware powinno pilnowac:

- aby nie wlaczac dwoch pompek przeciwstawnych jednoczesnie
- aby po `STOP` wszystkie wyjscia byly OFF
- aby po restarcie nie wznowic przypadkiem starej procedury
- aby brak kalibracji nie dal pozornie wiarygodnego wyniku
- aby tryb service test nie byl raportowany jako normalny pomiar

## Zasady implementacyjne

1. Zmiany maja byc male i kontrolowane.
2. Zachowujemy ESPHome jako glowna platforme.
3. W pierwszej kolejnosci stabilnosc, potem wygoda.
4. Nie dodajemy skomplikowanego JS zanim nie ustabilizujemy procesu.
5. Najpierw procedure i dane, potem wyglad UI.

## Etapy wdrozenia

### Etap 1

- stabilna wersja minimalna
- podstawowy WebGUI
- dzialajacy STOP

### Etap 2

- temperatura
- lepsza kalibracja pompek
- dane diagnostyczne

### Etap 3

- testy z preparatami referencyjnymi KH
- strojenie procedury
- strojenie modelu

### Etap 4

- migracja na docelowy hardware:
  - ADS1115
  - DS18B20
  - 3 pompki
  - PWM

### Etap 5

- dopracowane lokalne UI
- ewentualny lokalny `khv1.js`

## Kryteria sukcesu

Firmware mozna uznac za gotowe do kolejnego etapu, gdy:

- procedura wykonuje sie przewidywalnie
- STOP zatrzymuje wszystko poprawnie
- pompki sa dobrze skalibrowane
- dane z UI sa czytelne
- wynik KH da sie porownywac z testem referencyjnym
- odchylenie od testu referencyjnego daje sie systematycznie zmniejszac
