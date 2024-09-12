import binascii
import pickle
import math
class Codec:
    def __init__(self, **kwargs) -> None:
        self.crc_lenght = 2 or kwargs.get('crc_lenght')
        self.crc_hash = 0xFFFF or kwargs.get('crc_hash')
        self.max_payload = 255 or kwargs.get('max_payload')
        self.info_size = 9 or kwargs.get('info_size')
        self.payload_size_length = math.ceil(self.max_payload.bit_length()/8) 
        self.start_sequence = b'#StR#' or kwargs.get('start_sequence')
        self.end_sequence = b'#eNd#' or kwargs.get('end_sequence')
        self.extremes_size = len(self.start_sequence)
        self.header_size = self.payload_size_length + self.info_size + self.crc_lenght + 4
        self.header_slice = slice(self.extremes_size, self.extremes_size+self.header_size)

        if type(self.crc_lenght) != int:
            raise Exception("crc_lenght deve ser um inteiro")
        if type(self.crc_hash) != int:
            raise Exception("crc_hash deve ser um inteiro")
        if type(self.max_payload) != int:
            raise Exception("max_payload deve ser um inteiro")
        if type(self.info_size) != int:
            raise Exception("info_size deve ser um inteiro")
        if type(self.start_sequence) != bytes:
            raise Exception("start_sequence deve ser bytes")
        if type(self.end_sequence) != bytes:
            raise Exception("end_sequence deve ser bytes")
        if len(self.start_sequence) != len(self.end_sequence):
            raise Exception("Sequências de início e fim devem ter o mesmo tamanho")
        if self.start_sequence == self.end_sequence:
            raise Exception("Sequências de início e fim não podem ser iguais")
        
        self.packet_id = 0
    def crc16(self, data: bytes):
        crc16 = binascii.crc_hqx(data, self.crc_hash)
        crc16 = crc16.to_bytes(self.crc_lenght, 'big')
        return crc16
    def empacotar(self, tipo:int, info=None, payload=None):
        """
        Gera um pacote. 3 start bytes, 10 bytes de header, payload, 3 bytes de EOP

        Payload pode ser int, bytes ou string. Deve conter até 255 bytes.

        Info pode ser int ou string. Deve conter até 7 bytes.
        Tipo: 

        0: request
        1: accept
        2: Object
        3: Start of data
        4: Data
        5: Data confirmation
        6: end of data
        7: Error message

        Info: até 7 caracteres
        Qualquer tipo de informação extra. Para Handshakes,
        é geralmente o nome do processo a ser confirmado. 
        Para dados, é geralmente o indice do pacote enviado/recebido. 

        header:
        1 byte: tipo
        1 byte: tipos de dados
        2 bytes: packet_id
        x bytes: crc-16
        x byte: tamanho do payload
        x bytes: info
        """
        if info == None:
            info = ''
        if type(info) != str and type(info) != int:
            raise Exception("Info deve ser string ou int")
        if type(info) == str and len(info) > self.info_size:
            raise Exception(f"Info muito grande, máximo {self.info_size} bytes")
        if tipo > 7 or tipo < 0:
            raise Exception("Tipo inválido")
        
        types = 0     
        if type(info) == int:
            types += 3
            try:
                info = info.to_bytes(self.info_size, byteorder='big', signed=True)
            except:
                raise Exception(f"Info muito grande, máximo {self.info_size} bytes")
        elif type(info) == str:
            info = info.encode('utf-8')

        if payload == None:
            payload = b''
        if tipo == 2:
            payload = pickle.dumps(payload)
        elif type(payload) == int:
            types +=1
            size = math.ceil(payload/255)
            payload = payload.to_bytes(length=size, byteorder='big')
        elif type(payload) == bytes:
            types += 2
        elif type(payload) == str:
            payload = payload.encode('utf-8')
        if len(payload) > self.max_payload:
            raise Exception(f"Payload muito grande, máximo {self.max_payload} bytes")
    
        sop = self.start_sequence
        eop = self.end_sequence

        crc = self.crc16(payload)
        header = b''
        header += tipo.to_bytes(1, 'big')  
        header+= types.to_bytes(1, 'big')
        header+= self.packet_id.to_bytes(2, 'big')
        header += crc
        header+= len(payload).to_bytes(self.payload_size_length, byteorder='big')
        header += info
        while len(header) < self.header_size:
            header+= b'+'
        
        if payload.find(self.end_sequence) != -1:
            raise Exception(f"Payload não pode conter sequência de fim: {self.end_sequence}")
        if payload.find(self.start_sequence) != -1:
            raise Exception(f"Payload não pode conter sequência de início: {self.start_sequence}")
        if info.find(self.end_sequence) != -1:
            raise Exception(f"Info não pode conter sequência de fim: {self.end_sequence}")
        if info.find(self.start_sequence) != -1:
            raise Exception(f"Info não pode conter sequência de início: {self.start_sequence}")
        self.packet_id += 1
        return (sop+header+payload+eop)

    def desempacotar(self, pacote):
        if pacote[:self.extremes_size] != self.start_sequence:
            raise Exception("Pacote não contem sequência de início")
        if pacote[-self.extremes_size:] != self.end_sequence:
            raise Exception("Pacote não contem sequência de fim")
        header = pacote[self.header_slice]
        """
        1 byte: tipo
        1 byte: tipos de dados
        2 bytes: packet_id
        x bytes: crc-16
        x byte: tamanho do payload
        x bytes: info
        """
        tipo = header[0]
        tipo_dados = header[1]
        packet_id = int.from_bytes(header[2:4], byteorder='big')
        crc_recebido = header[4:self.crc_lenght+2]
        tamanho_payload = int.from_bytes(header[4+self.crc_lenght:4+self.crc_lenght+self.payload_size_length], byteorder='big')
        info = header[4+self.crc_lenght+self.payload_size_length:]
        payload = pacote[self.header_size+self.extremes_size:-self.extremes_size]
        

        crc_calculado = self.crc16(payload)

        if tipo_dados <=2: # info é string
            info = info.decode('utf-8').strip('+')
        else: # info é int
            info = int.from_bytes(info, byteorder='big', signed=True)
        if tipo == 2: # payload é objeto
            payload = pickle.loads(payload)
        elif tipo_dados == 0 or tipo_dados == 3: # payload é string
            payload = payload.decode('utf-8')
        elif tipo_dados == 1 or tipo_dados == 4: # payload é int
            payload = int.from_bytes(payload, byteorder='big')
        else: # payload é bytes
            pass 

        decodificado = {'tipo': tipo,
                        'info': info,
                        'size': tamanho_payload,
                        'payload': payload,
                        'crc_recebido': crc_recebido,
                        'crc_calculado': crc_calculado,
                        'total_size': len(pacote),
                        'packet_id': packet_id}
        return decodificado
    
