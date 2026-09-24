from machine import Pin, PWM, I2C
from mfrc522 import MFRC522
from i2c_lcd import I2cLcd
from umqtt_simple import MQTTClient
import network
import utime

# --- 1. Hardware Initialization ---
i2c = I2C(1, scl=Pin(3), sda=Pin(2), freq=400000)
lcd = I2cLcd(i2c, 0x27, 2, 16)

# --- 2. WiFi Connection Setup ---
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("Connecting to WiFi...")
        lcd.clear()
        lcd.putstr("Connecting WiFi...")
        wlan.connect("Wokwi-GUEST", "")
        
        timeout = 15
        while not wlan.isconnected() and timeout > 0:
            utime.sleep(1)
            timeout -= 1
            print(".", end="")
            
    if wlan.isconnected():
        print("\nWiFi Connected! IP:", wlan.ifconfig()[0])
        lcd.clear()
        lcd.putstr("WiFi Connected!")
        utime.sleep(1)
    else:
        print("\nWiFi Connection Failed!")
        lcd.clear()
        lcd.putstr("WiFi Failed")
        utime.sleep(1)

connect_wifi()

# --- 3. MQTT Configuration ---
MQTT_BROKER   = "YOUR_URL_MQTT_BROKER"
MQTT_PORT     = YOUR_PORT
MQTT_USER     = "YOUR_MQTT_USER"
MQTT_PASSWORD = "YOUR_MQTT_PASSWORD"  
MQTT_TOPIC    = b"garage/garage_events"

client = MQTTClient(
    client_id="YOUR_CLIENT_ID",
    server=MQTT_BROKER,
    port=MQTT_PORT,
    user=MQTT_USER,
    password=MQTT_PASSWORD,
    ssl=True,
    ssl_params={'server_hostname': MQTT_BROKER}
)

def connect_mqtt():
    try:
        client.connect()
        print("MQTT Connected successfully!")
    except Exception as e:
        print("MQTT Connection Error:", e)

connect_mqtt()

def send_mqtt_event(event_type, card_id, extra_data=None):
    try:
        if extra_data is not None:
            message = f'{{"event": "{event_type}", "card_id": "{card_id}", "duration_sec": {extra_data}}}'
        else:
            message = f'{{"event": "{event_type}", "card_id": "{card_id}"}}'
        client.publish(MQTT_TOPIC, message)
        print(f"MQTT Sent: {message}")
    except Exception as e:
        print("MQTT Send Error, reconnecting...", e)
        try:
            connect_mqtt()
            client.publish(MQTT_TOPIC, message)
        except Exception as ex:
            print("MQTT Reconnect Failed:", ex)

# --- 4. Hardware Components ---
reader = MFRC522(spi_id=1, sck=14, miso=12, mosi=15, cs=13, rst=22)

red_led = Pin(10, Pin.OUT)    # ON when parking is FULL
green_led = Pin(7, Pin.OUT)   # ON when parking is AVAILABLE

gate = PWM(Pin(4))
gate.freq(50)

ir1 = Pin(6, Pin.IN)
ir2 = Pin(5, Pin.IN)

trig = Pin(26, Pin.OUT)
echo = Pin(27, Pin.IN)

def set_gate(angle):
    duty = int(1000 + (angle / 180) * 8000)
    gate.duty_u16(duty)

def get_distance():
    trig.low()
    utime.sleep_us(2)
    trig.high()
    utime.sleep_us(10)
    trig.low()
    timeout = utime.ticks_add(utime.ticks_ms(), 30)
    while echo.value() == 0:
        if utime.ticks_diff(timeout, utime.ticks_ms()) <= 0:
            return 999
    pulse_start = utime.ticks_us()
    while echo.value() == 1:
        if utime.ticks_diff(timeout, utime.ticks_ms()) <= 0:
            return 999
    pulse_end = utime.ticks_us()
    distance = utime.ticks_diff(pulse_end, pulse_start) * 0.0343 / 2
    return distance

ALLOWED_ID_1 = [1, 3, 4, 0, 0]
ALLOWED_ID_2 = [17, 51, 68, 0, 0]

last_parking_status = None
entry_times = {}

# Non-blocking Gate State Management Variables
gate_state = "CLOSED"  # "CLOSED", "OPENING", "OPEN", "CLOSING"
gate_timer = 0
GATE_OPEN_DURATION = 3000  # 3 seconds in milliseconds

def update_parking_status():
    global last_parking_status
    car1 = ir1.value()
    car2 = ir2.value()
    
    if car1 == 0 and car2 == 0:
        red_led.value(0)
        green_led.value(1)
        current_status = "EMPTY"
    elif car1 == 1 and car2 == 1:
        red_led.value(1)
        green_led.value(0)
        current_status = "FULL"
    else:
        red_led.value(0)
        green_led.value(1)
        current_status = "HALF_FULL"
        
    if current_status != last_parking_status:
        last_parking_status = current_status
        send_mqtt_event("PARKING_STATUS", current_status)

print("System Initialized. Waiting for RFID card...")
lcd.clear()
lcd.putstr("System Ready    ")
set_gate(0)

# --- Main Program Loop (Non-blocking) ---
while True:
    try:
        current_time = utime.ticks_ms()
        
        # 1. Continuously update parking slots and IR sensors status
        update_parking_status()
        
        # 2. Background Gate State Machine (Non-blocking delay)
        if gate_state == "OPENING":
            set_gate(90)
            gate_timer = current_time
            gate_state = "OPEN"
        elif gate_state == "OPEN" and utime.ticks_diff(current_time, gate_timer) >= GATE_OPEN_DURATION:
            set_gate(0)
            gate_state = "CLOSED"
            lcd.clear()
            lcd.putstr("Scan RFID Card  ")

        # 3. Read Ultrasonic and RFID only when the gate is closed/idle
        if gate_state == "CLOSED":
            dist = get_distance()
            reader.init()
            (stat, tag_type) = reader.request(reader.REQIDL)
            
            if stat == reader.OK:
                # Check distance condition (Car must be within 50 cm)
                if dist > 50:
                    print(f"Car too far! Distance: {dist:.1f} cm")
                    lcd.clear()
                    lcd.putstr("Too Far! Closer ")
                    send_mqtt_event("WARNING_TOO_FAR", f"Dist: {dist:.1f}cm")
                    utime.sleep(1.5)
                    lcd.clear()
                    lcd.putstr("Scan RFID Card  ")
                else:
                    (stat, uid) = reader.anticoll(reader.PICC_ANTICOLL1)
                    card_id_str = str(uid)
                    print(f"Card detected with UID: {uid}")
                    
                    if uid == ALLOWED_ID_1 or uid == ALLOWED_ID_2:
                        if card_id_str not in entry_times:
                            # --- ENTRY WORKFLOW ---
                            entry_times[card_id_str] = current_time
                            print(f"Access Granted for {card_id_str}!")
                            lcd.clear()
                            lcd.putstr("You can Enter!  ")
                            send_mqtt_event("ENTRY", str(uid))
                            gate_state = "OPENING"
                        else:
                            # --- EXIT WORKFLOW ---
                            entry_time = entry_times.pop(card_id_str)
                            duration_sec = utime.ticks_diff(current_time, entry_time) // 1000
                            
                            print(f"Car leaving. Duration: {duration_sec} s")
                            lcd.clear()
                            lcd.putstr(f"Goodbye! {duration_sec}s")
                            
                            send_mqtt_event("EXIT", card_id_str, duration_sec)
                            gate_state = "OPENING"
                    else:
                        # --- ACCESS DENIED WORKFLOW ---
                        print("Access Denied!")
                        lcd.clear()
                        lcd.putstr("Access Denied   ")
                        send_mqtt_event("DENIED_ATTEMPT", str(uid))
                        utime.sleep(1.5)
                        lcd.clear()
                        lcd.putstr("Scan RFID Card  ")
                        
        utime.sleep(0.05) # Small delay to optimize CPU load
        
    except Exception as e:
        print("Loop Error:", e)
        utime.sleep(1)