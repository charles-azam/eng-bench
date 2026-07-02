# 03 — Instrumentation: Locations & Types

Instrument inventory, types, ranges/accuracies, and **measurement locations** from ANL-ART-47 §4.1–
§4.2. This section describes *where and how quantities are measured* — no measured values are included.

---

## 1. Data acquisition (§4.1)
- Control software LabVIEW 2012; all devices networked over TCP/IP (LUNA fiber system runs on a
  dedicated computer). DAQ boards at four points along the test section.
- National Instruments hardware (Table 11):

| Qty | Model | Description |
|---|---|---|
| 4 | cDAQ-9188 | 8-slot cDAQ chassis |
| 26 | NI-9214 | 16-ch isothermal thermocouple input module |
| 2 | NI-9205 | 32-ch ±200 mV–±10 V, 16-bit analog input |
| 4 | WSN-3212 | 4-ch, 24-bit programmable thermocouple input node (wireless, chimney TCs) |
| 1 | NI-9265 | 4-ch, 16-bit, 0–20 mA analog output (chimney damper actuators) |

---

## 2. Instrumentation summary (§4.2, Table 12)
| Measurement | Instrument | # | Range | Accuracy |
|---|---|---|---|---|
| Power | Eurotherm EPower | 40 | 0–12 kW | ±1% |
| Heat flux | iTi Inc. model BHT | 16 | 0–300 kW/m² | ±5% |
| Temp — gas space (Type-K) | — | 34 | 0–1,250 °C | ±1.1 °C or 0.4% |
| Temp — riser wall (Type-K) | — | 32 | 0–1,250 °C | ±1.1 °C or 0.4% |
| Temp — heated plate (Type-K) | — | 125 | 0–1,250 °C | ±1.1 °C or 0.4% |
| Temp — insulation wall (Type-K) | — | 193 | 0–1,250 °C | ±2.2 °C or 1.1% |
| Temp — ceramic heater (Type-K) | — | 40 | 0–1,250 °C | ±2.2 °C or 1.1% |
| Mass flow rate | Sierra 640S | 1 | 0–1 kg/s | ±1% + 0.3 kg/min |
| Chimney velocity | Dwyer 160F | 2 | ±0–45 m/s | ±8.3% |
| Riser ΔP | Dwyer 668-11 | 8 | ±64 Pa | ±1% |
| Chimney ΔP | Dwyer 607-0B | 2 | ±24 Pa | ±0.5% |
| Humidity | Dwyer RHP | 1 | 3–95 %RH | ±2% |
| Wind speed | Davis Vantage Vue | 1 | 1–80 m/s | ±5% |
| Wind direction | Davis Vantage Vue | 1 | 0–360° | ±3° |
| Outdoor humidity | Davis Vantage Vue | 1 | 1–100 %RH | ±3% |
| Outdoor temperature | Davis Vantage Vue | 1 | −40 to +65 °C | ±0.5 °C |
| Rainfall | Davis Vantage Vue | 1 | 0–6553 mm | ±4% |
| Barometric pressure | Davis Vantage Vue | 1 | 410–820 mmHg | ±0.8 mmHg |

Total thermocouples: **424**, Type-K. General accuracy ±2.2 °C or 0.75%; special-limits-of-error
(SLE) sensors (riser inlet/outlet gas, heated-plate surface) ±1.1 °C or 0.4%.

---

## 3. Wall thermocouples (§4.2.1)
- Majority on heated plates and surrounding insulated panels; flush-mounted for surface temperature.
- Heated-plate TC mounting (Fig. 30): wires passed through the 1″ plate via a 5/32″ dia hole
  countersunk 90° to a 1/4″ opening; bonded with high-temp cement; wires not joined at junction
  (circuit completed through the steel plate → detachment detectable as open circuit).

## 4. Heat-flux sensors (§4.2.2, Table 13)
- 16 sensors (up to 19 IDs listed), iTi Inc. model BHT with polyimide HFT; NIST-calibrated to 5%,
  rated to 300 °C. Two surface types: matte-black (ε ≈ 1.0, total flux) and reflective golden
  (ε ≪ 1.0, convective-only) — the pair separates convective vs radiative components.
- **Locations** (Table 13; "mm" = elevation along riser; the Kradiative column is a per-sensor
  calibration sensitivity in W/m²·mV, not a test measurement):

| # | Sensor ID | Kradiative | Finish | Location |
|---|---|---|---|---|
|1|950|20.20|matte|Hot side, duct 1, 100 mm|
|2|951|65.72|reflective|Hot side, duct 1, 100 mm|
|3|948|21.59|matte|Hot side, duct 1, 3500 mm|
|4|1358|15.92|matte|Hot side, duct 1, 7000 mm|
|5|933|21.73|matte|Cold side, duct 1, 7000 mm|
|6|939|18.15|matte|Cold side, duct 1, 7000 mm|
|7|1360|15.12|matte|Hot side, duct 7, 3500 mm|
|8|1362|41.07|reflective|Hot side, duct 7, 3500 mm|
|9|946|19.11|matte|Hot side, duct 7, 7000 mm|
|10|942|18.55|matte|Cold side, duct 7, 3500 mm|
|11|935|52.97|reflective|Cold side, duct 7, 3500 mm|
|12|940|24.68|matte|Hot side, duct 11, 3500 mm|
|13|941|22.07|matte|Hot side, duct 11, 7000 mm|
|14|936|62.43|reflective|Hot side, duct 11, 7000 mm|
|15|932|19.77|matte|Cold side, duct 11, 350 mm|
|16|938|22.88|matte|Cold side, duct 11, 700 mm|
|17|1355|15.54|matte|South side, duct 7, 3500 mm|
|18|1356|15.24|matte|North side, duct 7, 3500 mm|
|19|1359|44.62|reflective|Hot side, duct 1, 7000 mm|

## 5. Meteorological (§4.2.3, Table 14)
- Davis VantageVue weather station on Bldg. 308 roof, wireless to control room. Measures barometric
  pressure, temperature, humidity, wind speed & direction, rainfall. Polls 1 record/min.
- Resolutions/ranges: Baro 0.1 mmHg / 410–820 mmHg; Humidity 0.01 / 1–100%; Rainfall 0.2 mm /
  0–6553 mm; Temperature 0.1 °C / −40 to 60 °C; Wind direction 1° / 0–360°; Wind speed 0.1 m/s /
  1–80 m/s; Wind run 0.01 km.

## 6. Differential pressure (§4.2.4, Table 15)
- Riser ΔP: **Dwyer 668-11**, installed across 8 of the 12 risers (ducts 3, 5, 8, 10 omitted),
  bidirectional span ±0.25″ w.c. (±64 Pa). TCs co-located at each tap for gravitational-term
  separation.
- Chimney ΔP: **Dwyer 607-0B**, across both chimney networks, bidirectional ±0.10″ w.c. (±24 Pa).

## 7. Inlet flow & humidity (§4.2.5, Tables 16–17)
- **Sierra 640S** thermal mass flow meter located in the inlet downcomer, 24″ past the flow
  conditioner, extending to the duct centerline.
- **Dwyer RHP-2O11** humidity probe positioned 24″ above and on the centerline of the 24″ inlet
  entrance (inlet plenum).

## 8. Hot-wire probes (§4.2.6)
- Dantec constant-temperature anemometer (CTA) probes: 3-mm OD body, 10-µm tungsten wire; 0.2–500 m/s,
  max process temp 300 °C; operate at constant wire temp 242 °C; sampled at 50 kHz; co-located TC for
  temperature correction. Used at inlet and riser-outlet conditions.

## 9. Pitot tubes (§4.2.7)
- Two Dwyer model **160F** pitot tubes along the chimney ductwork (replaced chimney ΔP for isolating
  friction). 304 SS, K-factor Kp = 0.81, ±2% FS over 0–45 m/s. Treated as *relative* chimney-to-
  chimney velocities (installation < 10 L/D). Velocity relation: V = Kp·√(2ΔP/ρ).

## 10. Gas temperature (§4.2.8)
- Within each riser: Type-K TCs (ARI Industries T-22N-12BK8A-96(MOD)) extending to the lengthwise
  (10″) duct centerline. **Inlet TC** 0.75″ from the bottom lip on the cold side; **outlet TC** 4.0″
  below the top lip on the hot side.
- Outlet plenum: five instrumented insulation panels. The four vertical sides (N,S,E,W) each have
  6 embedded interior wall TCs; the top ceiling panel adds identical wall TCs plus **7 thermocouple
  rakes** for bulk gas temperature. Each rake carries 6 junctions, extending ~170 cm along the
  188-cm plenum height.

## 11. Luna fiber-optic distributed temperature (§4.2.9, Tables 18–19)
- Luna **ODiSi A-10** distributed Rayleigh-scatter fiber sensing. 155-µm polyimide-coated single-mode
  telecom fiber (Specialty Photonics CL POLY 1310). Max sensing length 10 m; ~10-mm spacing at 1 Hz
  (≈ 9,750 pts/s per 7.5-m fiber); temp range −50 to 300 °C; single-scan repeatability ±0.2 °C.
- Installed in 1/16″ OD × 0.030″ ID stainless capillaries (free expansion; secured only at head).
- **Locations:** two riser ducts, **#6 and #9** — 6 fibers on the outside wall and 5 within the gas
  space. Measurement is a temperature *difference* from baseline → 16 NIST-calibrated Type-K wall TCs
  positioned along the duct walls for baseline calibration.
- Special-handling requirements (Table 19): strain-free mounting, reference-fiber calibration,
  humidity correction (~0.15 °C shift per %RH), and post-install annealing.

---
Reference note: heater power controllers (40× Eurotherm EPower) and the heater control architecture
are described in **04_conditions.md** (§4.3), since they define the controlled power input.
