# Euros OS — ETAP 9.5.2: zatwierdzony zakres i przygotowanie paczki testowej

**Data:** 12 listopada 2026. **Stan:** zakres testu zatwierdzony przez operatora; przygotowanie paczki w toku, ale NIE WYKONANO instalacji ani restartu HA.  
**Wersja produkcyjna — potwierdzona pełnym porównaniem 15/15 plików:**
`12d2502091d2364e7cb1803eef3bd523a31618de` (ETAP 8).  
**Wersja testowa — przypięta, niezmienna referencja runtime:**
`07a49bccc0cb590f3179983156c706dbe4675189` (ETAP 9.5, przed pracami nad dokumentacją i narzędziem staging).
**Gałąź przygotowania:** `feature/stage9-deployment-prep`. Dodatkowe skrypty testowe nie są instalowane w HA jako część integracji.

## 1. Co zatwierdził operator

Operator zaakceptował *zakres* testu na działającym HA: wymiana plików samej integracji Euros OS, maksymalnie **jeden** uzgodniony restart HA Core, odczytowa kontrola pompy GEO_1, EMS Dom, 73 encji, powiązania dwóch urządzeń, logów i ciągłości energii. Zakres **nie obejmuje** zmieniania nastaw pompy, konfiguracji MQTT, certyfikatów TLS, rejestrów `.storage`, historii Recorder ani instalowania dodatkowych urządzeń.

Zgoda na zakres **nie jest jeszcze poleceniem wykonania instalacji**. Przed podmianą kodu operator ma zobaczyć wynik stagingu i wyraźnie wskazać start okna serwisowego. Obecny etap przygotowania ma być całkowicie odwracalny.

## 2. Dlaczego przypinamy runtime do SHA

Rozwojowa gałąź `feature/stage9-ha-validation` może się zmieniać wraz z dokumentacją i testami. Aby uniknąć przypadkowej instalacji późniejszego, niesprawdzonego commitu, przygotowanie i planowane wdrożenie są oparte na **pełnym** SHA `07a49bccc0cb590f3179983156c706dbe4675189`.

- GitHub CI tego commitu: https://github.com/BudrysLP/EurosOS/actions/runs/43271935047 (**success**).
- Porównanie z ETAPEM 8: `ahead 114`, `behind 0`; zmiany runtime dotyczą 11 plików, a `geo.py`, `ems.py` i pliki tłumaczeń pozostają zgodne z bazą.
- Weryfikacja HACS ZIP w testach projektu wykazała poprawną strukturę 15 plików; **nie jest to jeszcze rzeczywisty test instalacji przez Marketplace**.
- W `manifest.json` wciąż jest `version: 0.1.0`, a w HACS metadata istnieje niespójne minimum wersji HA. To nie jest oficjalne wydanie; numeru wersji nie zmieniano podczas przygotowań.
- Home Assistant Core w CI: `2026.11.0` z Pythonem 3.14; terminal użytkownika potwierdził `Python 3.14.10`, a kopie noszą nazwę `2026.11.1`. Rzeczywistą wersję Core i szczegóły środowiska trzeba odczytać w HA przy kontroli przed restartem.

## 3. Narzędzie staging — bez ingerencji w produkcję

`scripts/prepare_ha_stage9_candidate.py` wykonuje **tylko** następujące czynności:

1. Pobiera z oficjalnego repozytorium GitHub archiwum źródeł dla wskazanego pełnego SHA oraz listę blobów `git/trees/<sha>?recursive=1`.
2. Wydziela **wyłącznie** `custom_components/euros_os/`, dokładnie **15** plików.
3. Porównuje każdy plik z hash SHA-1 obiektu Git: `SHA1("blob " + rozmiar + NUL + zawartość)`. To kontrola **tożsamości z commitem**, a nie ogólna rekomendacja SHA-1 do kryptograficznego uwierzytelniania.
4. Odrzuca nieoczekiwane ścieżki, symlinki, duplikaty, błędną domenę, niekompletny zestaw lub rozbieżność zawartości.
5. Zapisuje po weryfikacji nowy katalog prywatny `stage9_candidate_07a49bccc0cb/euros_os` obok `before.json` i backupu, a nie do `/config/custom_components/`. Nigdy nie nadpisuje istniejącego katalogu.
6. Wypisuje jedynie liczbę zweryfikowanych plików, SHA i ścieżkę stagingu. **Nie otwiera połączenia z MQTT, nie dokonuje zmian w HA, nie resetuje Core.**

**Polecenia dopiero po ponownej kontroli gotowości skryptu i CI; nie wykonano ich jeszcze na HA**:

```sh
curl -fLsS https://raw.githubusercontent.com/BudrysLP/EurosOS/260ad5d6b9c1c6d7988745f4771406ffb0a02965/scripts/prepare_ha_stage9_candidate.py \
  -o /config/euros_os_stage9_private/prepare_ha_stage9_candidate.py.new
python3 -m py_compile /config/euros_os_stage9_private/prepare_ha_stage9_candidate.py.new
mv /config/euros_os_stage9_private/prepare_ha_stage9_candidate.py.new \
   /config/euros_os_stage9_private/prepare_ha_stage9_candidate.py
python3 /config/euros_os_stage9_private/prepare_ha_stage9_candidate.py \
  --sha 07a49bccc0cb590f3179983156c706dbe4675189 \
  --stage-root /config/euros_os_stage9_private
```

**Skrypt stagingu przypięto do dokładnego commitu `260ad5d6b9c1c6d7988745f4771406ffb0a02965`, dla którego GitHub Actions przeszedł.** Odrębny commit z kodem integracji do wdrożenia to `07a49bccc0cb590f3179983156c706dbe4675189`. Po stagingu zachować sam wynik, nie załączać archiwów ani prywatnych plików.

## 3.1. Staging na HA — wynik operatora 12 listopada 2026

Operator uruchomił polecenie z przypiętym skryptem `260ad5d6b9c1c6d7988745f4771406ffb0a02965` i dokładnym SHA kandydata `07a49bccc0cb590f3179983156c706dbe4675189`. Otrzymany komunikat:

```text
STAGED ONLY: 15/15 verified integration files
COMMIT: 07a49bccc0cb590f3179983156c706dbe4675189
STAGING DIRECTORY: /homeassistant/euros_os_stage9_private/stage9_candidate_07a49bccc0cb/euros_os
LIVE INTEGRATION: UNCHANGED; NO HA RESTART
```

Różnica między ścieżką wskazaną jako `/config` i wypisaną jako `/homeassistant` może wynikać z rozwiązania symlinku przez `Path.resolve()`; polecenia dalszej weryfikacji powinny używać `/config/euros_os_stage9_private`, a nie sztywnej ścieżki fizycznej.

**Zaliczone: weryfikacja 15 blobów Git oraz zapis osobnego katalogu stagingu.** Nie potwierdzono jeszcze porównania zmian pomiędzy nową a żywą integracją po stagingu ani sygnału rozpoczęcia okna serwisowego. Instalacja/restart pozostają niewykonane.

## 3.2. Porównanie LIVE / STAGE i przegląd zmian — 12 listopada 2026

Operator wykonał odczytowe porównanie plików w `/config/custom_components/euros_os` i prywatnym stagingu `/config/euros_os_stage9_private/stage9_candidate_07a49bccc0cb/euros_os`. Wynik: **LIVE 15, STAGE 15, brakujące [], dodatkowe [], zmienione 10 plików**:

`__init__.py`, `binary_sensor.py`, `config_flow.py`, `const.py`, `coordinator.py`, `manifest.json`, `number.py`, `select.py`, `sensor.py`, `switch.py`.

Niezmienione pozostały: `geo.py`, `ems.py`, `discovery.py` i dwa pliki tłumaczeń. Porównanie z repozytorium GitHub potwierdziło te same 10 modyfikacji pomiędzy pełnymi SHA produkcji i kandydata.

**Audyt wpływu na działanie:**

- `coordinator.py` i `__init__.py`: dodany watchdog świeżości MQTT co 10 s, obsługa błędnego połączenia jako `ConfigEntryNotReady`, wywołanie stanu niedostępnego przy ciszy brokera, dodatkowe zabezpieczenia publikacji poleceń. **To realne zmiany zachowania** — po instalacji konieczna jest obserwacja logów, odczytów i zachowania połączenia.
- Połączenie TLS: w kodzie pozostaje `client.tls_set_context(ssl._create_unverified_context())`. Nie włączamy w tym etapie walidacji CA ani nazwy/IP. **Punkt 9.2.5 pozostaje otwartym ryzykiem bezpieczeństwa P1**; staging nie rozwiązuje jego przyczyny.
- `sensor.py`, `const.py`: migracja do natywnego API sensorów HA, naprawa klasy jednostek i osobny `RestoreSensor` dla starszego szacowania energii. GEO i rzeczywiste liczniki EMS zachowują identyfikatory; wymagają potwierdzenia historii w żywym HA.
- `number.py`, `select.py`, `switch.py`, `binary_sensor.py`: dostępność zależna od świeżości pompy, bezpieczniejsze warunki sterowania; `number.py` rozpoznaje tryb EMS w GEO.
- `config_flow.py`: zmiana treści komunikatów diagnostycznych, bez zmiany ustawień brokera. `manifest.json`: `iot_class` z `local_polling` na `local_push`; `version=0.1.0` nadal bez zmiany.
- Nie stwierdzono nowego mechanizmu ingerującego w certyfikat pompy lub ustawienia MQTT; nie jest to jednak gwarancja poprawnej komunikacji po rzeczywistym restarcie.

**Wniosek:** porównanie LIVE/STAGE zaliczone jako bramka przygotowania, ale nie stanowi testu działania. Przed instalacją konieczny jest jednoznaczny sygnał operatora o rozpoczęciu okna serwisowego. Gdy po restarcie wystąpią błędy połączenia, `unavailable`, nieoczekiwane problemy z encjami lub licznikiem energii, należy zatrzymać test i rozważyć rollback.

## 4. Przed instalacją — bramki STOP

- Prywatny `before.json` ma 73 encje, 2 urządzenia; użytkownik potwierdził jego utworzenie 12.11.2026.
- Pełny backup 1,2 GB poza HA, Emergency Kit oraz archiwum `euros_os_before_stage9_20261112.tar.gz` (66,5 KB, `tar -tzf` zaliczone). Wszystkie poświadczone przez operatora; nie wykonywano próbnego odtwarzania.
- Aktualna wersja LIVE zgodna 15/15 z ETAPEM 8. Przed instalacją, jeśli upłynął czas lub były jakiekolwiek inne aktualizacje, powtórzyć read-only kontrolę i/lub odświeżyć backup.
- Staging: 15/15 zweryfikowanych blobów, bez innych plików, pod prywatną ścieżką, nie w folderze produkcyjnym.
- Wyraźny sygnał rozpoczęcia testu w ustalonym oknie serwisowym i gotowość do rollbacku.
- Ze względu na otwarty TLS P1 nie modyfikować sposobu uwierzytelniania brokera. Nie traktować tymczasowego testu jako zgody na publikację końcowego PR.

## 4.1. Preflight operatora — wynik PASS

Operator wykonał ostatnią kontrolę przed zamianą plików Euros OS i udokumentował wynik:

```text
PREFLIGHT: PASS
Kandydat: 07a49bccc0cb
LIVE/STAGE: 15/15
Snapshot: 73 encje, 2 urządzenia
Archiwum rollback: OK
Wolne miejsce: 99248 MB
HA: bez zmian, bez restartu
```

Sprawdzono manifest źródła, zgodność 15 ścieżek LIVE/STAGE, istnienie snapshotu rejestru oraz odczyt archiwum rollback. Wynik dopuszcza wyłącznie przeprowadzenie przygotowanej zamiany kodu w zatwierdzonym oknie; nie oznacza, że podmiana lub restart już nastąpiły.

## 4.2. Podmiana kodu — potwierdzona, Core jeszcze nie uruchomiony ponownie

Operator uruchomił kontrolowaną podmianę katalogu produkcyjnego z prywatnego stagingu. Terminal pokazał:

```text
FINAL CHECK: PASS
SWAP: PASS
LIVE: 15/15 new files verified
ROLLBACK: /config/euros_os_stage9_private/euros_os_live_rollback_stage9
HA CORE: NOT RESTARTED
```

**Potwierdzone:** na dysku działa już zestaw 15 plików z kandydata `07a49bccc0cb590f3179983156c706dbe4675189`, a poprzedni katalog przeniesiono do prywatnego `euros_os_live_rollback_stage9`. Poprzednio wykonane archiwum `tar.gz` nadal istnieje. To **nie jest jeszcze dowód działania nowego kodu**, ponieważ HA Core nie uruchamiano ponownie po podmianie. Nie sprawdzano ponownie MQTT, odczytów, rejestrów ani historii.

**Następna bramka:** sprawdzić konfigurację `ha core check`, a po wyniku bez błędów przeprowadzić jeden zatwierdzony `ha core restart` (bez safe mode). Po starcie zbadać GEO/EMS, logi i prywatne porównanie 73 encji. W razie problemów nie wykonywać automatycznych kolejnych restartów ani nie przywracać całego backupu bez analizy.

## 4.3. Restart zgłoszony przez operatora — do weryfikacji

Po poprawnej podmianie katalogu operator otrzymał polecenie `ha core check && ha core restart` i odpowiedział **„Zrobione”**. Przyjmujemy, że wykonał polecenie, ale nie dysponujemy osobnym wynikiem `ha core check` ani odczytem statusu po ponownym uruchomieniu. **Nie oznacza to jeszcze zaliczenia testów funkcjonalnych.**

**Wynik rejestrów po restarcie (12.11.2026): zaliczony.** Operator uruchomił prywatny skrypt `ha_registry_snapshot.py capture` zapisując `after.json`, a następnie `compare` z historycznym `before.json`. Udokumentowano:

```text
before_entities=73
after_entities=73
missing_entities=0
new_entities=0
changed_entity_ids=0
changed_device_links=0
before_devices=2
after_devices=2
missing_devices=0
new_devices=0
changed_parent_links=0
PASS: Registry identity unchanged
```

Porównanie potwierdza, że identyfikatory i relacje urządzeń pozostają niezmienione. **Nie dowodzi jeszcze dostępności i aktualności wartości MQTT, działania sterowania ani ciągłości statystyk energii.** Oba prywatne pliki JSON pozostają w HA, bez przekazywania do repozytorium.


## 4.4. Funkcjonalne odczyty GEO_1 i EMS Dom po restarcie — PASS

Użytkownik przesłał zrzuty integracji Home Assistant po aktualizacji. Na ekranie integracji wyświetlają się **2 urządzenia i 73 encje**, w tym `GEO_1` (38 encji, firmware `870.12`) oraz `EMS – Dom` (`METER_1`, 35 encji). Widoczne sensory nie mają statusów `unavailable`. Kolejne zdjęcia pokazują niewielkie zmiany wartości, co wspiera wniosek o bieżącej telemetrii.

**GEO_1:** tryb `EMS`, stan `CWU`, sprężarka i pompy (CO, źródła) działają według wskazań, CWU zadana 50,0°C i aktualna 46,1°C, temperatura wewnętrzna 21,9°C, zewnętrzna 3,0°C. Górne źródło zasilanie 53,5°C, powrót około 50,0–50,2°C, dolne źródło 7,1°C i 2,2°C, delta 4,9°C. Nie wysyłano nowych poleceń do urządzenia.

**EMS Dom:** chwilowy bilans około 3,24 kW, L1 0,85 kW, L2 około 1,47–1,48 kW, L3 0,92 kW (suma zgodna w granicach zaokrągleń); dzienny import 10,15 kWh i eksport 0,17 kWh, sieć 50 Hz, napięcia fazowe 231–233 V. Odczyty prądów i współczynników zmieniają się pomiędzy ujęciami.

**Obserwacja do weryfikacji, nie powód do natychmiastowego rollbacku:** pomocnicze techniczne sensory EMS pokazują na L2 około -0,13 do -0,15 kW i techniczny `Współczynnik TOTAL` = -1.0. Znaczenie pól i konwencję znaków należy porównać z oryginalnym payloadem/definicjami przed uznaniem tego za usterkę; nie edytować współczynników ani konfiguracji.

**Wniosek:** 9.5.3 zaliczono jako test powdrożeniowej rejestracji i odczytów GEO/EMS razem z wynikiem `PASS: Registry identity unchanged`. Nie weryfikowano ciągłości historii Recorder/Panelu Energia (9.5.4), pełnego odpornościowego cyklu MQTT (9.5.5) ani logów HA Core (9.5.6). Zrzuty nie stanowią niezależnego testu wszystkich 73 wartości.

**Kolejne kroki bez ingerencji w działanie pompy:**
1. **WYKONANE:** prywatny `after.json`, 73 encje i 2 urządzenia.
2. **WYKONANE:** porównanie `before`/`after`, 0 różnic, wynik PASS.
3. **GEO/EMS ZALICZONE:** odczyty po restarcie i 73/2 wpisy rejestrów zachowane; **OTWARTE:** ciągłość historii energii (9.5.4).
4. **OTWARTE:** logi Core; nie wykonywać dodatkowego restartu bez osobnej decyzji operatora.



Po osobnym zatwierdzeniu faktycznej wymiany (NIE w tym kroku):

1. Wykonać kontrolowane zastąpienie tylko `/config/custom_components/euros_os/` zweryfikowanymi 15 plikami (najpierw kopia działającego katalogu, później atomowe przełączenie, bez modyfikacji `.storage`).
2. Jeden kontrolowany restart **HA Core**, bez restartu całego hosta, gdy operator wyraźnie uruchomi okno testu.
3. Sprawdzić, że `GEO_1` i `EMS – Dom` są dostępne, działają 73 encje i 2 urządzenia, brak ERROR/traceback przypisywalnych integracji oraz brak zmiany ID.
4. Utworzyć prywatny `after.json` i porównać z `before.json`: `missing_entities = new_entities = changed_entity_ids = changed_device_links = missing_devices = new_devices = changed_parent_links = 0`.
5. Sprawdzić rzeczywiste odczyty i ciągłość energii po restarcie, bez wysyłania komend sterujących pompą.
6. Jeśli choć jedna krytyczna kontrola zawiedzie: natychmiast przerwać test, przywrócić **archiwum bieżącego kodu** bez kasowania encji i historii, a restart Core wykonać w niezbędnym zakresie — możliwość dodatkowego restartu awaryjnego wymaga akceptacji operatora.

**Brak zgody na oficjalne wydanie, aktualizację przez Marketplace i końcowy PR**. Otwarte TLS `9.2.5` (P1) oraz `9.3.9` nie są zamykane przez staging.

## 6. Stan checklisty

ETAP 9: **34/69 zadań**. 9.5.1, 9.5.2, 9.5.3 i 9.5.7 zakończone. Na podstawie raportu operatora podmieniono 15 plików, wykonano jeden restart, porównanie rejestrów 73/2 dało PASS, a widoczne odczyty GEO/EMS są aktywne i spójne. Otwarta jest historia energii (9.5.4), bezpieczeństwo obsługi stale/reconnect w żywym środowisku (9.5.5), logi (9.5.6) i decyzja końcowa (9.5.8).
