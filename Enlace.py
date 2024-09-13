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
    pacotes.append(codec.empacotar(6, i+2, save_name))
    return pacotes
class Enlace(object):
    def __init__(self, name, packet_size=1024, **kwargs):
        self.name        = name
        self.packet_size = packet_size
        self.accept_all_files = kwargs.get('accept_all_files', False)
        self.accept_all_objects = kwargs.get('accept_all_objects', True)
        self.await_acception_objects =kwargs.get('await_acception_objects', True)
        self.await_acception_files =kwargs.get('await_acception_files', True)
        self.send_confirmation =kwargs.get('send_confirmation', True)
        self.keep_log = kwargs.get('keep_log', True)
        self.requests_to_accept = {}
        self.requests_to_send = {}

        self.objects_received = {}

        self.buffer    = b""

        self.codec = Codec()

        self.accepted = {}
    def connect(self, timeout=1):
        for i in range(3):
            if not 'connect' in self.objects_received:
                self.send_object('start?', 'connect')
                try:
                    confirmation = self.receive_packet(timeout/3)
                except Timeout:
                    continue
                if confirmation['tipo'] == 2 and confirmation['info'] == 'connect' and confirmation['payload'] == 'accept':
                    self.send_object('go', 'connect')
                    return True
            else:
                self.send_object('accept', 'connect')
                confirmation = self.receive_packet(timeout)
                if confirmation['tipo'] == 2 and confirmation['info'] == 'connect' and confirmation['payload'] == 'go':
                    return True
        return False
    def open(self):
        self.port = serial.Serial(self.name,
                                  115200,
                                  serial.EIGHTBITS,
                                  serial.PARITY_NONE,
                                  serial.STOPBITS_ONE,
                                  0.1)
        
        self._activate()
    def _send(self, pacote): # envia um pacote
        self.port.flush()
        self.port.write(pacote)
        if self.keep_log:
            self._log(self.codec.desempacotar(pacote))

    def send_object(self, data, request_name=''): # manda uma request para enviar um objeto
        if not self.await_acception_objects:
            try:
                pacote = self.codec.empacotar(2, request_name, data)
            except Exception as e:
                raise e
            self._send(pacote)
            return
        else:  
            try:
                pacote = self.codec.empacotar(2, request_name, data)
            except Exception as e:
                raise e
            else:
                self.requests_to_send[request_name] = [pacote]
                request = self.codec.empacotar(0, 'object', request_name+'///'+str(type(data))+'///'+str(len(pacote)))
                self._send(request)
    def send_file(self, file_path,request_name='', save_name=None, data=None): # manda uma request para enviar um arquivo
        if not data:
            with open(file_path, 'rb') as f:
                data = f.read()
        if not save_name:
            save_name = file_path.split('/')[-1]
        pacotes = splice_file(self.codec, data, save_name)
        self.requests_to_send[request_name] = pacotes
        if not self.await_acception_files:
            self._accepted_goSend(request_name)
        else:
            request = self.codec.empacotar(0, 'file', request_name+'///'+save_name+'///'+str(len(pacotes)))
            self._send(request)

    def accept(self, accept_name):  # aceita uma request para receber um objeto ou arquivo
        if not accept_name in self.requests_to_accept:
            raise Exception(f"No request to accept with name {accept_name}")
        if self.requests_to_accept[accept_name]['type'] == 'object':
            return self._receive_object(accept_name)
        elif self.requests_to_accept[accept_name]['type'] == 'file':
            return self._receive_file(accept_name)
        
    def _error_during_receive(self, next_packet):
        self._send(self.codec.empacotar(7, next_packet))
    def _receive_object(self, accept_name):
        self.accepted[accept_name] = None
        self._send(self.codec.empacotar(1, 'object', accept_name))
        while self.accepted[accept_name] == None:
            continue
        objeto = self.accepted[accept_name]
        self.accepted.pop(accept_name)
        self._send(self.codec.empacotar(5, 0))  
        return objeto
    
    def _receive_file(self, accept_name): # recebe um arquivo
        self.pauseRead()
        self._send(self.codec.empacotar(1, 'file', accept_name))
        data = b""
        ultimo_recebido = -1
        while True:
            try:
                pacote = self.receive_packet(1)
            except Timeout:
                self._error_during_receive(ultimo_recebido)
                continue

            if pacote['tipo'] == 3: # inicio de dados
                self._send(self.codec.empacotar(5, 0))
                ultimo_recebido = 0

            # recebe um pacote de dados
            elif pacote['tipo'] == 4:
                if pacote['info'] == ultimo_recebido+1:
                    data += pacote['payload']
                    ultimo_recebido = pacote['info']
                    self._send(self.codec.empacotar(5, ultimo_recebido))
                else:
                    self._error_during_receive(ultimo_recebido)

            # fim dos dados
            elif pacote['tipo'] == 6: 
                save_name = pacote['payload']
                ultimo_recebido = pacote['info']
                self._send(self.codec.empacotar(5, ultimo_recebido))
                break

            # se der erro, envia confirmação do ultimo pacote recebido
            elif pacote['tipo'] == 7:
                self._send(self.codec.empacotar(5, ultimo_recebido)) 
        
        with open(save_name, 'wb') as f:
            f.write(data)
        self.resumeRead()
    def _accepted_goSend(self, accept_name):  # envia um objeto ou arquivo aceito
        pacotes = self.requests_to_send[accept_name]
        total_de_pacotes = len(pacotes)
        ultimo_recebido = -1
        while True:
            pacote = pacotes[ultimo_recebido+1]
            self._send(pacote)
            try:
                confirmacao = self.receive_packet(1)
            except Timeout:
                self._send(self.codec.empacotar(7, ultimo_recebido))
                continue

            # atualiza o ultimo pacote recebido
            if confirmacao['tipo'] == 5 or confirmacao['tipo'] == 7:
                ultimo_recebido = confirmacao['info']

            if ultimo_recebido == total_de_pacotes-1:
                break

        self.requests_to_send.pop(accept_name)
        
    
    def receive_packet(self, timeout=1):
        self.pauseRead()
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
                
                self.resumeRead()
                fim = fim + self.codec.extremes_size 
                pacote = data[inicio:fim] 
                data = data[:inicio] + data[fim:]
                pacote = self.codec.desempacotar(pacote)
                self._log(pacote, recebido=True)
                return pacote
        self.resumeRead()
        raise Timeout
    def _activate(self):
        import threading
        self.reading = True
        self.closePort = False
        self.threadRead = threading.Thread(target=self._keep_reading)
        self.threadRead.start()
    def _keep_reading(self):
        while True:
            if self.closePort:
                break
            if not self.reading:
                time.sleep(0.1)
                continue
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
                    request_type = pacote['info']
                    name, tipo, size = pacote['payload'].split('///')
                    if request_type == 'object':
                        self.requests_to_accept[name] = {'type': 'object',
                                                         'as': tipo,
                                                        'payloadSize': size}
                    elif request_type == 'file':
                        self.requests_to_accept[name] = {'type': 'file',
                                                         'as': tipo,
                                                        'n packets': size}
                    else:
                        raise Exception(f"Tipo de dado não reconhecido: {tipo}")
                elif pacote['tipo'] == 1:
                    self._accepted_goSend(pacote['payload'])
                elif pacote['tipo'] == 2:
                    if self.accept_all_objects:
                        self.objects_received[pacote['info']] = pacote['payload']
                    if pacote['info'] in self.accepted:
                        self.accepted[pacote['info']] = pacote['payload']
        return

                
    def pauseRead(self):
        self.reading = False
    def resumeRead(self):
        self.reading = True
    def close(self):
        self.closePort = True
        self.threadRead.join()
        self.port.close()
    def clear_buffer(self):
        self.buffer = b""
    def get_objects(self):
        objects = self.objects_received
        self.objects_received = {}
        return objects
    def _log(self, pacote, recebido=False):
        hora = datetime.now()
        # formated time:
        hora = hora.strftime("%d/%m/%Y %H:%M:%S:%f")
        tipo = pacote['tipo']
        linha = hora
        if recebido:
            linha += " | Recebido | "
        else:
            linha += " | Enviado | "

        if tipo == 0:
            name = pacote['payload'].split('///')[0]
            linha += f"Request: {name} | {pacote['info']} | "
        elif tipo == 1:
            name = pacote['payload'].split('///')[0]
            linha += f"Accept request: {name} | "
        elif tipo == 2:
            linha += f"Object: {pacote['info']} | "
        elif tipo == 3:
            linha += f"Start of data: {pacote['payload']} | numero de pacotes: {pacote['info']} | "
        elif tipo == 4:
            linha += f"Data: {pacote['info']} | "
        elif tipo == 5:
            linha += f"Data confirmation: {pacote['info']} | "
        elif tipo == 6:
            linha += f"End of data: {pacote['payload']} | "
        elif tipo == 7:
            linha += f" Error message: {pacote['payload']} | "
        linha += f"Tamanho pacote: {pacote['total_size']} | "
        linha += f"CRC recebido: {pacote['crc_recebido']} | "
        linha += f"CRC calculado: {pacote['crc_calculado']} | "
        linha += f"Packet ID: {pacote['packet_id']}"
        if 'log.txt' not in os.listdir():
            with open('log.txt', 'w') as f:
                f.write(linha+'\n')
        else:
            with open('log.txt', 'a') as f:
                f.write(linha+'\n')