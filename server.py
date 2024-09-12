import Enlace
import time
com = Enlace.Enlace('/dev/cu.usbmodem2101')
com.open()
com.activate()
time.sleep(5)
com.receiveFile('file')
com.close()