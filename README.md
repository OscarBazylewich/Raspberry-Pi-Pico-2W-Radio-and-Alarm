# Animal-Themed Custom Clock-Radio

A turtle-themed FM clock-radio built around a Raspberry Pi Pico 2 W, featuring a custom two-layer PCB, dual-interface control (physical + web), and a 3D-printed enclosure — developed for ECE 299 at the University of Victoria.

**Authors:** Oscar Bazylewich, Ethan Packer

![Final product](<img width="1697" height="903" alt="pcbschematic" src="https://github.com/user-attachments/assets/30369861-8623-44e2-a987-57beeab3edea" />)

## Overview

This project combines digital timekeeping, FM radio tuning, and wireless connectivity into a single compact embedded system, driven entirely by one Raspberry Pi Pico 2 W programmed in MicroPython. The system supports two fully synchronized control interfaces: a physical rotary encoder + button set, and a local web server hosted on the Pico's own Wi-Fi access point.

### Core Features
- **Clock/Alarm:** manual time setting, 12h/24h toggle, customizable alarm with snooze
- **FM Radio:** RDA5807M tuner with manual frequency and volume control
- **Dual UI:** rotary encoder/buttons on-device, plus a browser-based UI over Wi-Fi
- **Shared OLED display:** single SPI display multiplexed between clock and radio screens via a centralized state machine
- **Wi-Fi NTP sync:** corrects RTC drift without blocking the main control loop

## Hardware Design

### Circuit / Schematic
The circuit integrates a Pico 2 W, RDA5807M FM tuner (I2C), SSD1306 OLED (SPI), LM386 audio amplifier, rotary encoder, and push buttons, with a MOSFET-switched linear regulator stage that allows the system to run off either USB power or a 9V battery.

![PCB schematic](<img width="1697" height="903" alt="pcbschematic" src="https://github.com/user-attachments/assets/f5104d47-28bb-45d7-8ddf-3b8a73dfeda5" />
)

Key design decisions:
- Pull-down resistors on push buttons to prevent floating inputs
- RC debounce filtering on rotary encoder lines to reject mechanical switch chatter
- MOSFET-based regulator switching circuit to support dual power sourcing (USB 5V or 9V battery) while supplying a stable regulated voltage to the rest of the system

![Prototype breadboard interface](<img width="630" height="226" alt="prototypebreadboardimage" src="https://github.com/user-attachments/assets/fb3cd519-febf-41e3-9324-8065379eef0e" />
)

### PCB Layout (KiCad)
Custom two-layer PCB designed in KiCad with the following priorities:
- Radio module and SPI display physically separated to minimize signal coupling
- Extensive ground pours on both layers to reduce EMI
- Components placed close together to minimize trace lengths and preserve signal integrity
- Thermal reliefs added to pads to make hand-soldering easier despite the dense layout

![3D rendered PCB](docs/images/pcb-3d-render.png)

### Enclosure (SolidWorks)
A custom turtle-themed enclosure was 3D-printed in PLA with tight fit tolerances around the OLED display and controls, including front acoustic ports sized to match the speaker's active surface area.

![3D SolidWorks enclosure model](docs/images/enclosure-3d-model.png)

![Enclosure orthographic drawing](docs/images/enclosure-drawing.png)

## Firmware

Written entirely in MicroPython using `asyncio` for non-blocking concurrency between:
- **Hardware loop** — button scanning with debounce, encoder ISR handling, OLED rendering, alarm triggering
- **Web server loop** — parses HTTP requests and serves a live status page

Both interfaces route through the same shared state functions (`do_button_action`, `apply_encoder_delta`, `apply_absolute_value`), so the physical controls and web UI can never fall out of sync with each other — there's a single source of truth for what each input does in any given menu state.

Full firmware source is in [`firmware/`](./firmware).

## Testing

Verified on a breadboard prototype prior to PCB assembly, validating each peripheral (display, radio, encoder, RTC) individually before full integration.
