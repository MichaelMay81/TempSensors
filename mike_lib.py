import utime  # utime == time ??
import machine


def get_mac_address():
    import network
    import ubinascii

    return ubinascii.hexlify(network.WLAN().config('mac'), ':').decode()


def set_time_by_ntp():
    import ntptime

    # set RealTimeClock with Network Time Protocol
    print("set RC with ntp")
    return ntptime.settime()


def sleep(sleep_for_sec):
    utime.sleep(sleep_for_sec)


def sleep_rtc(sleep_for_sec):
    # connect GPIO16 to reset
    # use 470R, 1K or shotkey diode with cathode to GPIO16 to avoid continuous reset
    rtc = machine.RTC()

    # configure ALARM0 to wake device
    rtc.irq(trigger=rtc.ALARM0, wake=machine.DEEPSLEEP)
    sleep_for_ms = sleep_for_sec * 1000
    rtc.alarm(rtc.ALARM0, sleep_for_ms)

    # go to sleep
    machine.deepsleep()


def query_sensor(pinSda, pinScl):
    import bme280

    i2c = machine.I2C(sda=machine.Pin(pinSda), scl=machine.Pin(pinScl))
    bme = bme280.BME280(i2c=i2c)
    raw = bme.read_compensated_data()
    print("query sensors: {}".format(bme.values))

    # Temperature: 1/100 Degree Celsius
    temp = raw[0] / 100
    # Pressure: 1/256 Pascal -> 1/100 hPa
    pres = raw[1] / 256 / 100
    # Humidity: 1/1024 % relative humidity
    humi = raw[2] / 1024

    return (temp, pres, humi)


def send_to_graphite(data):
    import socket

    ts_offset = 946684800  # 1970 to 2000
    timestamp = utime.time() + ts_offset
    print("time: {}".format(utime.localtime()))

    ip = "192.168.66.100"
    port = 2003
    sock = socket.socket()
    sock.connect((ip, port))

    send_errors = False
    for tup in data:
        db_name = tup[0]
        date = tup[1]
        data_string = "{}.metric {} {} \n".format(db_name, date, timestamp)
        #print(data_string)
        bytes_sent = sock.send(data_string)
        if bytes_sent == 0:
            send_errors = True

        if send_errors:
            print("!!Something went wrong while sending data to {}:{}".format(ip, port))
        else:
            print("Sent to {}:{}".format(ip, port))
    sock.close()


def _run_indoor():
    led = machine.Pin(16, machine.Pin.OUT)
    led.off()

    sensor = query_sensor(0, 2)
    temperature = sensor[0]  # Degree Celsius
    pressure    = sensor[1]  # hPa
    humidity    = sensor[2]  # relative humidity

    #room = "kids_room_"  # ws://192.168.66.54:8266/
    room = "bed_room_"  # b4:e6:2d:36:db:28 ws://192.168.66.45:8266/
    #room = "living_room_"  # b4:e6:2d:37:38:3e ws://192.168.66.34:8266/
    data = [
        (room + "temperature", temperature),
        (room + "pressure", pressure),
        (room + "humidity", humidity)
    ]
    send_to_graphite(data)

    led.on()


def run_outdoor():
    led = machine.Pin(16, machine.Pin.OUT)
    led.off()

    sensor1 = query_sensor(0, 2)
    temperature1 = sensor1[0]  # Degree Celsius
    pressure1    = sensor1[1]  # hPa
    humidity1    = sensor1[2]  # relative humidity

    sensor2 = query_sensor(4, 5)
    temperature2 = sensor2[0]  # Degree Celsius
    pressure2 = sensor2[1]  # hPa
    humidity2 = sensor2[2]  # relative humidity

    #room = "kids_room_"  # ws://192.168.66.54:8266/
    #room = "bed_room_"  # b4:e6:2d:36:db:28 ws://192.168.66.45:8266/
    #room = "living_room_"  # b4:e6:2d:37:38:3e ws://192.168.66.34:8266/
    #data = [
    #    (room + "temperature", temperature),
    #    (room + "pressure", pressure),
    #    (room + "humidity", humidity)
    #]
    #send_to_graphite(data)

    led.on()

def run_outdoor_loop():
    #every = 60 * 30  # every half hour
    every = 20

    while True:
        #set_time_by_ntp()
        now_ut = utime.time()
        sec_passed = now_ut % every
        sec_to_wait = every - sec_passed

        # RC is not very precise...
        if sec_to_wait < (every/2):
            sec_to_wait += every

        print("now: {}, wait for: {}".format(utime.localtime(now_ut), sec_to_wait))

        sleep(sec_to_wait)

        run_outdoor()

def run_test1():
    set_time_by_ntp()

    # Virtual (RTOS-based) timers with callback
    tim = machine.Timer(-1)
    sleep_for_ms = 10000
    tim.init(period=sleep_for_ms, mode=machine.Timer.PERIODIC, callback=lambda t: _run_indoor())


def run_test2():
    set_time_by_ntp()

    wait_for = 60 * 30  # every half hour

    while True:
        _run_indoor()
        sleep(wait_for)
