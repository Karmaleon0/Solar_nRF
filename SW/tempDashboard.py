import sys
import re
import time
import csv
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QLabel, QWidget, QVBoxLayout, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import QTimer, QThread, pyqtSignal, Qt
from PyQt6.QtGui import QFont, QColor
import serial
from datetime import datetime
import serial.tools.list_ports

## COM_PORT = 'COM4'  # Change as needed
BAUD_RATE = 115200

import serial.tools.list_ports  # Add to your imports

class SerialReaderThread(QThread):
    data_received = pyqtSignal(str, float, int, float)  # name, temp, rssi, timestamp

    def __init__(self):
        super().__init__()
        self.running = True
        self.ser = None

        # Look for J-Link port
        ports = list(serial.tools.list_ports.comports())
        for port in ports:
            if "JLink" in port.description:
                try:
                    self.ser = serial.Serial(port.device, BAUD_RATE, timeout=1)
                    print(f"Connected to {port.device} ({port.description})")
                    break
                except Exception as e:
                    print(f"Error opening {port.device}: {e}")

        if not self.ser:
            print("No J-Link COM port found.")


    def run(self):
        if not self.ser:
            return

        while self.running:
            line = self.ser.readline().decode(errors='ignore').strip()
            match = re.search(r'Temp from (.+?): (\-?\d+\.\d{2}) C \(RSSI (-?\d+)\)', line)
            if match:
                name = match.group(1)
                temp = float(match.group(2))
                timestamp = time.time()
                rssi = int(match.group(3))
                self.data_received.emit(name, temp, rssi, timestamp)

    def stop(self):
        self.running = False
        self.wait()

def add_glow(label: QLabel, color_hex: str, radius=20, strength=0.9):
    glow = QGraphicsDropShadowEffect()
    glow.setBlurRadius(radius)
    glow.setColor(QColor(color_hex))
    glow.setOffset(0, 0)
    label.setGraphicsEffect(glow)

class TempDashboard(QWidget):
    def __init__(self):
        super().__init__()

        self.last_time = time.time()  # initialize to now, so elapsed time starts counting
        now_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"temperature_log_{now_str}.csv"

        self.setWindowTitle("tempDashboard")
        self.setGeometry(300, 300, 450, 220)

        # Fonts
        self.temp_font = QFont("Segoe UI", 120, QFont.Weight.Bold)
        self.info_font = QFont("Segoe UI", 60)

        # Layout
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        # Temp label (big neon number)
        self.temp_label = QLabel("")
        self.temp_label.setFont(self.temp_font)
        self.temp_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Elapsed time label
        self.elapsed_label = QLabel("")
        self.elapsed_label.setFont(self.info_font)
        self.elapsed_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.elapsed_label.setStyleSheet("color: #FF69B4;")  # Hot Pink neon text
        add_glow(self.elapsed_label, "#FF69B4", radius=25)

        # RSSI label
        self.rssi_label = QLabel("")
        self.rssi_label.setFont(self.info_font)
        self.rssi_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.rssi_label.setStyleSheet("color: #FF69B4;")  # Hot Pink neon text
        add_glow(self.rssi_label, "#FF69B4", radius=25)

        # ... after creating labels:

        self.temp_label = QLabel("")
        self.temp_label.setFont(self.temp_font)
        self.temp_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.temp_label.setText("0.00 °C")
        self.temp_label.setStyleSheet("color: #00FFFF;")
        add_glow(self.temp_label, "#00FFFF", radius=40)

        self.elapsed_label = QLabel("")
        self.elapsed_label.setFont(self.info_font)
        self.elapsed_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.elapsed_label.setText("No data received yet")
        self.elapsed_label.setStyleSheet("color: #FF69B4;")
        add_glow(self.elapsed_label, "#FF69B4", radius=25)

        self.rssi_label = QLabel("")
        self.rssi_label.setFont(self.info_font)
        self.rssi_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.rssi_label.setText("RSSI: N/A")
        self.rssi_label.setStyleSheet("color: #FF69B4;")
        add_glow(self.rssi_label, "#FF69B4", radius=25)


        layout.addWidget(self.temp_label)
        layout.addWidget(self.elapsed_label)
        layout.addWidget(self.rssi_label)

        self.setLayout(layout)

        # Dark background
        self.setStyleSheet("""
            QWidget {
                background-color: #0f0f1a;
                border-radius: 20px;
            }
            QLabel {
                padding: 5px;
            }
        """)

        self.serial_thread = SerialReaderThread()
        self.serial_thread.data_received.connect(self.update_data)
        self.serial_thread.start()

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_elapsed)
        self.timer.start(1000)

        self.csv_file = open(filename, "a", newline="")
        self.csv_writer = csv.writer(self.csv_file)
        if self.csv_file.tell() == 0:
            self.csv_writer.writerow(["Timestamp", "Name", "Temperature", "RSSI"])

    def update_data(self, name, temp, rssi, timestamp):
        neon_cyan = "#00FFFF"
        self.temp_label.setText(f"{temp:.2f} °C")
        self.temp_label.setStyleSheet(f"color: {neon_cyan};")
        add_glow(self.temp_label, neon_cyan, radius=40)

        self.rssi_label.setText(f"RSSI: {rssi} dBm")

        self.last_time = timestamp

        dt = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
        self.csv_writer.writerow([dt, name, f"{temp:.2f}", rssi])
        self.csv_file.flush()

    def update_elapsed(self):
        if self.last_time is None:
            self.elapsed_label.setText("No data received yet")
        else:
            elapsed = time.time() - self.last_time
            self.elapsed_label.setText(f"Last update: {int(elapsed)}s ago")

    def closeEvent(self, event):
        self.serial_thread.stop()
        self.csv_file.close()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TempDashboard()
    window.show()
    sys.exit(app.exec())
