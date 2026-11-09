# Euros OS — ETAP 7: rozszerzone testy integracyjne i awaryjne

**Status:** testy symulacyjne zakończone pozytywnie; wdrożenie do HA nie zostało wykonane.

**Gałąź:** `feature/integration-failure-scenarios` (utworzona z `feature/compatibility-safety`).
**GitHub Actions, ostatni zielony przebieg kodu:** https://github.com/BudrysLP/EurosOS/actions/runs/42686384532
**Wynik:** Python 3.12 — 91/91; Python 3.13 — 91/91.

## Zakres zweryfikowany automatycznie

1. **MQTT:** wiadomości z błędnym JSON, nieprawidłowym `Devices`, nieobsługiwaną pompą, niekompletnym `Data` są odrzucane bez nadpisania stanu poprawną fikcyjną wartością.
2. **Tożsamość:** niespójne lub powielone wpisy pompy nie przełączają skonfigurowanego urządzenia.
3. **EMS:** `METER_1` oraz dodatkowe `METER_N` mają niezależne aktualizacje; częściowe wiadomości z licznikami nie zmieniają czasu ostatniej wiadomości pompy.
4. **Niejednoznaczne liczniki:** sprzeczne, podwójne wpisy tego samego `METER_N` w jednej wiadomości są odrzucane, zamiast stosowania zasady „ostatni wygrywa”.
5. **Rejestracja HA (symulacja):** `METER_1` zachowuje poprzednie `unique_id` i 2 liczniki dzienne. Dodatkowe liczniki tworzą odrębne encje bez nieuzasadnionych dziennych liczników domu. Zmiana kolejności i ponowne wiadomości nie duplikują encji.
6. **ALLINONE bez licznika:** nie tworzy urządzenia EMS.
7. **Wartości:** brakujące, niefinitywne lub nieprawidłowe odczyty temperatury pompy i mierników EMS nie są interpretowane jako rzeczywiste zero; prawidłowe zero i ujemny bilans są zachowane.
8. **Historia/dzienny licznik:** test odtworzenia stanu dziennej energii z danych RestoreSensor, jego aktualizacji i zachowania wartości przy `NaN`.
9. **Przerwy i ponowne połączenie:** ostatni poprawny stan zostaje zachowany; po rozłączeniu `connected` jest resetowany; stan i encje nie są usuwane. Wyłączenie integracji zatrzymuje worker MQTT.
10. **Wątki:** wywołania encji są kierowane do pętli HA; wyścig zamknięcia pętli nie zgłasza wyjątku do wątku MQTT.
11. **Bez publikowania:** testy odczytu i wykrywania potwierdzają brak wysyłania sterujących wiadomości MQTT.
12. **Zgodność:** cały odziedziczony zestaw testów GEO, EMS, HA API i etapu 4/5/6 pozostał zielony.

## Ograniczenia i dalsze kontrole

- Wykorzystano **podstawione klasy HA i symulator klienta MQTT**. To nie jest test na realnym Home Assistant, w rzeczywistym rejestrze encji ani na fizycznym urządzeniu.
- Nie zweryfikowano w rzeczywistym HA działania RestoreSensor, automatycznego tworzenia encji, długiego braku MQTT ani konfiguracji wielokrotnych urządzeń.
- Nie potwierdzono faktycznej ciągłości danych bazy Recorder, tylko zgodność identyfikatorów encji i logikę odtwarzania.
- Aktualny kod MQTT dziedziczy wyłączoną weryfikację certyfikatu TLS. Zmiany tego ustawienia nie wprowadzono bez sprawdzenia kompatybilności z lokalnym urządzeniem.
- Sterowanie pompą nie jest objęte testami komunikacji z urządzeniem; w tym etapie nie modyfikowano jego zachowania.

## ETAP 8 — warunki wejścia do kontrolowanego testu HA

1. Potwierdzić wybór środowiska testowego / metodę bezpiecznego wdrożenia.
2. Zabezpieczyć kopię konfiguracji integracji, zapis encji i kopię zapasową HA.
3. Sprawdzić na żywym GEO + EMS stabilność `unique_id`, odczytów, licznika dziennego, restartu, utraty MQTT i trybu pracy.
4. Zrobić kontrolę przywrócenia poprzedniej wersji, gdyby test nie przeszedł.
5. Nie scalać do `main` ani nie otwierać upstream PR bez odrębnej decyzji.
