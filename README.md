# Animal-Themed Custom Clock-Radio

A turtle-themed FM clock-radio built around a Raspberry Pi Pico 2 W, featuring a custom two-layer PCB, dual-interface control (physical + web), and a 3D-printed enclosure — developed for ECE 299 at the University of Victoria.

**Authors:** Oscar Bazylewich, Ethan Packer

![Prototype breadboard interface](docs/images/prototype-interface.png)
<!-- ^ Figure 6: Prototype Home interface -->

## Overview

This project combines digital timekeeping, FM radio tuning, and wireless connectivity into a single compact embedded system — all driven by one Raspberry Pi Pico 2 W programmed entirely in MicroPython. The system supports two fully synchronized control interfaces: a physical rotary encoder + button set, and a local web server accessible over Wi-Fi.

### Core Features
- **Clock/Alarm:** manual time setting, 12h/24h toggle, customizable alarm with snooze
- **FM Radio:** RDA5807M tuner with manual frequency and volume control
- **Dual UI:** rotary encoder/buttons on-device, plus a browser-based UI hosted on the Pico's own access point
- **Shared OLED display:** single SPI display multiplexed between clock and radio screens via a centralized state machine
- **Wi-Fi NTP sync:** corrects RTC drift (~1.73 s/day) without blocking the main asyncio loop

## Hardware Design

### Circuit / Schematic
The circuit integrates a Pico 2 W, RDA5807M FM tuner (I2C), SSD1306 OLED (SPI), LM386 audio amplifier, rotary encoder, and push buttons, with a MOSFET-switched linear regulator to allow USB or 9V battery operation.

![PCB schematic](docs/images/pcb-schematic.png)
<!-- ^ Figure 2: PCB Schematic -->

Key design decisions:
- Pull-down resistors on push buttons to prevent floating inputs
- RC debounce filtering (τ ≈ 1 ms) on rotary encoder lines
- Op-amp/regulator circuit adapted from UVic ECE lab reference designs

### PCB Layout (KiCad)
Custom two-layer PCB, **11.2 cm × 10.5 cm**, designed in KiCad with the following priorities:
- Radio module and SPI display physically separated to minimize signal coupling
- Extensive ground pours on both layers to reduce EMI
- Components placed tightly for signal integrity and easier soldering
- Thermal reliefs added to pads for solderability

![3D rendered PCB](docs/images/pcb-3d-render.png)
<!-- ^ Figure 3: 3D View of PCB -->

### Enclosure (SolidWorks)
A custom turtle-themed enclosure was 3D-printed in PLA with ±0.2 mm fit tolerances around the OLED display and controls, including front acoustic ports sized to match the speaker's active surface area.

![3D SolidWorks enclosure model](docs/images/enclosure-3d-model.png)
<!-- ^ Figure 4: 3D SolidWorks Model of Case -->

![Enclosure orthographic drawing](docs/images/enclosure-drawing.png)
<!-- ^ Figure 5: SolidWorks Drawing of Case (Top/Isometric/Side/Back views) -->

## Firmware

Written entirely in MicroPython using `asyncio` for non-blocking concurrency between:
- Hardware loop (button scanning, encoder ISR consumption, OLED rendering, alarm checking)
- Web server loop (parses HTTP requests, serves a live status page)

Both interfaces call the same shared state functions (`do_button_action`, `apply_encoder_delta`, `apply_absolute_value`), so physical controls and the web UI can never fall out of sync.

Full firmware source is included in [`firmware/`](./firmware) (or see `Appendices` in the final report).

## Bill of Materials

See [Table 2 in the final report](./ECE299FinalReport.pdf) for the full BOM — key components:

| Component | Part |
|---|---|
| Microcontroller | Raspberry Pi Pico 2 W |
| Display | SSD1306 OLED (SPI) |
| FM Tuner | RDA5807M |
| Audio Amp | LM386N-4/NOPB |
| Speaker | ABS-216-RC |

## Testing

Verified on a breadboard prototype prior to PCB assembly, using modified sample code from the course reference material to validate each peripheral (display, radio, encoder, RTC) individually before integration.

## Project Timeline

![Gantt chart](docs/images/gantt-chart.png)
<!-- ^ Figure 1: Project timeline Gantt chart -->

## References

Full citation list available in the [final report](./ECE299FinalReport.pdf), including datasheets for the RP2040/Pico 2 W, LM386, and RDA5807M.

---
📄 Full writeup: [`ECE299FinalReport.pdf`](./ECE299FinalReport.pdf)
