from protocolo import Enlace

com = Enlace('/dev/cu.usbmodem101')
com.open()

com.send_file('image.jpeg', 'file')
