# Summary

This Pull Request introduces a consolidated set of improvements to the Euros OS Home Assistant integration, including **FriskoGEO heat pump support, whole-home EMS energy monitoring, automatic device discovery, MQTT reliability improvements, Home Assistant API compatibility fixes, expanded automated tests, and updated documentation**.

The implementation was developed and validated against a real **Euros GEO 06 SH heat pump**, an associated **METER_1 electricity meter**, and **Home Assistant Core 2026.11.1**.

This contribution consolidates our previous development work into a clean branch based on upstream `main`, avoiding the long history of experimental development commits.

The main objectives are:

- Extend Euros OS beyond the existing ATMO / ALLINONE functionality.

- Preserve backward compatibility with existing installations.

- Support different heat pump types and dynamically detected electricity meters.

- Improve MQTT connection handling and Home Assistant entity availability.

- Prevent unsupported or unverified heat pump control operations.

- Provide automated regression coverage and reproducible release packaging.

- Prepare the integration for easier maintenance and future development.

---

## 1. FriskoGEO heat pump support

Added model-specific support for `FriskoGEO` devices.

### Supported functionality

- Automatic recognition of GEO heat pumps.

- GEO-specific temperature sensors.

- Heating and domestic hot water operating state detection.

- GEO-specific operating mode detection.

- Firmware version reporting.

- Ground-source and heating-side temperature difference calculations.

- Improved handling of missing, invalid and unsupported measurements.

### Operating state detection

The integration distinguishes:

- `CO` – space heating.

- `CWU` – domestic hot water heating.

- `IDLE` – idle state.

- `OFF` – disabled state.

The state calculation requires valid controller flags. Missing or malformed data must not be interpreted as a valid `IDLE` or `OFF` state.

### Temperature difference calculations

Added GEO-specific calculated sensors:

- Ground-source temperature difference (ΔT).

- Heating-side temperature difference (ΔT).

Calculations use the corresponding validated temperature readings and reject invalid or missing values.

### Unsupported GEO measurements

Measurements that are not available or reliably reported by the tested GEO controller are excluded from new GEO entity creation.

This includes selected air-source-specific measurements, unsupported compressor/electrical fields, and unverified pressure calibration controls.

The integration must not substitute whole-home EMS measurements for missing heat pump measurements.

Existing Home Assistant entity registry entries and their history are preserved.

---

## 2. GEO operating modes and control safety

Added GEO-specific mode recognition, including:

- `AUTO`

- `EMS`

- `TIME`

- `AWAY`

- `OFF`

Mode detection is based on observed controller telemetry.

**Important safety restriction:**

Reading the EMS operating mode is supported, but the MQTT commands required to safely activate EMS mode or perform certain EMS-to-AUTO transitions have not been fully validated.

Therefore:

- Switching to EMS from Home Assistant is deliberately blocked.

- Unverified transitions from EMS to AUTO are blocked.

- Invalid or unsupported mode requests are rejected.

- No optimistic state update is performed when a command is rejected.

- Existing supported controls remain available where their behavior has been validated.

Users should use the official Euros Smart application for unsupported mode transitions.

These restrictions are intentional and should not be removed without validation of the corresponding MQTT control protocol.

---

## 3. Whole-home EMS telemetry – METER_1

Added support for the physical electricity meter identified as `METER_1`.

Home Assistant creates a separate device:

**EMS – Dom**

The tested installation exposes **35 EMS entities**:

- 33 direct telemetry and diagnostic readings.

- 2 calculated daily energy counters.

### Supported measurements

The EMS implementation includes:

- Instantaneous grid power balance.

- Total imported electricity.

- Total exported electricity.

- Voltage for individual phases.

- Current for individual phases.

- Line-to-line voltages.

- Active power for individual phases.

- Total reactive power.

- Apparent power.

- Power factor.

- Grid frequency.

- Reactive energy counters.

- Selected technical and diagnostic measurements.

- Daily imported energy.

- Daily exported energy.

All EMS entities are **read-only**.

### Important distinction

`METER_1` represents the **whole-home electricity meter**, not a dedicated electricity meter for the heat pump.

Its power and energy values must not be interpreted as direct heat pump consumption.

Technical diagnostic values are also distinguished from standard energy measurements and should not be used for billing without independent validation.

---

## 4. Dynamic discovery of additional electricity meters

Extended the integration to support dynamically detected `METER_N` devices.

The implementation supports the discovery architecture for devices such as:

- `METER_1`

- `METER_2`

- `METER_3`

- Additional `METER_N` identifiers.

Additional meters are created only when their corresponding device data is present in the MQTT payload.

The discovery logic does not create fictional or predefined meters when no corresponding physical device is detected.

### Multi-device handling

The discovery mechanism:

- Identifies supported heat pump types.

- Does not rely on `Devices[0]`.

- Handles varying device order.

- Rejects ambiguous heat pump selection.

- Separates heat pump data from meter data.

- Prevents unrelated meter updates from being interpreted as heat pump updates.

Physical `METER_2` and `METER_3` devices were not available for hardware testing; those scenarios were validated using simulated MQTT payloads.

---

## 5. MQTT connection reliability

Improved the MQTT coordinator lifecycle and handling of connection failures.

### Included improvements

- Handling unexpected MQTT disconnections.

- Reconnection and recovery scenarios.

- Connection timeout handling.

- Cleanup of MQTT resources during integration unload.

- Prevention of orphaned MQTT worker activity.

- Safer handling of callbacks and asynchronous Home Assistant updates.

- Better isolation of heat pump and electricity meter data.

- Protection against stale data being presented as current.

- Rejection of invalid or malformed MQTT payloads.

### Entity availability

The integration separately evaluates data freshness for the heat pump and individual meters.

This prevents a new EMS reading from incorrectly making stale heat pump data appear current, and vice versa.

The coordinator also blocks control operations when the heat pump connection or data freshness is insufficient.

Automated tests cover timeout boundaries, disconnect/reconnect behavior and repeated integration setup/unload cycles.

---

## 6. Home Assistant API compatibility

Updated entity implementations to improve compatibility with modern Home Assistant versions.

Changes include:

- Correct use of modern `SensorEntity` properties.

- Improved native units and state classes.

- Removal of deprecated entity property patterns.

- Better handling of `unknown` and `unavailable` states.

- Validation of numerical sensor values.

- Rejection of `NaN`, infinity, and invalid numeric measurements.

- Improved energy sensor metadata.

- Preservation of existing unique identifiers.

### Estimated energy restoration

Improved handling of the legacy estimated electricity consumption sensor for models where the required input data is available.

The implementation uses `RestoreSensor` and processes new measurement samples rather than incrementing consumption whenever Home Assistant reads the sensor state.

This prevents repeated state reads from artificially increasing the estimated energy total.

For GEO devices, unsupported estimated energy measurements remain excluded.

---

## 7. Backward compatibility

Preserving existing installations was an important requirement throughout development.

The implementation was designed to retain:

- Existing configuration entries.

- Entity unique identifiers.

- Entity IDs.

- Device associations.

- Existing supported controls.

- Historical Home Assistant statistics.

- Compatibility with the existing ATMO and ALLINONE code paths.

### Real installation validation

On the tested Home Assistant installation, the registry comparison confirmed:


Component | Result
-- | --
GEO entities | 38/38
EMS entities | 35/35
Total entities | 73/73
Registered devices | 2/2
Unexpected entity ID changes | 0
Unexpected device registry changes | 0

The 32 identified EMS Recorder statistics series contained records before and after the tested code update. This supports preservation across the observed period, not a guarantee of every historical sample's completeness or accuracy.

---

## 8. Automated testing

### Final Pull Request CI

The consolidated release branch passed GitHub Actions:

**Run:** [Euros OS – CI #43431288027](https://github.com/BudrysLP/EurosOS/actions/runs/43431288027)

| Test environment | Result |
| --- | --- |
| Python 3.12 – unit and MQTT simulation | PASS |
| Python 3.13 – unit and MQTT simulation | PASS |
| Python 3.14 – unit and MQTT simulation | PASS |
| Home Assistant Core 2026.11 API | PASS |

**All four CI jobs completed successfully.**

The previously documented development suite executed 154 unit/simulation tests per Python version, plus six Home Assistant Core tests using mocked MQTT communication.

### Covered test scenarios

- Pump discovery and identification.

- GEO and ATMO device isolation.

- Multiple meters.

- Different MQTT device ordering.

- Invalid and incomplete payloads.

- Entity registration and identity preservation.

- Repeated setup/unload cycles.

- MQTT timeout and reconnection.

- Data freshness and availability.

- Daily energy counters.

- Counter restoration and day changes.

- Invalid numerical values.

- Prevention of duplicate energy accumulation.

- Unsupported GEO control commands.

- Home Assistant API compatibility.

- Release archive structure.

These tests do not replace hardware validation of all supported pump and meter models.

---

## 9. Real hardware validation

Testing was also performed on an operating Home Assistant installation.

### Test environment

- **Home Assistant Core:** 2026.11.1

- **Heat pump:** Euros GEO 06 SH

- **Controller type:** FriskoGEO

- **Heat pump device:** GEO_1

- **Electricity meter:** METER_1

- **EMS monitoring:** Whole-home electricity measurements

- **MQTT transport:** TLS 1.3, port 8883

### Verified results

- GEO and EMS devices were correctly registered.

- All 73 expected entity registry entries were retained.

- GEO and EMS entities were available during the documented checks.

- Existing unique identifiers and device associations were preserved.

- New EMS measurements continued to arrive.

- Recorder retained the identified EMS statistics series across the observed update.

- No unintended changes to the heat pump operating parameters were required.

Hardware validation was limited to the devices available in this installation.

---

## 10. Security and MQTT authentication – existing behavior intentionally retained

Following a review of MQTT authentication and transport security, the project owner decided to **retain the existing MQTT authentication credentials and TLS connection implementation unchanged** for this contribution.

### Factory MQTT credentials

The integration currently uses manufacturer-shared MQTT credentials defined in `const.py`.

These values are intentionally preserved for compatibility with existing devices.

No new username/password configuration flow or credential migration is introduced by this PR.

### TLS certificate verification

The existing implementation uses:

`ssl._create_unverified_context()`

This allows encrypted TLS communication but **does not verify the MQTT broker certificate or authenticate the server identity**.

Diagnostic tests confirmed that the tested broker uses TLS 1.3 and provides a certificate chain, but the currently configured IP address does not match the server certificate's SAN entries.

The broker's local CA has not been independently authenticated.

**This is a known security limitation, not a resolved vulnerability.**

Possible consequences include man-in-the-middle attacks and exposure of the shared MQTT credentials if an attacker can intercept or redirect the connection.

The recommended operational mitigation is to restrict MQTT port 8883 to a trusted local network and avoid exposing the broker to the public Internet.

A future contribution may introduce properly authenticated TLS after the manufacturer-specific CA and hostname requirements are established.

**This PR does not claim to fix TLS certificate verification.**

---

## 11. Documentation and release preparation

Updated or added documentation covering:

- Supported heat pump models.

- GEO-specific functionality.

- Whole-home EMS monitoring.

- Additional meter discovery.

- Entity and measurement limitations.

- Installation requirements.

- Safe upgrade procedures.

- Backward compatibility.

- Rollback instructions.

- MQTT security limitations.

- Automated testing and hardware validation.

- Release preparation and known limitations.

Relevant files include:

- `README.md`

- `CHANGELOG.md`

- `docs/RELEASE_UPGRADE_AND_ROLLBACK.md`

- `docs/RELEASE_CANDIDATE_CHECKLIST.md`

- Technical test and compatibility documentation.

### Release packaging

Added a reproducible archive builder:

`scripts/build_release_zip.py`

The archive uses the expected filename:

`euros_os.zip`

The generated ZIP places the integration files directly at the archive root, as required by the current release configuration.

Packaging validation is included in the automated test workflow.

No official upstream GitHub Release or version tag is created by this Pull Request.

---

## 12. Known limitations

The following limitations are explicitly acknowledged:

- Physical hardware testing was performed with FriskoGEO and METER_1, not every supported device model.

- ATMO and ALLINONE compatibility was covered by automated tests but not independently verified on physical devices during this project.

- Additional physical METER_2/METER_3 devices were not available for validation.

- GEO EMS mode activation and certain mode transitions remain intentionally blocked until their control commands are validated.

- Whole-home EMS readings do not represent heat pump-only electricity consumption.

- Some technical measurement fields should not be interpreted as certified billing data.

- Existing MQTT TLS certificate verification remains disabled by design, as documented above.

- The final minimum supported Home Assistant version has not been established for older releases.

- A complete installation/upgrade test through the final published Marketplace/HACS release remains a release-stage verification task.

These limitations should be retained in the release documentation rather than hidden.

---

## 13. Versioning and release decision

The current integration manifest still declares version `0.1.0`, while the upstream repository has previously published newer release tags.

We intentionally did not assign a new official version number in this contribution.

**The maintainer should determine the next release version and minimum supported Home Assistant version before publishing a release.**

The existing `hacs.json` metadata and previously documented minimum Home Assistant version also require final reconciliation against the chosen compatibility policy.

The code has been tested against Home Assistant Core 2026.11, but compatibility with older Home Assistant versions is not guaranteed by the available tests.

---

## 14. Relationship to previous Pull Requests

This contribution consolidates the work previously discussed in the GEO / EMS development effort.

Relevant previous PRs:

- [PR #3 – NumberEntity compatibility fix](https://github.com/McKoPcIu/EurosOS/pull/3)

- [PR #4 – GEO and whole-home EMS support](https://github.com/McKoPcIu/EurosOS/pull/4)

At the time of preparation, PR #3 remained open and PR #4 was closed.

Some compatibility changes overlap with PR #3.

The consolidated PR is intended to provide a single, maintainable set of changes for review instead of multiple partially overlapping Pull Requests.

The maintainer can decide how to reconcile or close the earlier PR.

---

## 15. Files and implementation areas

The main modified or added implementation files include:

**Core integration**

- `__init__.py`

- `coordinator.py`

- `config_flow.py`

- `const.py`

- `discovery.py`

- `geo.py`

- `ems.py`

**Home Assistant entities**

- `sensor.py`

- `binary_sensor.py`

- `number.py`

- `select.py`

- `switch.py`

**Testing and tooling**

- `tests/`

- `tests_ha/`

- `.github/workflows/euros-os-stage4-tests.yml`

- `scripts/build_release_zip.py`

- `scripts/run_unit_tests_strict.py`

- `scripts/ha_registry_snapshot.py`

**Documentation**

- `README.md`

- `CHANGELOG.md`

- Release, compatibility, testing and upgrade documentation under `docs/`.

---

## 16. Maintainer review requests

I would particularly appreciate feedback on:

- FriskoGEO integration architecture and compatibility with existing pump models.

- EMS / METER_N automatic discovery and entity naming.

- Backward compatibility with existing Home Assistant installations.

- The deliberate restrictions on unverified GEO control operations.

- The decision to retain the current MQTT authentication and TLS behavior, including the documented security risks.

- The minimum supported Home Assistant version.

- The preferred next release version.

- The relationship between this consolidated PR and the earlier NumberEntity PR #3.

I am happy to make additional changes and run further regression tests based on the maintainer's feedback.

Thank you for maintaining Euros OS and for reviewing this contribution.
