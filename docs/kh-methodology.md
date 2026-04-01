# KH Methodology

Ten dokument opisuje zalozenia chemiczne i proceduralne dla projektu KH Keeper.

Nie jest to jeszcze finalna specyfikacja produktu, ale roboczy punkt odniesienia do dalszego firmware i testow.

## Cel

Projekt ma wyznaczac KH w akwarium morskim na podstawie:

- pomiaru pH probki przed aeracja
- aeracji probki do stanu bliskiego rownowadze z gazem o znanym CO2
- pomiaru pH probki po aeracji
- modelu ukladu weglanowego

W praktyce:

- `pH_before` sluzy glownie do diagnostyki i kontroli procesu
- `pH_after` jest kluczowe do obliczenia KH

## Zalozenia chemiczne

W wodzie morskiej KH odpowiada w praktyce alkalicznosci ukladu weglanowego.

Podczas samej aeracji:

- zmienia sie rozpuszczone CO2
- zmienia sie pH
- alkalicznosc nie powinna sie zmieniac od samej wymiany CO2 z gazem

To oznacza, ze po doprowadzeniu probki do rownowagi z gazem o znanym CO2 da sie wyznaczyc alkalicznosc z:

- `pH_after`
- `CO2_gas`
- temperatury
- zasolenia

Model referencyjny do badan i walidacji:

- `PyCO2SYS / CO2SYS`

Wniosek projektowy:

- do researchu, symulacji i walidacji uzywamy `PyCO2SYS`
- na ESP32 nie uruchamiamy Pythona
- na ESP32 pozniej wdrazamy uproszczony solver albo lookup table przygotowane offline

## Co jest krytyczne dla wiarygodnego wyniku

### 1. Znane CO2 gazu aerujacego

To najwazniejsza rzecz poza samym pH.

Jesli aeracja odbywa sie:

- powietrzem z pokoju, wynik bedzie zalezal od aktualnego CO2 w pomieszczeniu
- powietrzem z zewnatrz, wynik zwykle bedzie stabilniejszy
- gazem o kontrolowanym CO2, wynik bedzie najbardziej powtarzalny

Wniosek:

- trzeba docelowo zalozyc albo stale zrodlo powietrza, albo pomiar CO2 gazu aerujacego

### 2. Dokladnosc i stabilnosc pH

Blad pH bardzo mocno psuje wynik KH.

W praktyce trzeba zalozyc:

- regularna kalibracje
- dobra stabilizacje temperatury probki
- odczekanie na uspokojenie sondy po zmianach przeplywu i aeracji
- pozniejsza walidacje wzgledem testu referencyjnego

### 3. Temperatura i zasolenie

Model ukladu weglanowego zalezy od:

- temperatury
- zasolenia

Wniosek:

- temperatura musi byc mierzona
- zasolenie mozna na start przyjac jako stale, ale docelowo powinno byc parametrem konfiguracyjnym

## Rola pH przed i po aeracji

### `pH_before`

Zastosowanie:

- diagnostyka nadmiaru CO2 w probce
- sprawdzenie, czy pobrana probka zachowuje sie sensownie
- porownanie przed i po aeracji
- kontrola jak mocno probka byla przesunieta od rownowagi

### `pH_after`

Zastosowanie:

- glowny parametr do obliczania KH po doprowadzeniu probki do rownowagi

Wniosek:

- procedura nie moze opierac sie tylko na "czasie aeracji"
- musi uwzgledniac warunek konca procesu albo przynajmniej bardzo dobrze dobrane czasy

## Strategia obliczeniowa

### Etap 1. Model referencyjny offline

Budujemy narzedzie badawcze poza ESP32:

- Python
- `PyCO2SYS`

To narzedzie ma sluzyc do:

- sprawdzania wrazliwosci wyniku na pH, temperature, salinity i CO2
- generowania tabel lub uproszczonych wzorow
- porownania z testami recznymi KH

### Etap 2. Algorytm urzadzenia

Na ESP32 wdrazamy:

- albo prosty solver przyblizony
- albo lookup table
- albo empiryczny model skalibrowany do realnego ukladu

Na start najbezpieczniej:

- nie udawac "laboratoryjnej chemii"
- zbudowac powtarzalny proces
- porownywac wyniki do testu referencyjnego

## Tryby pracy

Trzeba rozdzielic trzy osobne rzeczy.

### 1. Full measurement

To jest docelowy pomiar KH.

Proponowana kolejnosc:

1. flush komory
2. pobranie probki
3. stabilizacja przed pierwszym odczytem
4. odczyt `pH_before`
5. aeracja
6. stabilizacja po aeracji
7. odczyt `pH_after`
8. obliczenie KH
9. zwrot albo oproznienie probki

### 2. Quick measurement

To jest szybszy pomiar orientacyjny.

Zasady:

- krotsze czasy bazowe
- nadal zachowujemy ten sam porzadek procesu
- wynik oznaczamy jako mniej pewny
- nie traktujemy go jako rownowaznego z trybem full

### 3. Service test

To nie jest pomiar KH, tylko test mechaniczny i procesowy.

Zasady:

- przyspieszone czasy, np. 5 do 10 procent normalnych wartosci
- bez raportowania finalnego KH jako wiarygodnego pomiaru
- sluzy do sprawdzenia:
  - pompek
  - przeplywu
  - aeracji
  - przejsc miedzy etapami
  - dzialania STOP

## Jak wyznaczac koniec aeracji

Sa dwie glowne mozliwosci.

### Wersja minimalna

- staly czas aeracji
- staly czas stabilizacji po aeracji

Plusy:

- proste do wdrozenia

Minusy:

- wynik zalezy od warunkow probki i moze byc mniej powtarzalny

### Wersja lepsza

- aeracja do osiagniecia stabilnosci pH

Przykladowa logika:

- mierz pH co kilka sekund
- zakoncz aeracje, gdy zmiana pH w oknie czasu spadnie ponizej progu
- potem odczekaj dodatkowy czas stabilizacji

Wniosek:

- docelowo warto przejsc na warunek stabilnosci pH zamiast samego czasu

## Kalibracja pompek

To trzeba traktowac osobno od chemii.

### Zasada

Dla kazdej pompki wykonujemy pomiar:

- uruchom pompke na zadany czas `t_cal`
- zmierz rzeczywista objetosc `V_meas`

Nastepnie:

- `ml_per_s = V_meas / t_cal`

Aby podac zadana objetosc:

- `time_s = target_ml / ml_per_s`

### Wnioski projektowe

- kalibracja musi byc osobna dla kazdej pompki
- kalibracja jest wazna tylko dla konkretnego trybu pracy pompki
- jesli zmienimy PWM, napiecie lub warunki hydrauliczne, kalibracja moze przestac pasowac
- najlepiej miec stale, ustalone warunki pracy pompki i kalibrowac tylko ten jeden tryb

### Procedura kalibracji

1. Uzytkownik wybiera czas kalibracji
2. Uklad uruchamia pompke na ten czas
3. Uzytkownik wpisuje realny wynik w ml
4. Uklad liczy `ml_per_s`
5. Wynik zapisujemy jako wartosc trwała

### Dalszy kierunek

Lepiej przejsc z jednego sztywnego czasu 30 s na:

- konfigurowalny czas kalibracji
- nadal z prostym przeliczeniem czasu do objetosci

## Proponowany zestaw procedur operacyjnych

### SOP pomiaru full

1. Upewnij sie, ze pH jest skalibrowane
2. Upewnij sie, ze pompki maja aktualna kalibracje
3. Wykonaj flush
4. Pobierz probke
5. Odczekaj stabilizacje
6. Zapisz `pH_before`
7. Aeruj probke
8. Odczekaj stabilizacje po aeracji
9. Zapisz `pH_after`
10. Oblicz KH
11. Zwroc albo oproznij probke

### SOP szybkiego pomiaru

1. Ta sama procedura co full
2. Krotsze czasy bazowe
3. Wynik oznacz jako orientacyjny

### SOP testu serwisowego

1. Przejdz cala sekwencje skroconymi czasami
2. Nie zapisuj wyniku KH jako wiarygodnego
3. Sprawdz:
   - czy pompki ruszaja
   - czy aeracja dziala
   - czy STOP zatrzymuje wszystko
   - czy statusy i UI sa poprawne

## Co trzeba zbadac dalej

Najwazniejsze otwarte tematy:

1. Jakie zrodlo gazu aerujacego bedzie docelowe
2. Czy mierzymy CO2 gazu aerujacego, czy zakladamy wartosc stala
3. Jakie zasolenie przyjmujemy na start
4. Czy szybki pomiar ma byc tylko orientacyjny, czy tez "prawie docelowy"
5. Czy wynik na ESP32 ma byc:
   - solverem przyblizonym
   - lookup table
   - modelem empirycznym

## Zrodla referencyjne

- PyCO2SYS paper:
  - https://gmd.copernicus.org/articles/15/15/2022/gmd-15-15-2022.html
- PyCO2SYS docs:
  - https://pyco2sys.readthedocs.io/en/v2-beta-release/detail/
- NOAA CO2SYS:
  - https://www.ncei.noaa.gov/access/ocean-carbon-acidification-data-system/oceans/CO2SYS/co2rprt.html
- USGS pH measurement guidance:
  - https://pubs.usgs.gov/publication/tm9A6.4
- Potentiometric pH sensor evaluation:
  - https://c-can.info/an-evaluation-of-potentiometric-ph-sensors-in-coastal-monitoring-applications-ocean-acidification/
