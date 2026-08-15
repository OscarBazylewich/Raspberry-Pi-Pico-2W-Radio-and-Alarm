import machine
from machine import Pin, SPI, I2C, PWM
import time
import utime
import network
import asyncio

rtc = machine.RTC()

# Libraries must be saved on the Pico
from SSD1306 import SSD1306_SPI
import framebuf

# ============================================================================
# Radio class (unchanged from your original)
# ============================================================================
class Radio:
    def __init__( self, NewFrequency, NewVolume, NewMute ):
        self.Volume = 2
        self.Frequency = 88.0
        self.Mute = False

        self.SetVolume( NewVolume )
        self.SetFrequency( NewFrequency )
        self.SetMute( NewMute )

        self.i2c_sda = Pin(26)
        self.i2c_scl = Pin(27)
        self.i2c_device = 1
        self.i2c_device_address = 0x10

        self.Settings = bytearray( 8 )
        self.radio_i2c = I2C( self.i2c_device, scl=self.i2c_scl, sda=self.i2c_sda, freq=200000)
        self.ProgramRadio()

    def SetVolume( self, NewVolume ):
        try:
            NewVolume = int( NewVolume )
        except:
            return False

        if ( not isinstance( NewVolume, int )):
            return False
        if (( NewVolume < 0 ) or ( NewVolume >= 16 )):
            return False
        self.Volume = NewVolume
        return True

    def SetFrequency( self, NewFrequency ):
        try:
            NewFrequency = float( NewFrequency )
        except:
            return False

        if ( not ( isinstance( NewFrequency, float ))):
            return False
        if (( NewFrequency < 87.0 ) or ( NewFrequency > 108.0 )):
            return False
        self.Frequency = NewFrequency
        return True

    def SetMute( self, NewMute ):
        try:
            self.Mute = bool( int( NewMute ))
        except:
            return False
        return True

    def ComputeChannelSetting( self, Frequency ):
        Frequency = int( Frequency * 10 ) - 870
        ByteCode = bytearray( 2 )
        ByteCode[0] = ( Frequency >> 2 ) & 0xFF
        ByteCode[1] = (( Frequency & 0x03 ) << 6 ) & 0xC0
        return ByteCode

    def UpdateSettings( self ):
        self.Settings = bytearray( 8 )
        if ( self.Mute ):
            self.Settings[0] = 0x80
        else:
            self.Settings[0] = 0xC0
        self.Settings[1] = 0x09 | 0x04
        self.Settings[2:4] = self.ComputeChannelSetting( self.Frequency )
        self.Settings[3] = self.Settings[3] | 0x10
        self.Settings[4] = 0x04
        self.Settings[5] = 0x00
        self.Settings[6] = 0x84
        self.Settings[7] = 0x80 + self.Volume
        self.Settings = self.Settings[:8]

    def ProgramRadio( self ):
        self.UpdateSettings()
        self.radio_i2c.writeto( self.i2c_device_address, self.Settings )

    def GetSettings( self ):
        self.RadioStatus = self.radio_i2c.readfrom( self.i2c_device_address, 256 )
        if (( self.RadioStatus[0xF0] & 0x40 ) != 0x00 ):
            MuteStatus = False
        else:
            MuteStatus = True
        VolumeStatus = self.RadioStatus[0xF7] & 0x0F

        FrequencyStatus = (( self.RadioStatus[0x00] & 0x03 ) << 8 ) | ( self.RadioStatus[0x01] & 0xFF )
        FrequencyStatus = ( FrequencyStatus * 0.1 ) + 87.0
        if (( self.RadioStatus[0x00] & 0x04 ) != 0x00 ):
            StereoStatus = True
        else:
            StereoStatus = False
        return ( MuteStatus, VolumeStatus, FrequencyStatus, StereoStatus )

# ============================================================================
# Rotary Encoder handling (interrupt-driven, unchanged)
# ============================================================================
EncoderState = 0
EncoderChange = 0   # signed delta accumulated since main loop last checked

def DoEncoder( Encoder, State ):
    global EncoderState
    global EncoderChange

    # Wired with pull-up resistors to 3V3 + decoupling caps to ground, so
    # idle level is HIGH and a contact closure pulls the line LOW. A turn
    # therefore starts on a FALLING edge (State==4).

    if ( EncoderState == 0 ):
        if (( Encoder == 'A' ) and ( State == 4 )):
            EncoderState = 1
        elif (( Encoder == 'B' ) and ( State == 4 )):
            EncoderState = 4

    elif ( EncoderState == 1 ):
        if (( Encoder == 'B' ) and ( State == 4 )):
            EncoderState = 2
        else:
            EncoderState = 0

    elif ( EncoderState == 2 ):
        if (( Encoder == 'A' ) and ( State == 8 )):
            EncoderState = 3
        else:
            EncoderState = 0

    elif ( EncoderState == 3 ):
        if (( Encoder == 'B' ) and ( State == 8 )):
            EncoderChange = EncoderChange + 1
        EncoderState = 0

    elif ( EncoderState == 4 ):
        if (( Encoder == 'A' ) and ( State == 4 )):
            EncoderState = 5
        else:
            EncoderState = 0

    elif ( EncoderState == 5 ):
        if (( Encoder == 'B' ) and ( State == 8 )):
            EncoderState = 6
        else:
            EncoderState = 0

    elif ( EncoderState == 6 ):
        if (( Encoder == 'A' ) and ( State == 8 )):
            EncoderChange = EncoderChange - 1
        EncoderState = 0

    else:
        EncoderState = 0

    return( True )

def EncoderAInterrupt( Pin ):
    DoEncoder( 'A', Pin.irq().flags())
    return( True )

def EncoderBInterrupt( Pin ):
    DoEncoder( 'B', Pin.irq().flags())
    return( True )

# GPIO 14 -> encoder terminal A, GPIO 13 -> encoder terminal B
EncoderA = Pin( 14, Pin.IN )
EncoderB = Pin( 13, Pin.IN )

EncoderA.irq( handler=EncoderAInterrupt, trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, hard=True )
EncoderB.irq( handler=EncoderBInterrupt, trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, hard=True )

def GetEncoderChange():
    global EncoderChange
    state = machine.disable_irq()
    delta = EncoderChange
    EncoderChange = 0
    machine.enable_irq(state)
    return delta

# ============================================================================
# Display Configuration
# ============================================================================
SCREEN_WIDTH = 128
SCREEN_HEIGHT = 64

spi_sck = Pin(18)
spi_sda = Pin(19)
spi_res = Pin(21)
spi_dc  = Pin(20)
spi_cs  = Pin(17)

SPI_DEVICE = 0
oled_spi = SPI( SPI_DEVICE, baudrate= 100000, sck= spi_sck, mosi= spi_sda )
oled = SSD1306_SPI( SCREEN_WIDTH, SCREEN_HEIGHT, oled_spi, spi_dc, spi_res, spi_cs, True )

# Initialize system variables
fm_radio = Radio(100.3, 2, False)

button_pins = [8, 5, 2]
buttons = [Pin(pin, Pin.IN, Pin.PULL_DOWN) for pin in button_pins]

# Read current physical status of pins at startup to avoid false triggers
Current_states = [buttons[0].value(), buttons[1].value(), buttons[2].value()]

current_menu = "Home"
clock_submenu = "Home"
alarm_field = "second"
setclock_field = "second"

ALARM_FIELD_CYCLE = ["second", "minute", "hour"]
SETCLOCK_FIELD_CYCLE = ["second", "minute", "hour"]

time_format_24h = True   # True = 24h display, False = 12h with AM/PM

alarm_hour = 7
alarm_minute = 0
alarm_second = 0
alarm_enabled = False

volume_target = "Radio"   # "Radio", "AlarmVol", or "AlarmTone" -- what the knob controls in the Volume menu
alarm_volume = 8          # 0-15, same scale as fm_radio.Volume, maps to PWM duty cycle

last_input_error = ""    # shown as a banner on the web page when the text-input field gets bad input

def cycle_field(cycle_list, current, forward):
    idx = cycle_list.index(current)
    if forward:
        idx = min(idx + 1, len(cycle_list) - 1)
    else:
        idx = max(idx - 1, 0)
    return cycle_list[idx]

def format_time(hour, minute, second):
    """Formats a 24h (hour, minute, second) triple according to the
    current time_format_24h setting."""
    if time_format_24h:
        return "%02d:%02d:%02d" % (hour, minute, second)
    if hour == 0:
        h12, suffix = 12, "AM"
    elif hour < 12:
        h12, suffix = hour, "AM"
    elif hour == 12:
        h12, suffix = 12, "PM"
    else:
        h12, suffix = hour - 12, "PM"
    return "%02d:%02d:%02d %s" % (h12, minute, second, suffix)

# ============================================================================
# Alarm sound
# ============================================================================
ALARM_TONE_PIN = 28
ALARM_TONE_MIN_HZ = 200
ALARM_TONE_MAX_HZ = 2000

alarm_tone_freq = 440   # Hz -- user-adjustable via Volume menu's "AlarmTone" target

alarm_tone = PWM(Pin(ALARM_TONE_PIN))
alarm_tone.freq(alarm_tone_freq)
alarm_tone.duty_u16(0)

alarm_playing = False
alarm_radio_was_muted = False
alarm_last_triggered_second = -1

def AlarmVolumeToDuty(vol):
    """Map a 0-15 volume level (same scale as fm_radio.Volume) to a
    16-bit PWM duty value. Capped at 50% duty (32768) rather than 100%,
    because a square wave's AC amplitude -- the part that actually gets
    through the coupling cap to the LM386 -- is maximized at 50% duty
    and falls off symmetrically toward either 0% or 100%. 100% duty is
    a constant DC level with no switching at all, which is silent once
    filtered by the coupling cap; mapping straight to 100% would make
    max volume the quietest setting instead of the loudest."""
    vol = max(0, min(15, vol))
    return int(32768 * vol // 15)

def StartAlarmSound():
    global alarm_playing, alarm_radio_was_muted
    alarm_radio_was_muted = fm_radio.Mute
    if not fm_radio.Mute:
        fm_radio.SetMute(1)
        fm_radio.ProgramRadio()
    alarm_tone.freq(alarm_tone_freq)
    alarm_tone.duty_u16(AlarmVolumeToDuty(alarm_volume))
    alarm_playing = True

def StopAlarmSound():
    global alarm_playing
    alarm_tone.duty_u16(0)
    if not alarm_radio_was_muted:
        fm_radio.SetMute(0)
        fm_radio.ProgramRadio()
    alarm_playing = False

# ============================================================================
# Shared action handlers
#
# do_button_action(i) and apply_encoder_delta(delta) hold ALL the menu
# logic. Both the physical button scanner/encoder ISR-consumer AND the
# web server call these same functions, so the web UI and the physical
# controls can never drift out of sync with each other -- there is only
# one implementation of "what button 2 does in the Alarm submenu", etc.
# ============================================================================

def do_button_action(i):
    """i is 0, 1, or 2 for B1, B2, B3."""
    global current_menu, clock_submenu, alarm_field, setclock_field, alarm_enabled, volume_target

    if alarm_playing:
        StopAlarmSound()
        return

    if current_menu == "Home":
        if i == 0:
            current_menu = "Clock"
            clock_submenu = "Home"
        elif i == 1:
            current_menu = "Volume"
        elif i == 2:
            current_menu = "Radio"

    elif current_menu == "Volume":
        if i == 0:
            current_menu = "Home"
        elif i == 1:
            next_mute_state = 0 if fm_radio.Mute else 1
            if fm_radio.SetMute(next_mute_state):
                fm_radio.ProgramRadio()
        elif i == 2:
            # Cycle which output the knob controls
            if volume_target == "Radio":
                volume_target = "AlarmVol"
            elif volume_target == "AlarmVol":
                volume_target = "AlarmTone"
            else:
                volume_target = "Radio"

    elif current_menu == "Radio":
        if i == 0:
            current_menu = "Home"
        # B2 retired -- encoder handles frequency directly in this menu.

    elif current_menu == "Clock":
        if clock_submenu == "Home":
            if i == 0:
                current_menu = "Home"
            elif i == 1:
                clock_submenu = "SetClock"
                setclock_field = "second"
            elif i == 2:
                clock_submenu = "Alarm"

        elif clock_submenu == "SetClock":
            if i == 0:
                clock_submenu = "Home"
            elif i == 1:
                setclock_field = cycle_field(SETCLOCK_FIELD_CYCLE, setclock_field, forward=False)
            elif i == 2:
                setclock_field = cycle_field(SETCLOCK_FIELD_CYCLE, setclock_field, forward=True)

        elif clock_submenu == "Alarm":
            # Selection screen: choose whether to adjust the alarm time
            # or just flip it on/off, rather than burying the toggle
            # inside the field-cycle knob interaction.
            if i == 0:
                clock_submenu = "Home"
            elif i == 1:
                clock_submenu = "AlarmTime"
                alarm_field = "second"
            elif i == 2:
                alarm_enabled = not alarm_enabled

        elif clock_submenu == "AlarmTime":
            if i == 0:
                clock_submenu = "Alarm"
            elif i == 1:
                alarm_field = cycle_field(ALARM_FIELD_CYCLE, alarm_field, forward=False)
            elif i == 2:
                alarm_field = cycle_field(ALARM_FIELD_CYCLE, alarm_field, forward=True)

def apply_encoder_delta(delta):
    global alarm_second, alarm_minute, alarm_hour, alarm_volume, alarm_enabled, time_format_24h, alarm_tone_freq

    if delta == 0:
        return

    if current_menu == "Home":
        # Any turn of the knob flips 12h/24h on the Home screen
        time_format_24h = not time_format_24h

    elif current_menu == "Volume":
        if volume_target == "Radio":
            new_vol = fm_radio.Volume + delta
            if fm_radio.SetVolume(new_vol):
                fm_radio.ProgramRadio()
        elif volume_target == "AlarmVol":
            alarm_volume = max(0, min(15, alarm_volume + delta))
            if alarm_playing:
                alarm_tone.duty_u16(AlarmVolumeToDuty(alarm_volume))
        elif volume_target == "AlarmTone":
            alarm_tone_freq = max(ALARM_TONE_MIN_HZ, min(ALARM_TONE_MAX_HZ, alarm_tone_freq + delta * 10))
            if alarm_playing:
                alarm_tone.freq(alarm_tone_freq)

    elif current_menu == "Radio":
        new_freq = round(fm_radio.Frequency + (delta * 0.1), 1)
        if fm_radio.SetFrequency(new_freq):
            fm_radio.ProgramRadio()

    elif current_menu == "Clock" and clock_submenu == "AlarmTime":
        if alarm_field == "second":
            alarm_second = (alarm_second + delta) % 60
        elif alarm_field == "minute":
            alarm_minute = (alarm_minute + delta) % 60
        elif alarm_field == "hour":
            alarm_hour = (alarm_hour + delta) % 24

    elif current_menu == "Clock" and clock_submenu == "SetClock":
        current = list(rtc.datetime())   # (year, month, day, weekday, hour, minute, second, subsec)
        if setclock_field == "hour":
            current[4] = (current[4] + delta) % 24
        elif setclock_field == "minute":
            current[5] = (current[5] + delta) % 60
        elif setclock_field == "second":
            current[6] = (current[6] + delta) % 60
        rtc.datetime(tuple(current))

def apply_absolute_value(value_str):
    """Sets whatever the current menu/field controls to an exact value,
    instead of nudging it by a delta -- this is what the web page's text
    input field uses, as an alternative to turning the knob.
    Returns (success, error_message) so the caller can show feedback."""
    global alarm_second, alarm_minute, alarm_hour, alarm_volume, alarm_enabled, time_format_24h, alarm_tone_freq

    if current_menu == "Home":
        v = value_str.strip().lower()
        if v in ("24", "24h"):
            time_format_24h = True
            return (True, "")
        elif v in ("12", "12h"):
            time_format_24h = False
            return (True, "")
        return (False, "Enter 12 or 24 for the time format.")

    elif current_menu == "Volume":
        if volume_target == "Radio":
            if fm_radio.SetVolume(value_str):
                fm_radio.ProgramRadio()
                return (True, "")
            return (False, "Volume must be a whole number from 0 to 15.")
        elif volume_target == "AlarmVol":
            try:
                v = int(float(value_str))
            except ValueError:
                return (False, "Alarm volume must be a whole number from 0 to 15.")
            if v < 0 or v > 15:
                return (False, "Alarm volume must be between 0 and 15.")
            alarm_volume = v
            if alarm_playing:
                alarm_tone.duty_u16(AlarmVolumeToDuty(alarm_volume))
            return (True, "")
        elif volume_target == "AlarmTone":
            try:
                v = int(float(value_str))
            except ValueError:
                return (False, "Tone must be a whole number from %d to %d Hz." % (ALARM_TONE_MIN_HZ, ALARM_TONE_MAX_HZ))
            if v < ALARM_TONE_MIN_HZ or v > ALARM_TONE_MAX_HZ:
                return (False, "Tone must be between %d and %d Hz." % (ALARM_TONE_MIN_HZ, ALARM_TONE_MAX_HZ))
            alarm_tone_freq = v
            if alarm_playing:
                alarm_tone.freq(alarm_tone_freq)
            return (True, "")

    elif current_menu == "Radio":
        if fm_radio.SetFrequency(value_str):
            fm_radio.ProgramRadio()
            return (True, "")
        return (False, "Frequency must be a number from 87.0 to 108.0 MHz.")

    elif current_menu == "Clock" and clock_submenu == "AlarmTime":
        try:
            v = int(float(value_str))
        except ValueError:
            return (False, "Please enter a whole number.")
        if alarm_field == "second":
            if 0 <= v <= 59:
                alarm_second = v
                return (True, "")
            return (False, "Seconds must be between 0 and 59.")
        elif alarm_field == "minute":
            if 0 <= v <= 59:
                alarm_minute = v
                return (True, "")
            return (False, "Minutes must be between 0 and 59.")
        elif alarm_field == "hour":
            if 0 <= v <= 23:
                alarm_hour = v
                return (True, "")
            return (False, "Hour must be between 0 and 23.")

    elif current_menu == "Clock" and clock_submenu == "SetClock":
        try:
            v = int(float(value_str))
        except ValueError:
            return (False, "Please enter a whole number.")
        current = list(rtc.datetime())
        if setclock_field == "hour":
            if 0 <= v <= 23:
                current[4] = v
            else:
                return (False, "Hour must be between 0 and 23.")
        elif setclock_field == "minute":
            if 0 <= v <= 59:
                current[5] = v
            else:
                return (False, "Minute must be between 0 and 59.")
        elif setclock_field == "second":
            if 0 <= v <= 59:
                current[6] = v
            else:
                return (False, "Second must be between 0 and 59.")
        rtc.datetime(tuple(current))
        return (True, "")

    return (False, "There's nothing to set on this screen.")

# ============================================================================
# WiFi Access Point
# ============================================================================
AP_SSID = "PicoAlarmClock"
AP_PASSWORD = "alarmclock123"   # WPA2 requires 8+ characters

def start_ap():
    ap = network.WLAN(network.AP_IF)
    ap.config(essid=AP_SSID, password=AP_PASSWORD)
    ap.active(True)
    while not ap.active():
        time.sleep(0.2)
    print("Access point active.")
    print("SSID:", AP_SSID, " Password:", AP_PASSWORD)
    print("Connect your phone/computer to that network, then browse to:")
    print("http://%s/" % ap.ifconfig()[0])
    return ap

# ============================================================================
# Web UI
# ============================================================================

def get_button_labels():
    """Returns ((label1,disabled1), (label2,disabled2), (label3,disabled3))
    for B1/B2/B3, matching whatever do_button_action() actually does in
    the current menu/submenu."""
    if alarm_playing:
        return (("Silence", False), ("Silence", False), ("Silence", False))

    if current_menu == "Home":
        return (("Clock", False), ("Volume", False), ("Radio", False))

    if current_menu == "Volume":
        mute_label = "Unmute" if fm_radio.Mute else "Mute"
        target_display = {"Radio": "Radio", "AlarmVol": "Alarm Vol", "AlarmTone": "Alarm Tone"}
        return (("Home", False), (mute_label, False), ("Target: %s" % target_display[volume_target], False))

    if current_menu == "Radio":
        return (("Home", False), ("-", True), ("-", True))

    if current_menu == "Clock":
        if clock_submenu == "Home":
            return (("Home", False), ("Clock", False), ("Alarm", False))

        elif clock_submenu == "SetClock":
            idx = SETCLOCK_FIELD_CYCLE.index(setclock_field)
            prev_label = SETCLOCK_FIELD_CYCLE[idx - 1] if idx > 0 else setclock_field
            next_label = SETCLOCK_FIELD_CYCLE[idx + 1] if idx < len(SETCLOCK_FIELD_CYCLE) - 1 else setclock_field
            return (
                ("Exit", False),
                (prev_label, idx == 0),
                (next_label, idx == len(SETCLOCK_FIELD_CYCLE) - 1),
            )

        elif clock_submenu == "Alarm":
            toggle_label = "Turn Off" if alarm_enabled else "Turn On"
            return (("Home", False), ("Set Time", False), (toggle_label, False))

        elif clock_submenu == "AlarmTime":
            idx = ALARM_FIELD_CYCLE.index(alarm_field)
            prev_label = ALARM_FIELD_CYCLE[idx - 1] if idx > 0 else alarm_field
            next_label = ALARM_FIELD_CYCLE[idx + 1] if idx < len(ALARM_FIELD_CYCLE) - 1 else alarm_field
            return (
                ("Exit", False),
                (prev_label, idx == 0),
                (next_label, idx == len(ALARM_FIELD_CYCLE) - 1),
            )

    return (("-", True), ("-", True), ("-", True))

def build_html():
    if fm_radio.Mute:
        vol_line = "MUTED"
    else:
        vol_line = str(fm_radio.Volume)

    rtc_now = rtc.datetime()
    hour = rtc_now[4]
    minute = rtc_now[5]
    second = rtc_now[6]

    time_line = format_time(hour, minute, second)
    alarm_line = "Alarm %s %s" % (
        format_time(alarm_hour, alarm_minute, alarm_second), "ON" if alarm_enabled else "OFF"
    )
    if volume_target == "Radio":
        if fm_radio.Mute:
            volume_line = "Volume: MUTED (Radio)"
        else:
            volume_line = "Volume: %02d (Radio)" % fm_radio.Volume
    elif volume_target == "AlarmVol":
        volume_line = "Volume: %02d (Alarm Vol)" % alarm_volume
    else:
        volume_line = "Tone: %d Hz (Alarm)" % alarm_tone_freq
    radio_line = "Radio: %5.1f MHz" % fm_radio.Frequency

    if current_menu == "Clock" and clock_submenu == "AlarmTime":
        menu_label = "Clock &gt; Alarm &gt; Set Time (field: %s)" % alarm_field
    elif current_menu == "Clock" and clock_submenu == "Alarm":
        menu_label = "Clock &gt; Alarm"
    elif current_menu == "Clock" and clock_submenu == "SetClock":
        menu_label = "Clock &gt; Set Clock (field: %s)" % setclock_field
    elif current_menu == "Clock":
        menu_label = "Clock"
    else:
        menu_label = current_menu

    (b1_label, b1_disabled), (b2_label, b2_disabled), (b3_label, b3_disabled) = get_button_labels()

    def render_button(num, label, disabled):
        if disabled:
            return '<span class="btn disabled">%s</span>' % label
        return '<a class="btn" href="/action?cmd=button&num=%d">%s</a>' % (num, label)

    b1_html = render_button(0, b1_label, b1_disabled)
    b2_html = render_button(1, b2_label, b2_disabled)
    b3_html = render_button(2, b3_label, b3_disabled)

    # The knob does something on Home (toggles 12h/24h), Volume, Radio,
    # and SetClock/AlarmTime -- not on the Clock's top submenu or the
    # Alarm selection screen (pure button navigation).
    knob_active = not (
        current_menu == "Clock" and clock_submenu in ("Home", "Alarm")
    )

    def render_knob(delta, arrow_html):
        if not knob_active:
            return '<span class="btn knob disabled">%s</span>' % arrow_html
        return '<a class="btn knob" href="/action?cmd=encoder&delta=%d">%s</a>' % (delta, arrow_html)

    knob_left_html = render_knob(-1, "&#8630; Knob")
    knob_right_html = render_knob(1, "Knob &#8631;")

    if knob_active:
        if current_menu == "Home":
            value_placeholder = "12 or 24"
        elif current_menu == "Volume" and volume_target == "AlarmTone":
            value_placeholder = "%d-%d Hz" % (ALARM_TONE_MIN_HZ, ALARM_TONE_MAX_HZ)
        elif current_menu == "Volume":
            value_placeholder = "0-15"
        elif current_menu == "Radio":
            value_placeholder = "87.0-108.0"
        elif current_menu == "Clock" and clock_submenu == "AlarmTime":
            value_placeholder = alarm_field
        elif current_menu == "Clock" and clock_submenu == "SetClock":
            value_placeholder = setclock_field
        else:
            value_placeholder = "value"

        value_input_html = (
            '<form action="/set_value" method="get" style="display:inline-block;">'
            '<input type="text" name="val" id="valInput" placeholder="%s" '
            'style="font-size:18px;padding:10px;width:110px;">'
            '<button type="submit" class="btn">Set</button>'
            '</form>'
        ) % value_placeholder
    else:
        value_input_html = (
            '<input type="text" disabled placeholder="n/a" '
            'style="font-size:18px;padding:10px;width:110px;background:#eee;color:#999;">'
            '<span class="btn disabled">Set</span>'
        )

    alarm_banner = ""
    if alarm_playing:
        alarm_banner = "<h2 style='color:red;'>ALARM! Tap any button below to silence</h2>"

    error_banner = ""
    if last_input_error:
        error_banner = (
            "<div style='background:#ffe0e0;color:#a00;padding:10px;"
            "border-radius:8px;margin:10px auto;max-width:320px;'>"
            "&#9888; %s</div>" % last_input_error
        )

    html = """<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Pico Alarm Clock</title>
<style>
  body {{ font-family: sans-serif; text-align: center; padding: 20px; }}
  .btn {{ display:inline-block; margin:6px; padding:14px 22px; font-size:18px;
          background:#2266cc; color:white; text-decoration:none; border-radius:8px; }}
  .knob {{ background:#2266cc; }}
  .disabled {{ background:#bbb; color:#eee; cursor:default; }}
  .menu-label {{ font-size: 16px; color: #666; margin-bottom: 10px; }}
  .home-status {{ display:inline-block; text-align:left; font-family: monospace;
                   font-size: 20px; line-height: 1.6; margin: 14px 0; }}
</style>
</head>
<body>
  {alarm_banner}
  {error_banner}
  <h1>Pico Alarm Clock</h1>
  <div class="menu-label">Menu: {menu_label}</div>
  <div class="home-status">
    <div>{time_line}</div>
    <div>{alarm_line}</div>
    <div>{volume_line}</div>
    <div>{radio_line}</div>
  </div>

  <div>
    {b1_html}
    {b2_html}
    {b3_html}
  </div>
  <div>
    {knob_left_html}
    {knob_right_html}
  </div>
  <div style="margin-top:10px;">
    {value_input_html}
  </div>
  <div>
    <button class="btn" style="border:none;font-family:sans-serif;" onclick="syncClock()">Sync Clock from Phone</button>
  </div>
  <script>
  function syncClock() {{
    var d = new Date();
    var url = "/set_time?y=" + d.getFullYear() +
              "&mo=" + (d.getMonth() + 1) +
              "&d=" + d.getDate() +
              "&wd=" + d.getDay() +
              "&h=" + d.getHours() +
              "&mi=" + d.getMinutes() +
              "&s=" + d.getSeconds();
    window.location.href = url;
  }}

  function maybeReload() {{
    var input = document.getElementById("valInput");
    if (!input || document.activeElement !== input) {{
      window.location.reload();
    }} else {{
      // User is actively typing in the value field -- skip this reload
      // and check again shortly, instead of wiping out what they typed.
      setTimeout(maybeReload, 2000);
    }}
  }}
  setTimeout(maybeReload, 2000);
  </script>
</body>
</html>""".format(
        alarm_banner=alarm_banner,
        error_banner=error_banner,
        menu_label=menu_label,
        time_line=time_line,
        alarm_line=alarm_line,
        volume_line=volume_line,
        radio_line=radio_line,
        b1_html=b1_html,
        b2_html=b2_html,
        b3_html=b3_html,
        knob_left_html=knob_left_html,
        knob_right_html=knob_right_html,
        value_input_html=value_input_html,
    )
    return html

async def handle_client(reader, writer):
    try:
        request_line = await reader.readline()
        # Drain and discard headers
        while True:
            line = await reader.readline()
            if line == b"\r\n" or line == b"":
                break

        try:
            request = request_line.decode()
            method, path, _ = request.split()
        except Exception:
            path = "/"

        acted_on_request = False

        if path.startswith("/action"):
            acted_on_request = True
            global last_input_error
            last_input_error = ""   # clear any stale error once the user moves on
            query = ""
            if "?" in path:
                query = path.split("?", 1)[1]
            params = {}
            for pair in query.split("&"):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    params[k] = v

            cmd = params.get("cmd", "")
            if cmd == "button":
                try:
                    num = int(params.get("num", "-1"))
                    if num in (0, 1, 2):
                        do_button_action(num)
                except ValueError:
                    pass
            elif cmd == "encoder":
                try:
                    delta = int(params.get("delta", "0"))
                    apply_encoder_delta(delta)
                except ValueError:
                    pass

        elif path.startswith("/set_time"):
            acted_on_request = True
            query = ""
            if "?" in path:
                query = path.split("?", 1)[1]
            params = {}
            for pair in query.split("&"):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    params[k] = v
            try:
                y = int(params.get("y"))
                mo = int(params.get("mo"))
                d = int(params.get("d"))
                wd = int(params.get("wd", "0"))
                h = int(params.get("h"))
                mi = int(params.get("mi"))
                s = int(params.get("s"))
                rtc.datetime((y, mo, d, wd, h, mi, s, 0))
                print("RTC set to %04d-%02d-%02d %02d:%02d:%02d" % (y, mo, d, h, mi, s))
            except (TypeError, ValueError) as e:
                print("Bad /set_time request:", e)

        elif path.startswith("/set_value"):
            acted_on_request = True
            query = ""
            if "?" in path:
                query = path.split("?", 1)[1]
            params = {}
            for pair in query.split("&"):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    params[k] = v
            val = params.get("val", "")
            # URL-decode the "+"-for-space and %XX escapes a browser form
            # submission produces (values here are just numbers/words, so
            # this simple decode is sufficient).
            val = val.replace("+", " ")
            success, message = apply_absolute_value(val)
            last_input_error = "" if success else message

        if acted_on_request:
            # Redirect back to the plain status page rather than rendering
            # it at the /action URL -- otherwise the page's auto-refresh
            # would keep reloading /action?... and re-firing the same
            # button/knob action every 2 seconds, causing the menu to
            # cycle on its own with no further input.
            writer.write(b"HTTP/1.1 303 See Other\r\nLocation: /\r\nConnection: close\r\n\r\n")
            await writer.drain()
        else:
            html = build_html()
            writer.write(b"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nConnection: close\r\n\r\n")
            writer.write(html.encode())
            await writer.drain()
    except Exception as e:
        print("Web request error:", e)
    finally:
        writer.close()
        await writer.wait_closed()

async def run_web_server():
    try:
        server = await asyncio.start_server(handle_client, "0.0.0.0", 80)
        print("Web server listening on port 80")
    except Exception as e:
        print("Web server FAILED to start:", e)
        return
    while True:
        await asyncio.sleep(3600)

# ============================================================================
# Hardware loop (buttons, encoder, display, alarm check) -- same logic as
# the standalone version, just running as an asyncio task instead of a
# plain blocking while loop, and using the shared do_button_action /
# apply_encoder_delta functions so it can never diverge from the web UI.
# ============================================================================

def draw_button_legend(y_start, line_height=10):
    """Draws B1/B2/B3 lines on the OLED, one per row, using the exact
    same labels the web page shows -- so the physical display and the
    web UI can never show different button meanings."""
    (l1, _), (l2, _), (l3, _) = get_button_labels()
    oled.text("B1:%s" % l1[:13], 0, y_start)
    oled.text("B2:%s" % l2[:13], 0, y_start + line_height)
    oled.text("B3:%s" % l3[:13], 0, y_start + 2 * line_height)

async def hardware_loop():
    global Current_states, alarm_last_triggered_second

    while True:
        oled.fill(0)

        current_time = rtc.datetime()
        hour = current_time[4]
        minute = current_time[5]
        second = current_time[6]

        if ( alarm_enabled and not alarm_playing
             and hour == alarm_hour and minute == alarm_minute and second == alarm_second
             and alarm_last_triggered_second != second ):
            alarm_last_triggered_second = second
            StartAlarmSound()

        # Debounced button scanner -- confirms each edge is real (not
        # contact bounce) before acting on it.
        # NOTE: currently testing PULL_DOWN wiring, so idle is LOW and a
        # press pulls the pin HIGH -- watching for a RISING edge here,
        # the opposite of the original PULL_UP/falling-edge setup.
        for i in range(3):
            button_now = buttons[i].value()

            if Current_states[i] == 0 and button_now == 1:
                # Possible rising edge (press) -- confirm before acting.
                utime.sleep_ms(20)
                if buttons[i].value() == 1:
                    do_button_action(i)
                    Current_states[i] = 1
                # else: bounce noise -- ignore, Current_states stays 0
                continue

            Current_states[i] = button_now

        # Apply any encoder movement
        delta = GetEncoderChange()
        apply_encoder_delta(delta)

        current_volume = fm_radio.Volume
        current_frequency = fm_radio.Frequency

        # Render UI
        if current_menu == "Home":
            if alarm_playing:
                oled.text("ALARM! Press btn", 0, 0)
            oled.text(format_time(hour, minute, second), 0, 12)
            oled.text("A:%s%s" % (
                format_time(alarm_hour, alarm_minute, alarm_second),
                " *" if alarm_enabled else ""
            ), 0, 24)
            if fm_radio.Mute:
                oled.text("Volume: MUTED", 0, 38)
            else:
                oled.text("Volume: %02d" %current_volume, 0, 38)
            oled.text("Radio: %5.1f MHz" %current_frequency, 0, 52)

        elif current_menu == "Volume":
            oled.text("Volume menu", 0, 0)
            if volume_target == "Radio":
                if fm_radio.Mute:
                    oled.text("Radio: MUTED", 0, 14)
                else:
                    oled.text("Radio Vol: %02d" %current_volume, 0, 14)
            elif volume_target == "AlarmVol":
                oled.text("Alarm Vol: %02d" % alarm_volume, 0, 14)
            else:
                oled.text("AlmTone:%dHz" % alarm_tone_freq, 0, 14)
            draw_button_legend(28)

        elif current_menu == "Radio":
            oled.text("Radio menu", 0, 0)
            oled.text("FM %5.1f MHz" %current_frequency, 0, 14)
            draw_button_legend(28)

        elif current_menu == "Clock":
            if clock_submenu == "Home":
                oled.text("Clock menu", 0, 0)
                draw_button_legend(14)
                oled.text("Alarm: %s" % ("ON" if alarm_enabled else "OFF"), 0, 50)

            elif clock_submenu == "SetClock":
                rtc_now = rtc.datetime()
                oled.text("Set Clock", 0, 0)
                oled.text("%02d:%02d:%02d" % (rtc_now[4], rtc_now[5], rtc_now[6]), 0, 14)
                oled.text("Field: %s" % setclock_field, 0, 26)
                draw_button_legend(38)

            elif clock_submenu == "Alarm":
                oled.text("Alarm menu", 0, 0)
                oled.text("%02d:%02d:%02d %s" % (
                    alarm_hour, alarm_minute, alarm_second,
                    "ON" if alarm_enabled else "OFF"
                ), 0, 14)
                draw_button_legend(28)

            elif clock_submenu == "AlarmTime":
                oled.text("Set Alarm Time", 0, 0)
                oled.text("%02d:%02d:%02d %s" % (
                    alarm_hour, alarm_minute, alarm_second,
                    "ON" if alarm_enabled else "OFF"
                ), 0, 14)
                oled.text("Field: %s" % alarm_field, 0, 26)
                draw_button_legend(38)

        oled.show()
        await asyncio.sleep(0.1)

# ============================================================================
# Entry point
# ============================================================================

async def main():
    start_ap()
    await asyncio.gather(hardware_loop(), run_web_server())

try:
    asyncio.run(main())
except Exception as e:
    print("Fatal error in main():", e)
