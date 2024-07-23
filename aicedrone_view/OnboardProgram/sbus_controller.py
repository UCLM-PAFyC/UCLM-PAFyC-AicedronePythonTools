import serial
import time

class SBUSController:
    def __init__(self, port, filter_x=0.3, filter_y=0.3):
        """
        Inicializa el controlador SBUS con los valores y configuraciones necesarios.
        
        Args:
        port (str): Puerto serial al que se conectará.
        filter_x (float): Valor de filtrado para x.
        filter_y (float): Valor de filtrado para y.
        """
        self.sbus_values = [1023] * 16  # Inicializar los valores SBUS
        self.serialport = serial.Serial()
        self.serialport.port = port
        self.serialport.baudrate = 100000
        self.serialport.parity = serial.PARITY_EVEN
        self.serialport.stopbits = serial.STOPBITS_TWO
        self.serialport.timeout = 1
        self.x = 0.5
        self.y = 0.5
        self.filter_x = filter_x
        self.filter_y = filter_y

    def connect_serial(self):
        """
        Conecta o desconecta el puerto serial.
        """
        if not self.serialport.is_open:
            self.serialport.open()
            print("Serial port connected")
        else:
            self.serialport.close()
            print("Serial port disconnected")

    def scan_ports(self):
        """
        Escanea y devuelve una lista de puertos seriales disponibles.
        
        Returns:
        list: Lista de descripciones de los puertos seriales disponibles.
        """
        available_ports = serial.tools.list_ports.comports()
        ports_info = []
        for port in available_ports:
            ports_info.append(f"Port: {port.device}, Description: {port.description}")
        return ports_info

    def send_data(self, data):
        """
        Envía datos a través del puerto serial.
        
        Args:
        data (str): Datos a enviar.
        """
        if self.serialport.is_open:
            self.serialport.write(data.encode())
            print(f"Sent data: {data}")

    def sbus_timer(self):
        """
        Actualiza los valores SBUS periódicamente y llama a `sbus_output`.
        """
        while True:
            self.sbus_values[2] += 1
            if self.sbus_values[2] >= 2048:
                self.sbus_values[2] = 0
            smothx = 0.5 - self.x
            smothx *= self.filter_x
            smothx = 0.5 - smothx
            smothy = 0.5 - self.y
            smothy *= self.filter_y
            smothy = 0.5 - smothy
            self.sbus_values[0] = int(2047 * smothx)
            self.sbus_values[1] = int(2047 * (1 - smothy))
            self.sbus_output(self.sbus_values, 16)
            time.sleep(0.01)  # Sleep for 10ms

    def sbus_output(self, values, num_values):
        """
        Convierte los valores SBUS en un formato adecuado y los envía a través del puerto serial.
        
        Args:
        values (list): Lista de valores SBUS.
        num_values (int): Número de valores a enviar.
        
        Returns:
        int: Número de bytes escritos o 0 si el puerto no está abierto.
        """
        byteindex = 1
        offset = 0
        oframe = bytearray(25)
        oframe[0] = 0x0f
        for i in range(min(num_values, 16)):
            value = values[i]
            if value > 0x07ff:
                value = 0x07ff
            while offset >= 8:
                byteindex += 1
                offset -= 8
            oframe[byteindex] |= (value << offset) & 0xff
            oframe[byteindex + 1] |= (value >> (8 - offset)) & 0xff
            oframe[byteindex + 2] |= (value >> (16 - offset)) & 0xff
            offset += 11
        if self.serialport.is_open:
            writed = self.serialport.write(oframe)
            return writed
        return 0

    def set_pitch(self, value):
        """
        Ajusta el valor de pitch en SBUS.
        
        Args:
        value (int): Valor de pitch.
        """
        self.sbus_values[1] = value

    def set_roll(self, value):
        """
        Ajusta el valor de roll en SBUS.
        
        Args:
        value (int): Valor de roll.
        """
        self.sbus_values[3] = value

    def set_yaw(self, value):
        """
        Ajusta el valor de yaw en SBUS.
        
        Args:
        value (int): Valor de yaw.
        """
        self.sbus_values[0] = value

    def update_coordinates(self, x, y):
        """
        Actualiza las coordenadas x e y.
        
        Args:
        x (float): Nueva coordenada x.
        y (float): Nueva coordenada y.
        """
        self.x = x
        self.y = y
