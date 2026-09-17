# MFRC522 Library for MicroPython (Modified to be flexible with pins)
from machine import Pin, SPI
from os import uname

class MFRC522:
    DEBUG = False
    OK = 0
    NOTAGERR = 1
    ERR = 2

    REQIDL = 0x26
    REQALL = 0x52
    AUTHENT1A = 0x60
    AUTHENT1B = 0x61
    PICC_ANTICOLL1 = 0x93
    PICC_ANTICOLL2 = 0x95
    PICC_ANTICOLL3 = 0x97

    def __init__(self, sck=14, mosi=15, miso=12, rst=22, cs=13, spi_id=1):
        self.sck = Pin(sck)
        self.mosi = Pin(mosi)
        self.miso = Pin(miso)
        self.rst = Pin(rst, Pin.OUT)
        self.cs = Pin(cs, Pin.OUT)
        
        self.rst.value(1)
        self.cs.value(1)
        
        self.spi = SPI(spi_id, baudrate=1000000, polarity=0, phase=0,
                       sck=self.sck, mosi=self.mosi, miso=self.miso)
        self.init()

    def antenna_on(self):
        temp = self.read_reg(0x14)
        if not (temp & 0x03):
            self.set_bit_mask(0x14, 0x03)

    def reset(self):
        self.write_reg(0x01, 0x0F)

    def write_reg(self, addr, val):
        self.cs.value(0)
        self.spi.write(bytes([(addr << 1) & 0x7E, val]))
        self.cs.value(1)

    def read_reg(self, addr):
        self.cs.value(0)
        self.spi.write(bytes([((addr << 1) & 0x7E) | 0x80]))
        val = self.spi.read(1)
        self.cs.value(1)
        return val[0]

    def set_bit_mask(self, addr, mask):
        tmp = self.read_reg(addr)
        self.write_reg(addr, tmp | mask)

    def clear_bit_mask(self, addr, mask):
        tmp = self.read_reg(addr)
        self.write_reg(addr, tmp & (~mask))

    def comm_card(self, cmd, send_data):
        back_data = []
        back_len = 0
        status = self.ERR
        irq_en = 0x00
        wait_irq = 0x00

        if cmd == 0x0E:
            irq_en = 0x12
            wait_irq = 0x10
        elif cmd == 0x0C:
            irq_en = 0x77
            wait_irq = 0x30

        self.write_reg(0x02, irq_en | 0x80)
        self.clear_bit_mask(0x04, 0x80)
        self.set_bit_mask(0x0A, 0x80)
        self.write_reg(0x01, 0x00)

        for c in send_data:
            self.write_reg(0x09, c)

        self.write_reg(0x01, cmd)
        if cmd == 0x0C:
            self.set_bit_mask(0x0D, 0x80)

        i = 2000
        while True:
            n = self.read_reg(0x04)
            i -= 1
            if not i or not (n & 0x01) or (n & wait_irq):
                break

        self.clear_bit_mask(0x0D, 0x80)

        if i:
            if not (self.read_reg(0x06) & 0x1B):
                status = self.OK
                if n & irq_en & 0x01:
                    status = self.NOTAGERR
                if cmd == 0x0C:
                    n = self.read_reg(0x0A)
                    last_bits = self.read_reg(0x0C) & 0x07
                    if last_bits:
                        back_len = (n - 1) * 8 + last_bits
                    else:
                        back_len = n * 8
                    if n == 0:
                        n = 1
                    if n > 16:
                        n = 16
                    for _ in range(n):
                        back_data.append(self.read_reg(0x09))
            else:
                status = self.ERR

        return status, back_data, back_len

    def init(self):
        self.reset()
        self.write_reg(0x2A, 0x8D)
        self.write_reg(0x2B, 0x3E)
        self.write_reg(0x2D, 30)
        self.write_reg(0x2C, 0)
        self.write_reg(0x15, 0x40)
        self.write_reg(0x11, 0x3D)
        self.antenna_on()

    def request(self, req_mode):
        self.write_reg(0x0D, 0x07)
        (status, back_data, back_bits) = self.comm_card(0x0C, [req_mode])
        if status != self.OK or back_bits != 16:
            status = self.ERR
        return status, back_bits

    def anticoll(self, anticoll_n=PICC_ANTICOLL1):
        self.write_reg(0x0D, 0x00)
        ser_nr = [anticoll_n, 0x20]
        (status, back_data, back_bits) = self.comm_card(0x0C, ser_nr)
        if status == self.OK:
            if len(back_data) == 5:
                ser_nr_check = 0
                for i in range(4):
                    ser_nr_check = ser_nr_check ^ back_data[i]
                if ser_nr_check != back_data[4]:
                    status = self.ERR
            else:
                status = self.ERR
        return status, back_data