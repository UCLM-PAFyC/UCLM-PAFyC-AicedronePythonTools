import socket
import serial
import threading
import select

# Configuración
SERIAL_PORT = '/dev/ttyACM0'  # Puerto serial
BAUD_RATE = 921600  # Tasa de baudios
TCP_IP = '0.0.0.0'  # IP para el servidor TCP
TCP_PORT = 8080  # Puerto para el servidor TCP

# Abrir puerto serial
try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0)  # Modo no bloqueante para el serial
except serial.SerialException as e:
    print(f"Error opening serial port {SERIAL_PORT}: {e}")
    exit(1)

def handle_client(conn, addr):
    """Maneja la conexión con el cliente"""
    print(f"Connection from {addr} has been established.")
    conn.setblocking(0)  # Modo no bloqueante para el socket

    while True:
        try:
            # Espera datos de la conexión TCP o del puerto serial
            ready_to_read, _, _ = select.select([conn, ser], [], [], 0.1)
            
            if ser in ready_to_read:
                data = ser.read(1024)  # Lee datos del puerto serial
                if data:
                    conn.sendall(data)  # Envía datos al cliente TCP

            if conn in ready_to_read:
                data = conn.recv(1024)  # Recibe datos del cliente TCP
                if data:
                    ser.write(data)  # Escribe datos al puerto serial
                else:
                    break  # Si no hay datos, se rompe el bucle (desconexión)
        except (BlockingIOError, socket.error):
            continue  # Maneja errores temporales y continúa
        except Exception as e:
            print(f"Error: {e}")
            break

    conn.close()
    print(f"Connection from {addr} closed.")

def start_server():
    """Inicia el servidor TCP"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((TCP_IP, TCP_PORT))
        s.listen()
        print(f"Listening on {TCP_IP}:{TCP_PORT}...")

        while True:
            conn, addr = s.accept()  # Acepta nuevas conexiones
            thread = threading.Thread(target=handle_client, args=(conn, addr))
            thread.start()  # Inicia un nuevo hilo para manejar la conexión
            print(f"Active connections: {threading.active_count() - 1}")

if __name__ == "__main__":
    start_server()  # Inicia el servidor
