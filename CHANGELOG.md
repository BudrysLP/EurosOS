# Changelog — Euros OS

Zmiany historyczne wydań oficjalnych utrzymuje autor repozytorium `McKoPcIu/EurosOS`. Niniejszy plik opisuje **proponowany, niewydany pakiet zmian w forku** i nie ustanawia nowego numeru wydania.

## [Unreleased] — kandydat do jednego skonsolidowanego PR (stan: 2026-11-13)

### Dodano
- Wykrywanie rodzajów pomp `FriskoGEO`, `FriskoATMO`, `FriskoALLINONE` i wybór właściwej pompy niezależnie od kolejności `Devices`.
- Obsługa pompy GEO: specjalizowane etykiety i odczyty, delta T dolnego/górnego źródła, rozpoznawanie trybu i stanu pracy, wykrywanie wersji firmware.
- Osobne urządzenie EMS – Dom / `METER_1`: 33 bezpośrednie pola diagnostyki energii i 2 dzienne liczniki; dane METER_1 obejmują cały dom, nie samą pompę.
- Dynamiczne rozpoznawanie kolejnych `METER_N` wyłącznie po odebraniu faktycznych danych MQTT.
- Testy regresyjne, testy prawdziwych API Home Assistant Core ze sztucznym MQTT, generowanie archiwum `euros_os.zip`.

### Zmieniono
- Kontrola świeżości danych osobno dla pompy i liczników; mechanizm watchdog, reakcja na rozłączenie i odzyskanie MQTT, ochrona podczas unload.
- Weryfikacja i blokowanie niepotwierdzonych komend sterujących; brak niezweryfikowanego przełączenia GEO do EMS lub z EMS do AUTO.
- Bezpieczniejsze przetwarzanie wartości numerycznych oraz przywracanie szacowanego licznika energii w starszych modelach.
- Zgodność z nowszym API encji Home Assistant; zachowanie dotychczasowych identyfikatorów GEO/EMS jako priorytet.
- Dokumentacja zakresu, instalacji i bezpiecznego wycofania aktualizacji.

### Zweryfikowano
- 154/154 testów offline na każdej z wersji Python 3.12, 3.13, 3.14, plus 6 testów HA Core 2026.11.0 w *historycznym* przebiegu CI z 12.11.2026. Nowy finalny commit wymaga powtórzenia testów.
- Na rzeczywistym HA Core 2026.11.1: 73/73 encje, 2 urządzenia; 35/35 EMS i 38/38 GEO w stanie dostępnym; w obu tabelach Recorder 32/32 serie statystyczne EMS z punktami przed i po aktualizacji. Nie zbadano wszystkich luk i poprawności pomiarów.

### Ograniczenia / blokady wydania
- **P1 TLS:** aktualny kod nie weryfikuje tożsamości certyfikatu MQTT; lokalny CA nie jest niezależnie uwierzytelniony, a adres IP HA nie zgadza się z SAN. Nie deklarować problemu jako naprawionego.
- **P1 przegląd danych uwierzytelniających:** w `const.py` istnieją stałe uwierzytelniania MQTT. Przed wydaniem przeprowadzić audyt źródła i dystrybucji poświadczeń, uzgodnić z autorem bezpieczną procedurę ich obsługi. Nigdy nie kopiować tych wartości do PR, dzienników czy dokumentacji.
- Brak testów na fizycznych `FriskoATMO`, `FriskoALLINONE` oraz dodatkowych `METER_2/METER_3`.
- Instalacja/aktualizacja w HACS/Marketplace z końcowego archiwum oraz minimalna wersja HA nieustalone.
- Numer wydania i decyzja o publikacji należą do autora. Otwarty PR #3 musi zostać rozstrzygnięty przed jednym końcowym PR.

Dalsze kroki: [lista kontrolna](docs/RELEASE_CANDIDATE_CHECKLIST.md).
