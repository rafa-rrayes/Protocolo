import Enlace

com = Enlace.Enlace('/dev/cu.usbmodem1101')
com.open()
com.activate()
com.sendFile('file', 'audio.mp3')