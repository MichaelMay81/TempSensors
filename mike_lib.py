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


def query_sensor():
    import bme280

    i2c = machine.I2C(sda=machine.Pin(0), scl=machine.Pin(2))
    bme = bme280.BME280(i2c=i2c)
    print("query sensors: {}".format(bme.values))
    return bme.read_compensated_data()


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


def _run_test():
    led = machine.Pin(16, machine.Pin.OUT)
    led.off()

    sensor = query_sensor()
    # Temperature: 1/100 Degree Celsius
    temp = sensor[0] / 100
    # Pressure: 1/256 Pascal -> 1/100 hPa
    pres = sensor[1] / 256 / 100
    # Humidity: 1/1024 % relative humidity
    humi = sensor[2] / 1024

    #room = "kids_room_"  # ws://192.168.66.54:8266/
    room = "bed_room_"  # b4:e6:2d:36:db:28 ws://192.168.66.45:8266/
    #room = "living_room_"  # b4:e6:2d:37:38:3e ws://192.168.66.34:8266/
    data = [
        (room + "temperature", temp),
        (room + "pressure", pres),
        (room + "humidity", humi)
    ]
    send_to_graphite(data)

    led.on()


def run_test1():
    set_time_by_ntp()

    # Virtual (RTOS-based) timers with callback
    tim = machine.Timer(-1)
    sleep_for_ms = 10000
    tim.init(period=sleep_for_ms, mode=machine.Timer.PERIODIC, callback=lambda t: _run_test())


def run_test2():
    set_time_by_ntp()

    wait_for = 60 * 30  # every half hour

    while True:
        _run_test()
        sleep(wait_for)
