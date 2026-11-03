# Animal-Themed Custom Clock-Radio

A turtle-themed FM clock-radio built around a Raspberry Pi Pico 2 W, featuring a custom two-layer PCB, dual-interface control (physical + web), and a 3D-printed enclosure — developed for ECE 299 at the University of Victoria.

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
![MicroPython](https://img.shields.io/badge/MicroPython-Pico%202%20W-2B2728?logo=micropython&logoColor=white)
![KiCad](https://img.shields.io/badge/KiCad-10-314CB0?logo=kicad&logoColor=white)

**Authors:** Oscar Bazylewich, Ethan Packer

<p align="center">
  <img width="640" alt="Finished turtle clock radio showing the time, alarm, volume and station" src="https://github.com/user-attachments/assets/56bc1907-05c3-48a4-921a-7b3245e22ea5" />
</p>

This project combines digital timekeeping, FM radio tuning and wireless connectivity into a single compact embedded system, driven entirely by one Raspberry Pi Pico 2 W programmed in MicroPython. The system supports two fully synchronized control interfaces: a physical rotary encoder + button set, and a local web server hosted on the Pico's own Wi-Fi access point. We designed the PCB in KiCad and the turtle enclosure in SolidWorks.

## Features

- **Clock/Alarm:** set the time from the knob or sync it from your phone, 12h/24h toggle, alarm with adjustable time, volume and tone
- **FM Radio:** RDA5807M tuner with manual frequency (87.0–108.0 MHz) and volume control
- **Dual UI:** rotary encoder/buttons on-device, plus a browser-based UI over Wi-Fi
- **Shared OLED display:** single SPI display multiplexed between clock and radio screens via a centralized state machine
- **Dual power:** runs off USB or a 9 V battery

## Hardware

The circuit integrates a Pico 2 W, RDA5807M FM tuner (I2C), SSD1306 OLED (SPI), LM386 audio amplifier, rotary encoder and push buttons, with a MOSFET-switched linear regulator stage that lets the system run off either USB power or a 9 V battery.

| Part | Role |
| --- | --- |
| Raspberry Pi Pico 2 W | Microcontroller and Wi-Fi access point |
| RDA5807M module | FM tuner (I2C) |
| 1.3-inch SSD1306 OLED, 128×64 | Display (SPI) |
| LM386N-4 | Audio amplifier |
| UA78M05IDCYR | 5 V linear regulator |
| IRLML5103TRPBF | P-channel MOSFET for USB/battery switching |
| Rotary encoder with switch (Alps EC12E footprint) | Knob |
| 3 × 6 mm tactile buttons | B1, B2, B3 |
| Eagle 12BH611-GR holder | 9 V battery |
| Speaker and wire antenna | Audio out, FM antenna |

<p align="center">
  <img width="800" alt="KiCad schematic of the full circuit" src="https://github.com/user-attachments/assets/a08df9cf-e17a-4bcc-a510-66c9a18b9570" />
  <br/>
  <em>Schematic. The firmware pins match this revision.</em>
</p>

Key design decisions:

- Pull-down resistors (10 kΩ) on push buttons to prevent floating inputs
- RC debounce filtering (10 kΩ + 47 nF) on rotary encoder lines to reject mechanical switch chatter
- MOSFET-based regulator switching circuit to support dual power sourcing (USB 5 V or 9 V battery) while supplying a stable regulated voltage to the rest of the system
- We mixed the radio audio and the alarm PWM at the LM386 input, so the alarm plays through the same speaker

### Pinout

Pins match [`firmware/main.py`](firmware/main.py):

| Signal | Pico pin | Notes |
| --- | --- | --- |
| Radio SDA / SCL | GP26 / GP27 | I2C1, 200 kHz, address `0x10`, 2 kΩ pull-ups |
| OLED SCK / MOSI | GP18 / GP19 | SPI0 |
| OLED CS / DC / RES | GP17 / GP20 / GP21 | Digital outputs |
| Encoder A / B | GP14 / GP13 | RC-filtered, interrupt on both edges |
| Encoder switch | GP10 | Wired but not used by the firmware |
| Buttons B1 / B2 / B3 | GP8 / GP5 / GP2 | Pull-down, active high |
| Alarm tone | GP28 | PWM into the LM386 |

Power: the regulator feeds VSYS (pin 39), VBUS (pin 40, USB 5 V) drives the MOSFET gate, and 3V3 (pin 36) powers the radio, OLED and pull-ups.

**Note:** the KiCad zip in `hardware/` is a different revision from the schematic and 3D render shown here, with different button and encoder pins and no alarm-tone connection. If you build from it, update `button_pins`, `EncoderA` and `EncoderB` in `main.py` and add a path for the alarm tone.

### PCB layout (KiCad)

Custom two-layer PCB designed in KiCad with the following priorities:

- Radio module and SPI display physically separated to minimize signal coupling
- Extensive ground pours on both layers to reduce EMI
- Components placed close together to minimize trace lengths and preserve signal integrity
- Thermal reliefs added to pads to make hand-soldering easier despite the dense layout

<p align="center">
  <img width="600" alt="KiCad 3D render of the PCB" src="https://github.com/user-attachments/assets/eb9abdda-967d-4928-b739-03e7cd99b86c" />
  <br/>
  <em>3D render of the same revision as the schematic.</em>
</p>

### Enclosure (SolidWorks)

A custom turtle-themed enclosure was 3D-printed in PLA with tight fit tolerances around the OLED display and controls, including front acoustic ports sized to match the speaker's active surface area. We haven't included the enclosure CAD files in this repo.

<p align="center">
  <img width="400" alt="SolidWorks model of the turtle enclosure with the lid raised" src="https://github.com/user-attachments/assets/2b6b6068-4960-4585-9e57-01351faf7c60" />
  <img width="630" alt="Orthographic drawing of the enclosure" src="https://github.com/user-attachments/assets/45f15d73-6e38-414c-8fe1-59d5f283f455" />
  <br/>
  <em>SolidWorks model with the lid raised, and the orthographic drawing.</em>
</p>

## How it works

Written entirely in MicroPython using `asyncio` for non-blocking concurrency between:

- **Hardware loop** — button scanning with debounce, encoder ISR handling, OLED rendering, alarm triggering (100 ms between passes)
- **Web server loop** — parses HTTP requests on port 80 and serves a live status page

Both interfaces route through the same shared state functions (`do_button_action`, `apply_encoder_delta`, `apply_absolute_value`), so the physical controls and web UI can never fall out of sync with each other — there's a single source of truth for what each input does in any given menu state.

- **Encoder:** a detent only counts after a full quadrature sequence, which rejects bouncing.
- **Buttons:** a press only counts if the pin still reads high 20 ms later.
- **Clock:** the Pico's internal RTC, set from the knob or **Sync Clock from Phone** (no NTP).
- **Alarm:** mutes the radio and plays a PWM square wave on GP28 (440 Hz default, 200–2000 Hz). Volume maps to 0–50 % duty, since 50 % gives a square wave its biggest AC amplitude. Any button stops it and restores the radio's previous mute state.

<p align="center">
  <img width="320" alt="The clock's web page on the Home menu" src="https://github.com/user-attachments/assets/ee7cd501-fe4e-4ec4-a443-1b715b9363af" />
  <br/>
  <em>The web UI served by the Pico.</em>
</p>

Web buttons hit `/action`, `/set_value` or `/set_time`, which redirect back to `/` so the 2-second auto-reload never repeats a press.

## Getting started

You'll need the board (or a breadboard wired to the [pinout](#pinout)), [MicroPython](https://micropython.org/download/) for the Pico 2 W, and [Thonny](https://thonny.org/) or [`mpremote`](https://docs.micropython.org/en/latest/reference/mpremote.html).

1. Hold **BOOTSEL** while plugging the Pico 2 W in, then copy the MicroPython `.uf2` onto the USB drive that shows up.
2. Copy both files in [`firmware/`](firmware) to the board's root, keeping the name `SSD1306.py` since `main.py` imports it. With mpremote:
   ```sh
   mpremote cp firmware/SSD1306.py :SSD1306.py
   mpremote cp firmware/main.py :main.py
   mpremote reset
   ```
   In Thonny, *Save as…* each file to the MicroPython device.
3. Power it from USB or the 9 V battery. `main.py` runs at boot and starts the access point and web server. To see the boot messages, open the REPL (Thonny's shell or `mpremote repl`) and press Ctrl-C, then Ctrl-D to soft-reboot.
4. Connect your phone or laptop to the clock's Wi-Fi (`AP_SSID` / `AP_PASSWORD` in `main.py`):
   - SSID: `PicoAlarmClock`
   - Password: `alarmclock123`
5. Open the address printed at boot (`http://<access-point IP>/`) and press **Sync Clock from Phone** to set the time.

For the hardware, extract `hardware/ECE299RadioClockProjectV2.zip` and open `ECE299RadioClockProject.kicad_pro` in KiCad 10 (see the [note](#pinout) above).

### Controls

Except on Home, the OLED shows what B1/B2/B3 do (same labels as the web page), and the knob adjusts whatever the screen controls.

| Screen | B1 | B2 | B3 | Knob |
| --- | --- | --- | --- | --- |
| Home | Clock menu | Volume menu | Radio menu | 12 h / 24 h |
| Volume | Home | Mute / unmute | Knob target: radio volume, alarm volume or tone | Adjust |
| Radio | Home | — | — | Tune ±0.1 MHz |
| Clock | Home | Set Clock | Alarm | — |
| Alarm | Back to Clock | Set alarm time | Alarm on / off | — |
| Set Clock / Set alarm time | Exit | Previous field | Next field | Adjust field |

While the alarm is ringing, any button (physical or web) silences it.

## Repository structure

```text
.
├── firmware/
│   ├── main.py                        # Radio, encoder, menus, alarm, Wi-Fi AP and web server
│   └── SSD1306.py                     # OLED driver (I2C and SPI classes, SPI is used)
├── hardware/
│   └── ECE299RadioClockProjectV2.zip  # KiCad 10 project (different revision)
├── LICENSE
└── README.md
```

## Testing

Verified on a breadboard prototype prior to PCB assembly, validating each peripheral (display, radio, encoder, RTC) individually before full integration.

<p align="center">
  <img width="630" alt="Breadboard prototype of the clock radio" src="https://github.com/user-attachments/assets/4c19208c-9f9a-40a4-96ee-80cb67cb2a44" />
  <br/>
  <em>Breadboard prototype running the home screen.</em>
</p>

## Credits

- **Authors:** Oscar Bazylewich and Ethan Packer, for ECE 299 at the University of Victoria.
- [`firmware/SSD1306.py`](firmware/SSD1306.py) is a MicroPython SSD1306 OLED driver with I2C and SPI interfaces.

## License

Released under the [MIT License](LICENSE).
