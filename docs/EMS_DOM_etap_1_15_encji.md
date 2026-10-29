# EurosOS — EMS – Dom: etap 1 (15 dodatkowych encji)

Dotyczy fizycznego licznika `METER_1`, zamontowanego **za licznikiem ENEA i przed switchem PV/ME**. Ten punkt pomiarowy obejmuje całą instalację domu (w tym pompę ciepła), a **nie osobny pobór energii samej pompy**.

## Lista encji

Wszystkie są tylko do odczytu, pochodzą z komunikatów `Devices[*].Data` urządzenia `Name=METER_1, Type=METER`, nie wysyłają poleceń do pompy. Ich `unique_id` zależy od istniejącego prefiksu wpisu integracji i klucza MQTT; dla 10 wcześniejszych encji EMS pozostaje niezmieniony.

| Klucz MQTT | Nazwa w Home Assistant | Jednostka | Opis |
|---|---|---|---|
| `AB_LINE_VOLT_FL_1` | EMS – Dom – Napięcie L1–L2 | V | Napięcie między fazami L1 i L2 na przyłączu domu. |
| `BC_LINE_VOLT_FL_1` | EMS – Dom – Napięcie L2–L3 | V | Napięcie między fazami L2 i L3 na przyłączu domu. |
| `CA_LINE_VOLT_FL_1` | EMS – Dom – Napięcie L3–L1 | V | Napięcie między fazami L3 i L1 na przyłączu domu. |
| `A_PHA_ACT_POW_FL_1` | EMS – Dom – Moc czynna L1 | kW | Chwilowy bilans mocy czynnej na L1; znak oryginalny z licznika. |
| `B_PHA_ACT_POW_FL_1` | EMS – Dom – Moc czynna L2 | kW | Chwilowy bilans mocy czynnej na L2; znak oryginalny z licznika. |
| `C_PHA_ACT_POW_FL_1` | EMS – Dom – Moc czynna L3 | kW | Chwilowy bilans mocy czynnej na L3; znak oryginalny z licznika. |
| `TOTAL_RACT_POW_FL_1` | EMS – Dom – Moc bierna całkowita | kvar | Suma mocy biernej raportowana przez licznik; znak oryginalny. |
| `A_PHA_VIEW_POW_FL_1` | EMS – Dom – Moc pozorna L1 | kVA | Moc pozorna na fazie L1. |
| `B_PHA_VIEW_POW_FL_1` | EMS – Dom – Moc pozorna L2 | kVA | Moc pozorna na fazie L2. |
| `C_PHA_VIEW_POW_FL_1` | EMS – Dom – Moc pozorna L3 | kVA | Moc pozorna na fazie L3. |
| `TOTAL_APPA_POWER_FL_1` | EMS – Dom – Moc pozorna całkowita | kVA | Łączna moc pozorna raportowana przez licznik. |
| `A_PHA_POW_FAC_FL_1` | EMS – Dom – Współczynnik mocy L1 | brak | Współczynnik mocy fazy L1 (bezwymiarowy, ze znakiem). |
| `B_PHA_POW_FAC_FL_1` | EMS – Dom – Współczynnik mocy L2 | brak | Współczynnik mocy fazy L2 (bezwymiarowy, ze znakiem). |
| `C_PHA_POW_FAC_FL_1` | EMS – Dom – Współczynnik mocy L3 | brak | Współczynnik mocy fazy L3 (bezwymiarowy, ze znakiem). |
| `TOTAL_POW_FAC_FL_1` | EMS – Dom – Współczynnik mocy całkowity | brak | Całkowity współczynnik mocy na przyłączu domu. |

## Weryfikacja źródła

Przeanalizowano **1 659 próbek** `[EMS_DIAG] METER_1` z logu Home Assistant 28–29 października 2026. Każde z 15 pól wystąpiło w każdej próbce. Wartości pasują do jednostek:

- Napięcia międzyfazowe: ok. 400–415 V.
- Moce czynne fazowe: wartości dodatnie i ujemne; suma trzech faz zgadza się w przybliżeniu z `TOTAL_ACT_POW_FL_1`.
- Moce pozorne: dodatnie, rzędu ułamków i pojedynczych kVA.
- Współczynniki mocy: bezwymiarowe wartości w zakresie -1…1.

Wartości są przekazywane bez domyślnych zer i bez przeliczania skali; brakujące/niepoprawne pola skutkują stanem niedostępnym, a nie sztucznym `0`. Klasy Home Assistant: `voltage`, `power`, `reactive_power`, `apparent_power`, `power_factor`; każda z klas ma `measurement`.

**Uwaga:** Interpretacja znaku mocy biernej (indukcyjna/pojemnościowa) oraz szczegółowa konwencja znaku PF wymagają ewentualnie dokumentacji modelu licznika; nie zmieniamy ich umownie.

## Zakres zmian

Wdrożenie polega wyłącznie na odczycie istniejących danych `METER_1`. Nie zmienia starszych 12 encji EMS, encji pompy `GEO_1`, tematów MQTT ani sterowania. Nowe polskie opisy są dostępne także w atrybucie `opis` każdej z nowych encji.

Po skopiowaniu aktualnego `ems.py` i `sensor.py` do HA oraz ponownym załadowaniu integracji oczekiwana liczba encji EurosOS: **73** (w tym 27 urządzenia „EMS – Dom”), przy nadal **2 urządzeniach**.

## Pozostałe na później — 8 pól

- `POS_REAC_POW_FL_1`, `REW_REAC_POW_FL_1`: liczniki energii biernej — potwierdzić kierunek i jednostkę.
- `A_ACT_POW_FL_1`, `B_ACT_POW_FL_1`, `C_ACT_POW_FL_1`: dodatkowe sygnały mocy fazowej — dokładnie ustalić znaczenie.
- `POS_ACT_POW_FACTOR`, `REV_ACT_POW_FACTOR`, `TOTAL_ACT_POW_FACTOR`: pola pomocnicze współczynnika/kierunku.

**Stan:** wdrożone w kodzie gałęzi `feature/geo-support`, do potwierdzenia działania w Home Assistant.
