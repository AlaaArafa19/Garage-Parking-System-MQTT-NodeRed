# Smart Garage Parking System 🚗🅿️

An IoT-based Smart Garage Monitoring and Control System developed using **Raspberry Pi Pico W**, **MicroPython**, and **Node-RED**. This project simulates real-time parking management, automated access control, environmental monitoring, and alert notifications.

---

## 📂 Project Structure

The repository is organized into the following main directories:

* 📁 **`Wokwi/`** : Contains the MicroPython firmware, simulation diagram, and required libraries for the Raspberry Pi Pico W.
* 📁 **`Node-RED/`** : Contains the JSON flow configuration for the Node-RED dashboard, telemetry handling, and automation logic.

---

## 🛠️ Hardware & Tech Stack

* **Microcontroller:** Raspberry Pi Pico W
* **Programming Language:** MicroPython
* **Sensors & Actuators:** MFRC522 RFID Reader, HC-SR04 Ultrasonic Sensor, DHT22 Temperature & Humidity Sensor, Analog Gas Sensor, SG90 Servo Motor, I2C LCD Display, Buzzer, and LEDs.
* **Protocols & Dashboard:** MQTT (HiveMQ broker), TCP/UDP Sockets, and Node-RED Dashboard.

---

## 🚀 Getting Started

### 1. Wokwi Simulation (Firmware)
You can test and run the live hardware simulation directly through Wokwi:
👉 **[Wokwi Simulation Link](https://wokwi.com/projects/475218180727966721)**

To run it locally or review the files:
1. Ensure the following files are included in your workspace:
   * `main.py` (Main logic)
   * `diagram.json` (Circuit connections)
   * `i2c_lcd.py` & `lcd_api.py` (LCD display drivers)
   * `mfrc522.py` (RFID reader driver)
   * `umqtt_simple.py` (MQTT communication)

### 2. Node-RED Dashboard
1. Open your Node-RED interface.
2. Click on the Menu (top right) -> **Import**.
3. Select the `flows.json` file located inside the `Node-RED` folder.
4. Click **Import** to load the complete dashboard layout, MQTT nodes, and alert triggers.
5. Configure your MQTT broker nodes and notification settings (Telegram/Email) if required.

---

## 👩‍💻 Author
**Alaa Arafa**  
*Computer Science and Engineering Student | IoT & Embedded Systems Developer*