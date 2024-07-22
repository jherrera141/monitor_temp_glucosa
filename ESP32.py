from machine import Pin, I2C, PWM
from utime import sleep, sleep_ms, ticks_ms, ticks_diff
import network, time
import ujson
from neopixel import NeoPixel
from dht import DHT22
from umqtt.simple import MQTTClient
from ssd1306 import SSD1306_I2C  # pantalla

# Configuración del ancho y alto de la pantalla OLED
ancho = 128
alto = 64

# Configuración de los pines I2C (asegúrate de que son los correctos)
i2c = I2C(0, scl=Pin(22), sda=Pin(21))

# Inicializar la pantalla OLED
oled = SSD1306_I2C(ancho, alto, i2c)

# Crear los objetos
np = NeoPixel(Pin(14), 1)  # Neopixel (led)
buzzer = PWM(Pin(26))  # Buzzer
buzzer.duty(0)  # Asegurarse de que el buzzer está apagado inicialmente
sen_temp = DHT22(Pin(12))  # Sensor de temperatura y humedad DHT22
Ventilador = Pin(4, Pin.OUT)
Ventilador.value(0)

# Configuración del pin D4 para controlar la fuente ATX
pin_atx_control = Pin(2, Pin.OUT)
pin_atx_control.value(1)  # Asegurarse de que la fuente ATX está apagada inicialmente (PS_ON a alto)

# Función para sonar el buzzer durante un corto periodo con pitidos constantes
def sonar_buzzer(frecuencia, duracion_on, duracion_off, repeticiones):
    for _ in range(repeticiones):
        buzzer.freq(frecuencia)
        buzzer.duty(512)  # La mitad del rango (0-1023) para generar sonido
        sleep_ms(duracion_on)  # Duración del pitido
        buzzer.duty(0)  # Apagar el buzzer
        sleep_ms(duracion_off)  # Pausa breve entre pitidos

#__________________función para mostrar datos en pantalla__________________
def mostrar_en_pantalla(temperatura, humedad):
    oled.fill(0)  # Limpia la pantalla
    oled.text("Temp: {:.1f} C".format(temperatura), 0, 10, 1)
    oled.text("Hum: {:.1f} %".format(humedad), 0, 20, 1)
    
    if temperatura > 7:
        oled.text("Fuera de lim sup", 0, 30, 1)
        Ventilador.value(1)
        if pin_atx_control.value() != 0:
            pin_atx_control.value(0)  # Encender la fuente ATX (PS_ON a bajo)
            print("Fuente ATX encendida, Temperatura:", temperatura)
        sonar_buzzer(440, 50, 50, 4)
    elif temperatura < 3:
        oled.text("Fuera de lim inf", 0, 30, 1)
        Ventilador.value(0)
        if pin_atx_control.value() != 1:
            pin_atx_control.value(1)  # Apagar la fuente ATX (PS_ON a alto)
            print("Fuente ATX apagada, Temperatura:", temperatura)
        sonar_buzzer(440, 50, 50, 4)
    elif 3 <= temperatura <= 7:
        oled.text("Temp. ok", 0, 30, 1)
        Ventilador.value(0)
        print("Temperatura en rango normal:", temperatura)
    
    if humedad > 70:
        oled.text("Hum. alta", 0, 40, 1)
        sonar_buzzer(440, 50, 50, 4)
    elif humedad < 30:
        oled.text("Hum. baja", 0, 40, 1)
        sonar_buzzer(440, 50, 50, 4)
    else:
        oled.text("Hum. ok", 0, 40, 1)

    oled.show()  # Actualiza la pantalla para mostrar los cambios

# Función para conectar a WiFi
def conectaWifi(red, password):
    global miRed
    miRed = network.WLAN(network.STA_IF)
    if not miRed.isconnected():  # Si no está conectado...
        miRed.active(True)  # Activa la interface
        miRed.connect(red, password)  # Intenta conectar con la red
        print('Conectando a la red', red + "...")
        timeout = time.time()
        while not miRed.isconnected():  # Mientras no se conecte...
            if (time.time() - timeout) > 10:
                return False
    return True

# Conexión MQTT
MQTT_CLIENT_ID = "clientId-xrzO9FbtME"
MQTT_BROKER = "broker.hivemq.com"
MQTT_USER = ""  # solo de ser necesario
MQTT_PASSWORD = ""  # solo de ser necesario
MQTT_TOPIC = "Diplomado/LabSolutions/Proyectofinal12"

np[0] = (18, 250, 3)
np.write()

if conectaWifi("SMART_WIFI850", "SMART850"):
    print("Conexión exitosa!")
    print('Datos de la red (IP/netmask/gw/DNS):', miRed.ifconfig())
    print("Conectando a MQTT server... ", "...", end="")
    np[0] = (0, 0, 250)
    np.write()
    client = MQTTClient(MQTT_CLIENT_ID, MQTT_BROKER, user=MQTT_USER, password=MQTT_PASSWORD)
    try:
        client.connect()
        print("Connected!")
    except Exception as e:
        print("Failed to connect to MQTT server:", e)
else:
    print("Imposible conectar")
    miRed.active(False)

while True:
    sleep_ms(30000)  # Espera de 30 segundos entre lecturas
    try:
        sen_temp.measure()
        tem = sen_temp.temperature()
        hum = sen_temp.humidity()
        message = ujson.dumps({
            "Humedad": hum,
            "Temperatura": tem,
        })

        print("Reportando a MQTT topic {}: {}".format(MQTT_TOPIC, message))
        client.publish(MQTT_TOPIC, message)

        # Mostrar los datos y mensajes en la pantalla OLED
        mostrar_en_pantalla(tem, hum)
    except OSError as e:
        print("Error al medir la temperatura/humedad:", e)
        oled.fill(0)
        oled.text("Error en sensor", 0, 30, 1)
        oled.show()
