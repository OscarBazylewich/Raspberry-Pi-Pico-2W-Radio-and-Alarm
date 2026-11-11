# Animal-Themed Custom Clock-Radio

The Animal-Themed Custom Clock-Radio is an FM clock radio in a 3D-printed turtle enclosure. The clock radio uses a Raspberry Pi Pico 2 W. It has a two-layer PCB. It also has two control interfaces: the hardware controls and a web UI. We made this clock radio for ECE 299 at the University of Victoria.

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
![MicroPython](https://img.shields.io/badge/MicroPython-Pico%202%20W-2B2728?logo=micropython&logoColor=white)
![KiCad](https://img.shields.io/badge/KiCad-10-314CB0?logo=kicad&logoColor=white)

**Authors:** Oscar Bazylewich, Ethan Packer

<p align="center">
  <img width="640" alt="The completed turtle clock radio. The OLED shows the time, the alarm, the volume and the radio station." src="https://github.com/user-attachments/assets/56bc1907-05c3-48a4-921a-7b3245e22ea5" />
</p>

The clock radio is a small embedded system. It contains a digital clock, an FM tuner and a Wi-Fi connection. One Raspberry Pi Pico 2 W controls all of the clock radio. We wrote the firmware in MicroPython.

The clock radio has two control interfaces:

- **Hardware controls:** a rotary encoder and a set of buttons on the clock radio
- **Web UI:** from a local web server on the Wi-Fi access point of the Pico 2 W

The two control interfaces are fully synchronized.

We made the PCB layout in KiCad and the model of the turtle enclosure in SolidWorks.

## Features

- **Clock/Alarm:** You can set the time with the encoder, or you can set the time from your phone. You can select a 12 h or a 24 h clock. You can adjust the alarm time, the alarm volume and the alarm tone.
- **FM Radio:** The RDA5807M tuner has manual frequency control (87.0–108.0 MHz) and volume control.
- **Two control interfaces:** The clock radio has a rotary encoder and buttons. You can also use the web UI in a browser through Wi-Fi.
- **One OLED for all screens:** The clock screens and the radio screens use one OLED (SPI). One state machine selects the screen that the OLED shows.
- **Two power sources:** The clock radio operates on USB power or on a 9 V battery.

## Hardware

The circuit contains a Pico 2 W, an RDA5807M tuner (I2C), an SSD1306 OLED (SPI) and an LM386 audio amplifier. It also contains a rotary encoder and buttons. A linear regulator circuit with a MOSFET switch lets the clock radio operate on USB power or on a 9 V battery.

| Part | Function |
| --- | --- |
| Raspberry Pi Pico 2 W | Microcontroller and Wi-Fi access point |
| RDA5807M module | FM tuner (I2C) |
| 1.3-inch SSD1306 OLED, 128×64 | Display (SPI) |
| LM386N-4 | Audio amplifier |
| UA78M05IDCYR | 5 V linear regulator |
| IRLML5103TRPBF | P-channel MOSFET that selects USB power or battery power |
| Rotary encoder with a switch (Alps EC12E footprint) | Control that you turn |
| Three 6 mm tactile buttons | B1, B2, B3 |
| Eagle 12BH611-GR holder | Holds the 9 V battery |
| Speaker and wire antenna | Audio output, FM antenna |

<p align="center">
  <img width="800" alt="KiCad schematic of the full circuit" src="https://github.com/user-attachments/assets/a08df9cf-e17a-4bcc-a510-66c9a18b9570" />
</p>

Important decisions for the circuit:

- Pull-down resistors (10 kΩ) on the buttons prevent floating inputs.
- RC debounce filters (10 kΩ + 47 nF) on the rotary encoder signals remove the contact bounce from these signals.
- A MOSFET switch circuit at the regulator lets the clock radio use two power sources (USB 5 V or 9 V battery). The regulator supplies a stable voltage to all other parts of the circuit.
- We mixed the radio audio and the alarm PWM signal at the LM386 input. Thus, the alarm and the radio use the same speaker.

### Pinout

| Signal | Pico pin | Notes |
| --- | --- | --- |
| Radio SDA / SCL | GP26 / GP27 | I2C1, 200 kHz, address `0x10`, 2 kΩ pull-up resistors |
| OLED SCK / MOSI | GP18 / GP19 | SPI0 |
| OLED CS / DC / RES | GP17 / GP20 / GP21 | Digital outputs |
| Encoder A / B | GP14 / GP13 | RC debounce filter, interrupt on the two edges |
| Encoder switch | GP10 | Connected, but the firmware does not use it |
| Buttons B1 / B2 / B3 | GP8 / GP5 / GP2 | Pull-down resistor, active high |
| Alarm tone | GP28 | PWM signal to the LM386 input |

Power connections:

- The regulator supplies power to VSYS (pin 39).
- VBUS (pin 40, USB 5 V) controls the MOSFET gate.
- 3V3 (pin 36) supplies power to the tuner, the OLED and the pull-up resistors.

**Note:** The KiCad zip file in `hardware/` is a different revision from the schematic and the 3D view on this page. In that revision, the button pins and the encoder pins are different. That revision also has no connection for the alarm tone.

If you assemble a PCB from that revision, do these steps:

1. In `main.py`, change the pin numbers in `button_pins`, `EncoderA` and `EncoderB` to the pins in the schematic of that revision.
2. Add a connection from GP28 to the LM386 input for the alarm tone.

### PCB layout (KiCad)

We made the two-layer PCB layout in KiCad. These items were important for the layout:

- The tuner and the OLED are at a distance from each other. This keeps the signal coupling between them to a minimum.
- Large ground pours on the two layers decrease EMI.
- The parts are near each other. This keeps the trace lengths to a minimum and helps to keep the signal integrity.
- We added thermal reliefs to the pads. These make the pads easier to solder manually, although the layout has many parts in a small area.

<p align="center">
  <img width="600" alt="KiCad 3D view of the PCB" src="https://github.com/user-attachments/assets/eb9abdda-967d-4928-b739-03e7cd99b86c" />
</p>

### Enclosure (SolidWorks)

The turtle enclosure is 3D-printed in PLA. The enclosure has tight fit tolerances around the OLED and the controls. The acoustic ports at the front have an area that agrees with the area of the speaker cone.

This repository does not contain the CAD files for the enclosure.

<p align="center">
  <img width="400" alt="SolidWorks model of the turtle enclosure with the lid up" src="https://github.com/user-attachments/assets/2b6b6068-4960-4585-9e57-01351faf7c60" />
  <img width="630" alt="Orthographic drawing of the enclosure" src="https://github.com/user-attachments/assets/45f15d73-6e38-414c-8fe1-59d5f283f455" />
</p>

## How the clock radio operates

We wrote all of the firmware in MicroPython. The firmware has two loops and uses `asyncio`. While one loop waits, the other loop can operate. Thus, one loop does not stop the other:

- **Hardware loop:** This loop reads the buttons (with debounce), processes the encoder interrupts (ISR), updates the OLED and starts the alarm. The loop waits 100 ms between cycles.
- **Web server loop:** This loop parses HTTP requests on port 80 and sends the web UI. The web UI shows the values of the clock radio, and it reloads at 2-second intervals.

The two control interfaces use the same functions (`do_button_action`, `apply_encoder_delta`, `apply_absolute_value`). These functions contain all of the logic for the inputs on each screen. Thus, the hardware controls and the web UI always stay synchronized.

This list gives more information about the inputs, the clock and the alarm:

- **Encoder:** The firmware counts a detent only after a full quadrature sequence. Thus, the firmware does not count contact bounce as a detent.
- **Buttons:** When a button pin is high, the firmware waits 20 ms and reads the pin again. The firmware accepts the input only if the pin is high at that time.
- **Clock:** The clock uses the internal RTC of the Pico 2 W. You can set the RTC with the encoder or with **Sync Clock from Phone** (no NTP).
- **Alarm:** The alarm mutes the radio and makes a PWM square wave on GP28. The default frequency is 440 Hz. The frequency range is 200–2000 Hz. The alarm volume sets a duty cycle of 0–50 %, because a square wave has its largest AC amplitude at a 50 % duty cycle. Each of B1, B2 and B3 stops the alarm and sets the radio to its previous mute condition.

<p align="center">
  <img width="320" alt="The web UI of the clock radio with the Home screen" src="https://github.com/user-attachments/assets/ee7cd501-fe4e-4ec4-a443-1b715b9363af" />
</p>

Each button on the web UI sends an HTTP request to `/action`, `/set_value` or `/set_time`. The web server then redirects the browser back to `/`. Thus, when the web UI reloads, it does not send the same input again.

## How to start

These items are necessary:

- A copy of this repository on your computer
- The PCB, or a breadboard with the connections in the [pinout](#pinout)
- [MicroPython](https://micropython.org/download/) for the Pico 2 W
- [Thonny](https://thonny.org/) or [`mpremote`](https://docs.micropython.org/en/latest/reference/mpremote.html)

Do these steps:

1. While you push and hold **BOOTSEL**, connect the Pico 2 W to your computer. Copy the MicroPython `.uf2` file to the USB drive that the computer shows.
2. If your PCB is from the files in `hardware/`, do the steps below the [note](#pinout) in the Pinout section.
3. Copy the two files in [`firmware/`](firmware) to the root folder of the Pico 2 W. Keep the name `SSD1306.py`, because `main.py` imports it. If you use mpremote, type these commands in the root folder of your copy of this repository:
   ```sh
   mpremote cp firmware/SSD1306.py :SSD1306.py
   mpremote cp firmware/main.py :main.py
   mpremote reset
   ```
   If you use Thonny, open each file in Thonny. Then use *Save as…* to save the file to the Pico 2 W (the MicroPython device).
4. Supply power to the circuit from USB or from the 9 V battery.

   **Note:** When the Pico 2 W boots, it starts `main.py`. Then `main.py` starts the access point and the web server.
5. Do these steps to get the address of the web UI:
   1. If the Pico 2 W is not connected to your computer, connect it with USB.
   2. Open the REPL (the shell in Thonny, or `mpremote repl`).
   3. Press Ctrl-C.
   4. Press Ctrl-D to soft-reboot the Pico 2 W.
   5. Find the address in the messages that the Pico 2 W prints on the REPL when it boots.
6. Connect your phone or laptop to the Wi-Fi network of the clock radio (`AP_SSID` / `AP_PASSWORD` in `main.py`):
   - SSID: `PicoAlarmClock`
   - Password: `alarmclock123`
7. On your phone or laptop, open the address from step 5 (`http://<access-point IP>/`) in a browser. Select **Sync Clock from Phone** to set the time.

The files in `hardware/` are from a different revision. Before you use them, read the [note](#pinout) in the Pinout section.

To open the hardware files, do these steps:

1. Unzip `hardware/ECE299RadioClockProjectV2.zip`.
2. Open `ECE299RadioClockProject.kicad_pro` in KiCad 10.

### Controls

On all screens other than the Home screen, the OLED shows a label for each of B1/B2/B3. Each label gives the function of the button. The web UI shows the same labels. The encoder adjusts the value that the screen controls (refer to the Encoder column in the table).

| Screen | B1 | B2 | B3 | Encoder |
| --- | --- | --- | --- | --- |
| Home | Clock screen | Volume screen | Radio screen | 12 h / 24 h |
| Volume | Home | Mute / unmute | Encoder function: radio volume, alarm volume or tone | Adjust |
| Radio | Home | — | — | Tune ±0.1 MHz |
| Clock | Home | Set Clock | Alarm | — |
| Alarm | Back to Clock | Set alarm time | Alarm on / off | — |
| Set Clock / Set alarm time | Exit | Previous field | Next field | Adjust field |

While the alarm tone is on, each of B1, B2 and B3 on the clock radio or on the web UI stops the alarm.

## Repository structure

```text
.
├── firmware/
│   ├── main.py                        # Radio, encoder, screens, alarm, Wi-Fi access point and web server
│   └── SSD1306.py                     # OLED driver with I2C and SPI classes (the firmware uses the SPI class)
├── hardware/
│   └── ECE299RadioClockProjectV2.zip  # KiCad 10 project (different revision)
├── LICENSE
└── README.md
```

## Test

Before the PCB was assembled, we made sure that the circuit operated correctly on a breadboard prototype. First, we made sure that each peripheral (OLED, tuner, encoder, RTC) operated correctly. Then we connected all of the peripherals together.

<p align="center">
  <img width="630" alt="Breadboard prototype of the clock radio" src="https://github.com/user-attachments/assets/4c19208c-9f9a-40a4-96ee-80cb67cb2a44" />
</p>

## Credits

- **Authors:** Oscar Bazylewich and Ethan Packer, for ECE 299 at the University of Victoria.
- [`firmware/SSD1306.py`](firmware/SSD1306.py) is a MicroPython driver for the SSD1306 OLED. The driver has an I2C class and an SPI class.

## License

The license of this project is the [MIT License](LICENSE).
