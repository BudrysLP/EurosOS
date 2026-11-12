# Euros OS — ETAP 9.2.5: strategia bezpieczeństwa MQTT/TLS

**Stan: 2026-11-12 — diagnoza w toku; problem P1.** Ten dokument służy wyłącznie przygotowaniu bezpiecznej strategii. Nie zmienia działania integracji ani konfiguracji pompy.

## Fakty ustalone na podstawie rzeczywistego odczytu

- Broker MQTT pompy odpowiada na porcie TLS 8883, udostępnia certyfikat X.509.
- Certyfikat ma subject CN `ee-agent`, issuer CN `An MQTT broker`, opis organizacji `OwnTracks.org`. To są napisy w certyfikacie, **nie dowód zaufania do CA**.
- Certyfikat jest ważny czasowo od 2020-05-12 do 2032-05-09.
- Zawiera SAN DNS `ee-agent`, `localhost` i adres IPv4 różny od aktualnego adresu urządzenia. Standardowe porównanie `checkip` z bieżącym IP powinno nie przejść.
- Upstream używa `ssl._create_unverified_context()` zarówno w `coordinator.py`, jak i w `config_flow.py`. Chroni to treść przed biernym podsłuchem, ale nie uwierzytelnia tożsamości serwera i jest ryzykiem MITM.
- `const.py` zawiera odziedziczony model statycznych poświadczeń MQTT. Nie dołączać wartości tych poświadczeń, logów uwierzytelniania ani pełnych MQTT payloadów do zgłoszeń i dokumentacji.
- Nie wiemy, czy firmware używa wspólnego certyfikatu, indywidualnego certyfikatu urządzenia, własnej CA ani czy wspiera wymianę certyfikatu bez ryzyka dla urządzenia.

## Bezpieczne testy read-only — terminal Home Assistant

Zastąpić `<IP_POMPY>` lokalnym adresem IP urządzenia. Polecenia nawiązują jedynie połączenie TLS i nie wykonują MQTT CONNECT, SUBSCRIBE ani PUBLISH.

### A. Zweryfikuj dopasowanie aktualnego IP (nie wymaga zaufanej CA)

```sh
openssl s_client -connect <IP_POMPY>:8883 -showcerts </dev/null 2>/dev/null | openssl x509 -noout -checkip <IP_POMPY> -fingerprint -sha256
```

Możliwy rezultat: `IP <IP_POMPY> does NOT match certificate`. SHA-256 to odcisk **publicznego certyfikatu**, nie klucz prywatny. Zachować go w prywatnej dokumentacji diagnostycznej, jeśli ma służyć jako przyszły punkt odniesienia.

### B. Zweryfikuj łańcuch certyfikatów i zgodność adresu

```sh
openssl s_client -connect <IP_POMPY>:8883 -verify_return_error -verify_ip <IP_POMPY> -brief </dev/null 2>&1
```

Błąd `unable to get local issuer certificate` albo `self-signed certificate in certificate chain` oznacza brak zaufanego łańcucha w lokalnym magazynie. Błąd `IP address mismatch` oznacza niezgodność nazwy/adresu. Ten test może zatrzymać się na *pierwszym* błędzie, dlatego A i B należy analizować osobno.

### C. Liczba certyfikatów wysyłanych przez broker (opcjonalnie)

```sh
openssl s_client -connect <IP_POMPY>:8883 -showcerts </dev/null 2>/dev/null | grep -c -- '-----BEGIN CERTIFICATE-----'
```

`-showcerts` pokazuje certyfikaty przesłane przez serwer; nie jest to dowód poprawności pełnego łańcucha.

## Decyzje projektowe — bez dokonywania zmian w pompie

1. **Preferowane, jeśli wspierane przez producenta:** serwer przedstawia certyfikat ważny dla faktycznej nazwy/IP urządzenia, podpisany przez zaufaną CA (publiczną lub bezpiecznie dostarczoną własną). Wtedy `ssl.create_default_context()`, `CERT_REQUIRED` i sprawdzanie nazwy.
2. **Po udokumentowaniu producenta:** opcjonalna własna CA wskazana przez użytkownika; wymaga osobnego testu dopasowania nazwy/IP. Samo zaufanie CA NIE naprawia niezgodności SAN.
3. **Bez potwierdzonego łańcucha:** pozostać przy dotychczasowej zgodnej z urządzeniem ścieżce tylko jako jawnie rozpoznanym ograniczeniu bezpieczeństwa, bez twierdzenia, że jest bezpieczna przed MITM; dalszy plan z autorem urządzenia/integracji. Nie stosować pozornej poprawy przez `tls_insecure_set(True)`.
4. **Certificate pinning / TOFU:** ewentualny tryb zaawansowany po uzgodnieniu modelu kluczy, niezależnego zaufanego kanału pozyskania fingerprintu, rotacji certyfikatów i możliwości technicznej weryfikacji **przed** wysłaniem danych uwierzytelniających. Nie implementować na ślepo.
5. **Statyczne poświadczenia:** sprawdzić, czy urządzenie rzeczywiście pozwala je zmieniać i jakie są skutki dla istniejących użytkowników. Nie usuwać/nie modyfikować poświadczeń w kodzie bez potwierdzonego mechanizmu konfiguracji.

## Kryteria zamknięcia 9.2.5

- [x] Ustalono, że certyfikat ma SAN niepasujący do bieżącego IP i jest czasowo ważny.
- [x] Potwierdzono w kodzie i dokumentacji Paho, że połączenie nie weryfikuje zaufania.
- [ ] Zebrano wynik `checkip` (A), diagnozę łańcucha (B) i opcjonalnie liczbę certyfikatów (C).
- [ ] Udokumentowano ostateczne ograniczenia i wybrany model wdrożenia, kompatybilny z realnym urządzeniem i innymi modelami Euros OS.
- [ ] Zweryfikowano docelową implementację i regresję albo formalnie uznano nierozwiązany problem za **blokadę wydania**.

**Nigdy** nie kopiować prywatnych kluczy, haseł, plików HA `.storage` ani kompletnych danych pompy do publicznego repozytorium.

## Źródła techniczne

- https://docs.openssl.org/master/man1/openssl-x509/
- https://docs.openssl.org/master/man1/openssl-s_client/
- https://docs.python.org/3/library/ssl.html
- https://eclipse.dev/paho/files/paho.mqtt.python/html/client.html
