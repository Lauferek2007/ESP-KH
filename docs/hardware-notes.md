# Hardware Notes

## Jak uzupelniac

Dla kazdego modulu dopisujemy:

- nazwe urzadzenia
- typ plytki
- uzyte piny
- zasilanie
- peryferia
- ograniczenia i uwagi montazowe

## Szablon

### Nazwa modulu

- Plytka:
- Framework:
- Zasilanie:
- Wi-Fi:
- Czujniki:
- Przekazniki / wyjscia:
- Piny:
- Uwagi:

## KH Keeper Min

- Plytka: ESP32 DevKit / `esp32dev`
- Framework: ESPHome na `esp-idf`
- Zasilanie: do uzupelnienia
- Wi-Fi: lokalny `web_server` + fallback AP
- Czujniki:
  - pH A0 przez ADC ESP32 na `GPIO32`
  - pH A1 przez ADC ESP32 na `GPIO33`
- Przekazniki / wyjscia:
  - `pump_p1_in` na `GPIO25`
  - `pump_p2_out` na `GPIO26`
  - `air_pump` na `GPIO27`
- Piny:
  - `GPIO25` - pompka P1
  - `GPIO26` - pompka P2
  - `GPIO27` - pompka powietrza
  - `GPIO32` - ADC pH A0
  - `GPIO33` - ADC pH A1
- Uwagi:
  - to jest wersja minimalna startowa
  - nie ma jeszcze ADS1115
  - nie ma jeszcze DS18B20
  - nie ma jeszcze PWM / LEDC
  - nie ma jeszcze 3 pompki
