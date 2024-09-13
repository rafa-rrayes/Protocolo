import Enlace

com = Enlace.Enlace('/dev/cu.usbmodem1101', accept_all_objects=True, await_acception_objects=False)
com.open()
com.send_file('audio.mp3', 'file')
com.close()