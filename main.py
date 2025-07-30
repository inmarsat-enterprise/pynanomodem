from pynanomodem import SatelliteModem


def main():
    modem = SatelliteModem()
    modem.connect(baudrate=115200)
    modem.disconnect()


if __name__ == '__main__':
    main()
