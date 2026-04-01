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

## Jak pracowac

1. Dodaj lub zaktualizuj plik YAML w `esphome/`
2. Zapisz wymagania sprzetowe w `docs/hardware-notes.md`
3. Uruchom walidacje lub kompilacje lokalnie
4. Zacommituj zmiany i wypchnij je na GitHub

## Lokalne komendy

Przy zalozeniu, ze masz zainstalowany Python 3.13 i ESPHome:

```powershell
python -m esphome config .\esphome\test-esp32.yaml
python -m esphome compile .\esphome\test-esp32.yaml
```

Mozna tez uzywac skryptow z katalogu `scripts/`.

## Ustalenia dla kolejnych sesji

Jesli kolejny komputer lub kolejny Codex ma przejac prace:

- najpierw przeczytaj `README.md`
- potem sprawdz `docs/hardware-notes.md`
- nastepnie otworz odpowiedni plik w `esphome/`

Dzieki temu rozmowa nie musi byc jedynym zrodlem wiedzy o projekcie.
