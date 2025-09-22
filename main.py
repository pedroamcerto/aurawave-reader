"""
AuraWave NFC Reader - Versão Simplificada
ESP32 MicroPython com WiFiManager otimizado para memória baixa
"""

import time
import gc
import network
import socket
from machine import Pin, SoftSPI, reset, unique_id
import ubinascii

try:
    import ujson
except:
    import json as ujson

# Hardware
led = Pin(33, Pin.OUT)
spi = SoftSPI(baudrate=100000, polarity=0, phase=0, 
              sck=Pin(26), mosi=Pin(25), miso=Pin(12))
cs = Pin(27, Pin.OUT)

# WiFi
station = network.WLAN(network.STA_IF)
ap = network.WLAN(network.AP_IF)

# Config global
config = {}
mqtt_client = None

# Importar MQTT
try:
    from umqttsimple import MQTTClient
    MQTT_AVAILABLE = True
except:
    MQTT_AVAILABLE = False
    print("MQTT não disponível")

def blink_led(times=3, delay=0.2):
    """Pisca LED"""
    for _ in range(times):
        led.value(1)
        time.sleep(delay)
        led.value(0)
        time.sleep(delay)

def load_config():
    """Carrega configurações"""
    global config
    try:
        with open('config.json', 'r') as f:
            config = ujson.load(f)
    except:
        config = {
            "mqtt": {
                "broker": "",
                "port": 1883,
                "topic": "aurawave/events",
                "username": "",
                "password": ""
            }
        }

def save_config():
    """Salva configurações"""
    try:
        with open('config.json', 'w') as f:
            ujson.dump(config, f)
        return True
    except:
        return False

def connect_mqtt():
    """Conecta ao MQTT"""
    global mqtt_client
    
    if not MQTT_AVAILABLE or not config.get("mqtt", {}).get("broker"):
        return False
    
    try:
        broker = config["mqtt"]["broker"]
        port = config["mqtt"].get("port", 1883)
        username = config["mqtt"].get("username", "")
        password = config["mqtt"].get("password", "")
        
        client_id = ubinascii.hexlify(unique_id()).decode()
        
        if username and password:
            mqtt_client = MQTTClient(client_id, broker, port=port, user=username, password=password)
        else:
            mqtt_client = MQTTClient(client_id, broker, port=port)
        
        mqtt_client.connect()
        print(f"MQTT conectado: {broker}:{port}")
        return True
    except Exception as e:
        print(f"Erro MQTT: {e}")
        mqtt_client = None
        return False

def send_mqtt_data(uid):
    """Envia dados via MQTT"""
    if not mqtt_client:
        return False
    
    try:
        topic = config.get("mqtt", {}).get("topic", "aurawave/events")
        message = {"eventType": "item", "log": uid}
        payload = ujson.dumps(message)
        
        mqtt_client.publish(topic, payload)
        print(f"MQTT enviado: {payload}")
        return True
    except Exception as e:
        print(f"Erro envio MQTT: {e}")
        return False

def save_wifi(ssid, password):
    """Salva WiFi"""
    try:
        with open('wifi.dat', 'w') as f:
            f.write(f"{ssid};{password}")
        return True
    except:
        return False

def load_wifi():
    """Carrega WiFi salvo"""
    try:
        with open('wifi.dat', 'r') as f:
            line = f.read().strip()
            if ';' in line:
                return line.split(';', 1)
    except:
        pass
    return None, None

def connect_wifi():
    """Conecta ao WiFi"""
    ssid, password = load_wifi()
    if not ssid:
        return False
    
    station.active(True)
    station.connect(ssid, password)
    
    for _ in range(15):
        if station.isconnected():
            print(f"WiFi OK: {station.ifconfig()[0]}")
            return True
        time.sleep(1)
    
    return False

def wifi_manager():
    """WiFiManager simplificado"""
    print("Iniciando WiFiManager...")
    
    # Criar AP
    ap.active(True)
    chip_id = ubinascii.hexlify(unique_id())[-4:].decode().upper()
    ap_name = f"AuraWave-{chip_id}"
    ap.config(essid=ap_name, password="12345678")
    
    print(f"AP: {ap_name} | Senha: 12345678")
    print("Acesse: http://192.168.4.1")
    
    # Servidor simples
    server = socket.socket()
    server.bind(('0.0.0.0', 80))
    server.listen(1)
    
    while True:
        if station.isconnected():
            ap.active(False)
            return True
        
        try:
            client, addr = server.accept()
            request = client.recv(1024).decode()
            
            if "GET /" in request:
                # Página de configuração
                station.active(True)
                networks = [ssid.decode() for ssid, *_ in station.scan()]
                
                html = f"""HTTP/1.1 200 OK
Content-Type: text/html

<!DOCTYPE html>
<html><head>
<title>AuraWave Setup</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body{{font-family:Arial;padding:20px;background:#f5f5f5}}
.container{{max-width:500px;margin:0 auto;background:white;padding:30px;border-radius:10px;box-shadow:0 2px 10px rgba(0,0,0,0.1)}}
h2{{color:#2c5aa0;text-align:center;margin-bottom:30px}}
h3{{color:#333;border-bottom:2px solid #2c5aa0;padding-bottom:5px}}
input,select{{width:100%;padding:12px;margin:8px 0;border:1px solid #ddd;border-radius:5px;box-sizing:border-box}}
button{{width:100%;padding:15px;background:#2c5aa0;color:white;border:none;border-radius:5px;cursor:pointer;font-size:16px}}
button:hover{{background:#1e4080}}
.network{{margin:8px 0;padding:12px;border:1px solid #ddd;border-radius:5px;background:#f9f9f9}}
.mqtt-info{{background:#e7f3ff;padding:15px;border-radius:5px;margin:15px 0;font-size:14px}}
</style>
</head>
<body>
<div class="container">
<h2>🌊 AuraWave Setup</h2>
<form method="post">

<h3>📶 Configuração WiFi</h3>"""
                
                for net in networks[:8]:  # Limitar para economizar memória
                    html += f'<div class="network"><input type="radio" name="ssid" value="{net}" required> {net}</div>'
                
                mqtt_broker = config.get("mqtt", {}).get("broker", "")
                mqtt_port = config.get("mqtt", {}).get("port", 1883)
                mqtt_topic = config.get("mqtt", {}).get("topic", "aurawave/events")
                mqtt_user = config.get("mqtt", {}).get("username", "")
                mqtt_pass = config.get("mqtt", {}).get("password", "")
                
                html += f"""
<input name="password" type="password" placeholder="Senha WiFi" required>

<h3>📡 Configuração MQTT</h3>
<input name="mqtt_broker" placeholder="Broker MQTT (ex: mqtt.broker.com)" value="{mqtt_broker}">
<input name="mqtt_port" type="number" placeholder="Porta" value="{mqtt_port}">
<input name="mqtt_topic" placeholder="Tópico" value="{mqtt_topic}">
<input name="mqtt_user" placeholder="Usuário (opcional)" value="{mqtt_user}">
<input name="mqtt_pass" type="password" placeholder="Senha (opcional)" value="{mqtt_pass}">

<div class="mqtt-info">
<strong>ℹ️ Formato da mensagem MQTT:</strong><br>
<code>{{"eventType": "item", "log": "ID_da_tag"}}</code>
</div>

<button type="submit">💾 Salvar e Conectar</button>
</form>
</div>
</body></html>"""
                
                client.send(html.encode())
            
            elif "POST /" in request:
                # Processar configuração
                try:
                    body = request.split('\r\n\r\n')[1]
                    data = {}
                    for pair in body.split('&'):
                        if '=' in pair:
                            key, value = pair.split('=', 1)
                            data[key] = value.replace('+', ' ').replace('%40', '@').replace('%3A', ':')
                    
                    ssid = data.get('ssid', '')
                    password = data.get('password', '')
                    
                    # Salvar configurações MQTT
                    if data.get('mqtt_broker'):
                        config["mqtt"]["broker"] = data.get('mqtt_broker', '')
                        config["mqtt"]["port"] = int(data.get('mqtt_port', 1883))
                        config["mqtt"]["topic"] = data.get('mqtt_topic', 'aurawave/events')
                        config["mqtt"]["username"] = data.get('mqtt_user', '')
                        config["mqtt"]["password"] = data.get('mqtt_pass', '')
                        save_config()
                    
                    if ssid and password:
                        # Tentar conectar
                        station.connect(ssid, password)
                        
                        connected = False
                        for _ in range(15):
                            if station.isconnected():
                                connected = True
                                break
                            time.sleep(1)
                        
                        if connected:
                            save_wifi(ssid, password)
                            ip = station.ifconfig()[0]
                            
                            response = f"""HTTP/1.1 200 OK
Content-Type: text/html

<html><body style="text-align:center;padding:50px;font-family:Arial">
<h1>✅ Conectado!</h1>
<p><strong>SSID:</strong> {ssid}</p>
<p><strong>IP:</strong> {ip}</p>
<p><strong>MQTT:</strong> {config['mqtt']['broker'] or 'Não configurado'}</p>
<div style="margin:20px;padding:15px;background:#e7f3ff;border-radius:5px">
<p>Sistema reiniciando...</p>
<p>Aguarde aproximadamente 10 segundos</p>
</div>
</body></html>"""
                            client.send(response.encode())
                            client.close()
                            time.sleep(2)
                            reset()
                        else:
                            client.send(b"HTTP/1.1 200 OK\r\n\r\n<h1>Erro: Falha na conexao</h1>")
                    else:
                        client.send(b"HTTP/1.1 200 OK\r\n\r\n<h1>Erro: Dados invalidos</h1>")
                except Exception as e:
                    client.send(f"HTTP/1.1 500 OK\r\n\r\n<h1>Erro: {e}</h1>".encode())
                    client.send(b"HTTP/1.1 500 OK\r\n\r\n<h1>Erro interno</h1>")
            
            client.close()
        except:
            pass

class MFRC522:
    """Driver MFRC522 mínimo"""
    OK, ERR = 0, 2
    REQIDL = 0x26
    AUTHENT1A = 0x60

    def __init__(self, spi, cs):
        self.spi = spi
        self.cs = cs
        self.cs.value(1)
        self.init()

    def _wreg(self, reg, val):
        self.cs.value(0)
        self.spi.write(bytes([((reg << 1) & 0x7e), val]))
        self.cs.value(1)

    def _rreg(self, reg):
        self.cs.value(0)
        self.spi.write(bytes([((reg << 1) & 0x7e) | 0x80]))
        val = self.spi.read(1)[0]
        self.cs.value(1)
        return val

    def _tocard(self, cmd, send):
        recv = []
        # Implementação simplificada para economizar memória
        self._wreg(0x01, 0x00)
        for c in send:
            self._wreg(0x09, c)
        self._wreg(0x01, cmd)
        
        # Aguardar resposta
        for _ in range(1000):
            n = self._rreg(0x04)
            if n & 0x01:
                break
        
        if self._rreg(0x06) & 0x1B == 0x00:
            return self.OK, recv
        return self.ERR, recv

    def init(self):
        self._wreg(0x01, 0x0F)  # Reset
        time.sleep(0.1)
        self._wreg(0x2A, 0x8D)
        self._wreg(0x2B, 0x3E)
        self._wreg(0x15, 0x40)
        self._wreg(0x11, 0x3D)

    def request(self, mode):
        self._wreg(0x0D, 0x07)
        stat, recv = self._tocard(0x0C, [mode])
        return stat

    def anticoll(self):
        stat, recv = self._tocard(0x0C, [0x93, 0x20])
        return stat, recv[:4] if stat == self.OK and len(recv) >= 4 else []

def read_nfc():
    """Lê NFC simplificado"""
    try:
        if rdr.request(rdr.REQIDL) == rdr.OK:
            stat, uid = rdr.anticoll()
            if stat == rdr.OK and len(uid) >= 4:
                uid_str = "".join([f"{b:02x}" for b in uid])
                return uid_str
    except:
        pass
    return None

def main():
    """Função principal otimizada"""
    global rdr
    
    print("=== AURAWAVE READER ===")
    
    # Limpar memória
    gc.collect()
    
    # Carregar config
    load_config()
    
    # Mostrar configurações
    print(f"MQTT: {config.get('mqtt', {}).get('broker', 'Não configurado')}")
    print(f"Tópico: {config.get('mqtt', {}).get('topic', 'aurawave/events')}")
    
    # Inicializar NFC
    rdr = MFRC522(spi, cs)
    
    # Boot LED
    blink_led(2)
    
    # Conectar WiFi
    if not connect_wifi():
        print("Sem WiFi - iniciando WiFiManager")
        if not wifi_manager():
            print("Falha no WiFiManager")
            return
    
    # Conectar MQTT
    if connect_mqtt():
        print("MQTT conectado!")
    else:
        print("MQTT não configurado ou falha na conexão")
    
    print("Sistema pronto!")
    
    # Loop principal
    last_uid = ""
    count = 0
    
    while True:
        try:
            uid = read_nfc()
            
            if uid and uid != last_uid:
                led.value(1)
                last_uid = uid
                count += 1
                
                print(f"[{count}] Tag: {uid}")
                
                # Enviar dados via MQTT
                if send_mqtt_data(uid):
                    print("✅ Enviado via MQTT")
                    blink_led(3, 0.1)  # LED sucesso
                else:
                    print("⚠️ Falha no envio")
                    blink_led(2, 0.3)  # LED aviso
                
                time.sleep(1)
                
            elif not uid and last_uid:
                last_uid = ""
                print("Tag removida")
            
            # Verificar mensagens MQTT se conectado
            if mqtt_client:
                try:
                    mqtt_client.check_msg()
                except:
                    pass
                
            led.value(0)
            time.sleep(0.2)
            
            # Limpeza de memória
            if count % 5 == 0:
                gc.collect()
                
        except KeyboardInterrupt:
            print("\nParando...")
            break
        except Exception as e:
            print(f"Erro: {e}")
            time.sleep(1)
    
    led.value(0)

if __name__ == "__main__":
    main()