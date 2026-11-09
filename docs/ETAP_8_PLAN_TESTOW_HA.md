# Euros OS — ETAP 8: kontrolowane testy w Home Assistant

Data przygotowania: 2026-11-09.
Status: **PRE-FLIGHT WYKONANY W GITHUB; TEST W REALNYM HA JESZCZE NIEWYKONANY.**

## 1. Pakiet testowy i zasady

- Repozytorium: `BudrysLP/EurosOS`.
- Gałąź przeznaczona do preflight: `feature/stage8-ha-preflight`.
- Źródło: zakończony ETAP 7, `feature/integration-failure-scenarios`.
- Wersja `manifest.json` jest nadal `0.1.0`; do identyfikowania wydania testowego używaj dokładnego SHA commitu, **nie numeru wersji**.
- Test na HA nie oznacza scalenia do `main`, publikacji upstream ani PR.
- Podczas testowania zachować wszystkie dotychczasowe encje, identyfikatory i ustawienia sterowania. **Nie usuwać istniejącej integracji i nie usuwać encji z rejestru.**
- Domyślnie weryfikacja tylko do odczytu: nie wysyłać komend zmiany trybu, temperatur ani harmonogramów pompy.
- Bez wyraźnej decyzji użytkownika nie kopiować plików do czynnej instalacji HA ani nie restartować jej.

## 2. Blokady i kontrola przed wdrożeniem

### Preflight kodu
- [x] `manifest.json` ma tylko jeden klucz `requirements` i deklaruje `paho-mqtt>=1.6,<3`; wcześniej drugi pusty klucz nadpisywał pierwszy.
- [x] GitHub Actions ma test wykrywający zduplikowane klucze JSON.
- [x] GitHub Actions wykonuje próbę instalacji rzeczywistej biblioteki Paho.
- [ ] Zanotować numer SHA ostatniego **zielonego** przebiegu dla gałęzi etap 8.
- [ ] Potwierdzić dostępność kopii poprzedniej, DZIAŁAJĄCEJ wersji Euros OS na docelowym HA.

### Backup HA OS (wykonuje operator w HA)
- [ ] Wejść w **Ustawienia > System > Kopie zapasowe**.
- [ ] Utworzyć **pełną kopię**, z zaznaczoną historią/rejestratorem (Recorder). Gdy baza jest zewnętrzna, wykonać oddzielną kopię jej danych.
- [ ] Pobrać plik kopii na inne urządzenie, poza hostem HA.
- [ ] Bezpiecznie zachować **emergency kit / klucz szyfrowania**; bez klucza nie będzie możliwe odtworzenie zaszyfrowanego backupu.
- [ ] Zachować dodatkową kopię **aktualnego** katalogu `/config/custom_components/euros_os` z instalacji HA do osobnego prywatnego archiwum.
- [ ] Sprawdzić, że archiwa istnieją i mają niezerowy rozmiar; nie publikować ich w GitHubie ani na czacie.

### Baseline
- [ ] Zanotować wersję Home Assistant Core i metodę instalacji integracji (HACS, ręcznie, inna).
- [ ] Zapisać aktualny komplet identyfikatorów encji pompy i EMS, osobno: `unique_id`, `entity_id`, `device_id`.
- [ ] Zapisać odczyty GEO i `METER_1`, licznik energii pobranej/oddanej dzisiaj, godzinę ich odczytu oraz status dostępności.
- [ ] Sprawdzić dostęp do logów HA i sposób cofnięcia zmian.
- [ ] Wybrać środowisko: preferowana oddzielna instancja testowa HA; ewentualny test na produkcji dopiero po potwierdzeniu backupu i akceptacji ryzyka.

## 3. Kontrolowana instalacja — wykonywana dopiero po akceptacji użytkownika

1. Utrwalić SHA kodu źródłowego i przechowywać osobno oryginalny katalog integracji.
2. Na oddzielnej instancji HA lub w zatwierdzonym oknie serwisowym podmienić **wyłącznie** pliki `/config/custom_components/euros_os` zawartością tego katalogu z **dokładnego** commitu testowego.
3. Nie modyfikować plików `.storage`, bazy Recorder, wpisów w rejestrze encji ani ustawień integracji.
4. Jeśli HACS zarządza integracją, nie używać „aktualizuj do main” ani przypadkowej gałęzi; dokumentować ręcznie podmieniony commit.
5. Po skopiowaniu plików wykonać restart HA Core **dopiero po akceptacji**.
6. Weryfikować pierwsze logi i stan encji, nie przełączać sterowania pompą.

## 4. Scenariusze akceptacyjne dla GEO + EMS

| ID | Scenariusz | Oczekiwany wynik |
|----|------------|------------------|
| HA8-01 | Uruchomienie integracji | Euros OS ładuje się bez błędów `ImportError`, `ModuleNotFoundError`, `ConfigEntryNotReady` |
| HA8-02 | GEO_1 | Pompa jest prawidłowo rozpoznana, zachowuje istniejące `entity_id` i `unique_id` |
| HA8-03 | METER_1 | EMS Dom aktualizuje wskazania, zachowuje poprzednie 33 sensory i 2 liczniki dzienne; nie powstają duplikaty |
| HA8-04 | Dostępność | Opóźnienie MQTT nie podaje błędnych zer; po powrocie wiadomości pomiary odzyskują dostępność |
| HA8-05 | Restart HA | Po restarcie działają GEO i EMS, energia dzienna odtwarza się bez fikcyjnego naliczenia |
| HA8-06 | Historia | Historia Recorder pozostaje powiązana z dotychczasowymi `entity_id` |
| HA8-07 | Nowy METER_N | Jeśli istnieje rzeczywisty licznik dodatkowy, tworzy się bez restartu i z własnymi identyfikatorami |
| HA8-08 | Brak dodatkowego licznika | Nie tworzą się hipotetyczne encje `METER_2`, `METER_3` |
| HA8-09 | Sterowanie | Dotychczasowe kontrolki pompy pozostają dostępne; **nie wysyłać testowych poleceń zmiany stanu bez zgody** |
| HA8-10 | Odłączenie i reload | Zgodnie z uzgodnioną procedurą diagnostyczną brak pozostawionego wątku/klienta MQTT i duplikatów |

**Uwaga:** test HA8-07 jest „nie dotyczy”, jeśli na danym urządzeniu nie występuje rzeczywisty `METER_2`; nie tworzyć fikcyjnych licznika na produkcyjnej pompie.

## 5. Kryteria natychmiastowego wycofania

- Integracja nie ładuje się albo przestaje odczytywać GEO lub `METER_1`.
- Nowe encje zastępują historyczne lub pojawiają się duplikaty o tym samym znaczeniu.
- Odczyt energii dziennej resetuje się błędnie, skacze nienaturalnie albo historia się rozłącza.
- W logach pojawiają się trwałe błędy wątków, MQTT lub błędy przy imporcie.
- Sterowanie pompą zmienia się bez zamierzonej interakcji.

## 6. Rollback — od najwęższego do najszerszego

1. Zatrzymać dalsze testy i zachować komunikaty błędów (bez haseł, pełnych MQTT payloadów z identyfikatorami i tajnych tokenów).
2. Nie usuwać wpisu integracji ani encji z rejestru.
3. Przywrócić wyłącznie poprzedni, oryginalny katalog `/config/custom_components/euros_os` z prywatnego archiwum i uruchomić ponownie HA Core w kontrolowanym oknie.
4. Sprawdzić powrót GEO, `METER_1`, identyfikatorów i historii.
5. Dopiero jeśli systemu nie da się odzyskać przez przywrócenie katalogu: rozważyć odtworzenie pełnego backupu HA, zgodnie z oficjalną dokumentacją. **Pełny restore może cofnąć inne zmiany i historię od daty backupu.**
6. Nie scalać zmian ani nie otwierać upstream PR przed zakończeniem testów.

## 7. Dziennik wykonania

| Pole | Wartość |
|------|---------|
| HA Core | nieustalone |
| Metoda instalacji Euros OS | nieustalona |
| SHA działającej wersji integracji | nieustalone |
| SHA wersji testowej | do wpisania po zatwierdzeniu |
| Lokalizacja backupu poza HA | niepotwierdzona |
| Data i wynik snapshotu encji | niepotwierdzone |
| Zgoda na podmianę plików / restart | NIE |
| Testy na HA | **NIE WYKONANO** |

## 8. Podstawa procedury

- Oficjalna dokumentacja Home Assistant: https://www.home-assistant.io/common-tasks/general/backups
- Oficjalne zadania Home Assistant OS: https://www.home-assistant.io/common-tasks/os
