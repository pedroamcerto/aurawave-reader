"""
AuraWave Reader - Boot
Sistema de inicialização com WiFi e MQTT básico
"""

import time
try:
    from umqttsimple import MQTTClient
except:
    print("MQTT library not found")
    MQTTClient = None
import ubinascii
import machine
import network

import gc
gc.collect()

# Configurações WiFi - serão substituídas pelo WiFiManager se necessário
ssid = ''
password = ''
mqtt_server = ''
mqtt_user = ''
mqtt_pass = ''

# Configurações MQTT
client_id = ubinascii.hexlify(machine.unique_id())
topic_sub = b'aurawave/commands'
topic_pub = b'aurawave/events'

station = network.WLAN(network.STA_IF)

def load_wifi_config():
    """Carrega configuração WiFi salva"""
    global ssid, password
    try:
        with open('wifi.dat', 'r') as f:
            lines = f.readlines()
        for line in lines:
            if ';' in line:
                saved_ssid, saved_password = line.strip().split(';', 1)
                ssid = saved_ssid
                password = saved_password
                break
        return True
    except:
        return False

def load_mqtt_config():
    """Carrega configuração MQTT"""
    global mqtt_server, mqtt_user, mqtt_pass
    try:
        import ujson
        with open('aura_config.json', 'r') as f:
            config = ujson.load(f)
        mqtt_config = config.get('mqtt', {})
        mqtt_server = mqtt_config.get('broker', '')
        mqtt_user = mqtt_config.get('username', '')
        mqtt_pass = mqtt_config.get('password', '')
        return bool(mqtt_server)
    except:
        return False

def connect_wifi():
    """Conecta ao WiFi se configurado"""
    if not ssid or not password:
        return False
    
    station.active(True)
    station.connect(ssid, password)
    
    timeout = 15
    while not station.isconnected() and timeout > 0:
        time.sleep(1)
        timeout -= 1
        print('.', end='')
    
    if station.isconnected():
        print(f'\nWiFi conectado! IP: {station.ifconfig()[0]}')
        return True
    else:
        print('\nFalha na conexão WiFi')
        return False

def boot():
    """Processo de boot"""
    print("=== AURAWAVE READER BOOT ===")
    
    # Tentar carregar e conectar WiFi
    if load_wifi_config() and connect_wifi():
        print("Boot WiFi concluído")
        # Carregar config MQTT se disponível
        load_mqtt_config()
    else:
        print("WiFi não configurado - será usado WiFiManager")
    
    gc.collect()
    print("Boot finalizado")

# Executar boot
boot()