from protocolo import Enlace
import time

com = Enlace('/dev/cu.usbmodem2101')
com.open()
time.sleep(5)
com.accept('file')
com.close()