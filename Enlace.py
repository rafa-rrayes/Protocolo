import serial
import time
from codec import Codec
from datetime import datetime
import os
import math

class InvalidCRC(Exception):
    def __init__(self, received, calculated, message="Invalid CRC"):
        self.message = message
        self.received = received
        self.calculated = calculated
class Timeout(Exception):
    def __init__(self, message="Timeout"):
        self.message = message

def splice_file(codec, file_data, save_name, packet_size=255, ):
    pacotes = []
    numero_de_pacotes = math.ceil(len(file_data)/packet_size)
    pacotes.append(codec.empacotar(3, numero_de_pacotes, save_name))
    for i in range(0, numero_de_pacotes):
        inicio = i*packet_size
        fim = inicio + packet_size
        pacotes.append(codec.empacotar(4, i+1, file_data[inicio:fim]))
    pacotes.append(codec.empacotar(6, 'nome', save_name))
    return pacotes
class Enlace(object):
    def __init__(self, name, packet_size=1024, **kwargs):
        self.name        = name
        self.packet_size = packet_size
        self.accept_all_files = kwargs.get('accept_all_files', False)
        self.receive_all_data = kwargs.get('receive_all_data', True)
        self.await_confirmation =kwargs.get('await_confirmation', True)
        self.send_confirmation =kwargs.get('send_confirmation', True)
        self.keep_log = kwargs.get('keep_log', True)
        self.requests_to_accept = {}
        self.requests_to_send = {}

        self.received = []

        self.buffer    = b""

        self.codec = Codec()
    def open(self):
        self.port = serial.Serial(self.name,
                                  115200,
                                  serial.EIGHTBITS,
                                  serial.PARITY_NONE,
                                  serial.STOPBITS_ONE,
                                  0.1)
        self._activate()
    
    def sendData(self, request_name, data):
        try:
            pacote = self.codec.empacotar(2, request_name, data)
        except Exception as e:
            raise e
        if not self.await_confirmation:
            self._send(pacote)
        else:
            self.requests_to_send[request_name] = [pacote]
            request = self.codec.empacotar(0, 'object', request_name+'///'+str(type(data))+'///'+str(len(pacote)))
            self._send(request)
    def sendFile(self, request_name, file_path, save_name=None, data=None):
        if not data:
            with open(file_path, 'rb') as f:
                data = f.read()
        if not save_name:
            save_name = file_path.split('/')[-1]
        pacotes = splice_file(self.codec, data, save_name)
        if not self.await_confirmation:
            for pacote in pacotes:
                self._send(pacote)
        else:
            self.requests_to_send[request_name] = pacotes
            request = self.codec.empacotar(0, 'file', request_name+'///'+save_name+'///'+str(len(pacotes)))
            self._send(request)
    def receive(self, accept_name):
        if not accept_name in self.requests_to_accept:
            raise Exception(f"No request to accept with name {accept_name}")
        if self.requests_to_accept[accept_name]['tipo'] == 'object':
            return self._receiveObject(accept_name)
        elif self.requests_to_accept[accept_name]['tipo'] == 'file':
            return self._receiveFile(accept_name)
        

    def _receiveObject(self, accept_name):
        self._send(self.codec.empacotar(1, 'object', accept_name))
        pacote = self.receber(0)
        return pacote['payload']
    def _receiveFile(self, accept_name):

        self._send(self.codec.empacotar(1, 'file', accept_name))
        data = b""
        ultimo_recebido = -1
        while True:
            try:
                pacote = self.receber(1)
            except Timeout:
                
                self._send(self.codec.empacotar(7, ultimo_recebido))
                continue
            if pacote['tipo'] == 6:
                save_name = pacote['payload']
                break
            elif pacote['tipo'] == 3:
                print(f"Recebendo inicio")
                total_de_pacotes = pacote['info']
                self._send(self.codec.empacotar(5, 0))
                ultimo_recebido = 0
            elif pacote['tipo'] == 4:
                print(f"Recebendo pacote {pacote['info']}")
                if pacote['info'] == ultimo_recebido+1:
                    data += pacote['payload']
                    ultimo_recebido = pacote['info']
                    print(f"Recebido pacote {ultimo_recebido}")
                    self._send(self.codec.empacotar(5, ultimo_recebido))
                else:
                    self._send(self.codec.empacotar(7, ultimo_recebido))
            elif pacote['tipo'] == 7:
                self._send(self.codec.empacotar(5, ultimo_recebido))
        with open(save_name, 'wb') as f:
            f.write(data)
        
    
        
    def _send(self, pacote):
        self.port.flush()
        self.port.write(pacote)
        if self.keep_log:
            self._log(self.codec.desempacotar(pacote))
    def receber(self, timeout=1):
        start = time.time()
        data = b""
        while (time.time() - start < timeout or timeout == 0):
            data += self.port.read(1)
            inicio = data.find(self.codec.start_sequence)
            if inicio != -1: 
                fim = data.find(self.codec.end_sequence, inicio)
                if fim == -1:
                    # If no valid #eNd# marker is found yet, continue reading
                    continue
                fim = fim + self.codec.extremes_size 
                pacote = data[inicio:fim] 
                data = data[:inicio] + data[fim:]
                
                pacote = self.codec.desempacotar(pacote)
                return pacote
        raise Timeout
    def _activate(self):
        import threading
        self.threadRead = threading.Thread(target=self._keep_reading)
        self.threadRead.start()
    def _keep_reading(self):
        while True:
            self.buffer += self.port.read(1)
            inicio = self.buffer.find(self.codec.start_sequence)
            if inicio != -1: 
                fim = self.buffer.find(self.codec.end_sequence, inicio)
                if fim == -1:
                    # If no valid #eNd# marker is found yet, continue reading
                    continue
                # recebeu um pacote
                    
                fim = fim + self.codec.extremes_size
                pacote = self.buffer[inicio:fim] 
                self.buffer = self.buffer[:inicio] + self.buffer[fim:]
                
                pacote = self.codec.desempacotar(pacote)
                self._log(pacote, recebido=True)

                # if pacote['crc_recebido'] != pacote['crc_calculado']:
                #     raise InvalidCRC(pacote['crc_recebido'], pacote['crc_calculado'])

                if pacote['tipo'] == 0:
                    tipo = pacote['info']
                    name, tipo, size = pacote['payload'].split('///')
                    if tipo == 'object':
                        self.requests_to_accept[name] = {'tipo': tipo, 'payloadSize': size}
                    elif tipo == 'file':
                        self.requests_to_accept[name] = {'tipo': tipo, 'n packets': size}
                elif pacote['tipo'] == 1:
                    self._accepted_goSend(pacote['payload'])
                
                return pacote
        
    def _accepted_goSend(self, accept_name):
        pacotes = self.requests_to_send[accept_name]
        total_de_pacotes = len(pacotes)
        ultimo_recebido = -1
        while True:
            pacote = pacotes[ultimo_recebido+1]
            self._send(pacote)
            if self.await_confirmation:
                try:
                    confirmacao = self.receber(2)
                except Timeout:
                    self._send(self.codec.empacotar(7, ultimo_recebido))
                    continue
                if confirmacao['tipo'] == 5:
                    ultimo_recebido = confirmacao['info']
                if confirmacao['tipo'] == 7:
                    ultimo_recebido = confirmacao['info']
            else:
                ultimo_recebido += 1
            if ultimo_recebido == total_de_pacotes-1:
                break
        self.requests_to_send.pop(accept_name)
                
        
    def close(self):
        self.port.close()
        self.threadRead.join()
    def clear_buffer(self):
        self.buffer = b""
    def _log(self, pacote, recebido=False):
        hora = datetime.now()
        # formated time:
        hora = hora.strftime("%d/%m/%Y %H:%M:%S:%f")
        tipo = pacote['tipo']
        linha = hora
        if recebido:
            linha += " Recebido / "
        else:
            linha += " Enviado / "

        if tipo == 0:
            linha += f" Handshake: {pacote['info']} / "
        elif tipo == 1:
            linha += f" Handshake confirmation: {pacote['info']} / "
        elif tipo == 3:
            linha += f" Start of data: {pacote['payload']} / numero de pacotes: {pacote['info']} / "
        elif tipo == 4:
            linha += f" Data: {pacote['info']} / "
        elif tipo == 5:
            linha += f" Data confirmation: {pacote['info']} / "
        elif tipo == 6:
            linha += f" #eNd# of data: {pacote['payload']} / "
        elif tipo == 7:
            linha += f" Error message: {pacote['payload']} / "
        linha += f" Tamanho: {pacote['total_size']} / "
        linha += f" CRC recebido: {pacote['crc_recebido']} / "
        linha += f" CRC calculado: {pacote['crc_calculado']}"
        if 'log.txt' not in os.listdir():
            with open('log.txt', 'w') as f:
                f.write(linha+'\n')
        else:
            with open('log.txt', 'a') as f:
                f.write(linha+'\n')