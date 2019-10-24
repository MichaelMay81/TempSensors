import utime  # utime == time ??
import machine

from ucollections import namedtuple

Sensor = namedtuple('Sensor', ['id', 'pinSda', 'pinScl'])


def get_mac_address():
    import network
    import ubinascii

    return ubinascii.hexlify(network.WLAN().config('mac'), ':').decode()


def set_time_by_ntp():
    import mike_ntptime

    # set RealTimeClock with Network Time Protocol
    print("set RC with ntp")
    return mike_ntptime.settime("192.168.66.100")


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


def query_sensor(pin_sda, pin_scl):
    import bme280

    i2c = machine.I2C(sda=machine.Pin(pin_sda), scl=machine.Pin(pin_scl))
    try:
        bme = bme280.BME280(i2c=i2c)
    except OSError:
        print("ERROR: couldn't query sensor ({}/{})".format(pin_sda, pin_scl))
        return None

    raw = bme.read_compensated_data()
    print("query sensors: {}".format(bme.values))

    # Temperature: 1/100 Degree Celsius
    temp = raw[0] / 100
    # Pressure: 1/256 Pascal -> 1/100 hPa
    pres = raw[1] / 256 / 100
    # Humidity: 1/1024 % relative humidity
    humi = raw[2] / 1024

    return temp, pres, humi


def query_onewire_sensor(pin_dat):
    import onewire, ds18x20

    dat = machine.Pin(pin_dat)
    sensor = ds18x20.DS18X20(onewire.OneWire(dat))

    # scan for devices on the bus
    roms = sensor.scan()
    print('found devices:', roms)

    # loop 10 times and print all temperatures
    for i in range(10):
        print('temperatures:', end=' ')
        sensor.convert_temp()
        utime.sleep_ms(750)
        for rom in roms:
            print(sensor.read_temp(rom), end=' ')
        print()


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


def _run(sensors, send=True):
    led = machine.Pin(16, machine.Pin.OUT)
    led.off()

    raw_data = [(s.id, query_sensor(s.pinSda, s.pinScl)) for s in sensors]

    data = [
        ((d[0] + "temperature", d[1][0]),  # Degree Celsius
         (d[0] + "pressure", d[1][1]),  # hPa
         (d[0] + "humidity", d[1][2]))  # relative humidity
        for d in raw_data
    ]

    if send:
        for d in data:
            if d is not None:
                send_to_graphite(d)

    led.on()


def _run_loop(sensors, every):
    # repeat until we get a valid time
    while True:
        try:
            set_time_by_ntp()
        except OSError:
            print("ERROR: couldn't set time by ntp")
            sleep(5)
        else:
            break

    _run(sensors, False)

    while True:
        now_ut = utime.time()
        sec_passed = now_ut % every
        sec_to_wait = every - sec_passed

        # RC is not very precise...
        # if sec_to_wait < (every/2):
        #    sec_to_wait += every

        print("now: {}, wait for: {}".format(utime.localtime(now_ut), sec_to_wait))

        sleep(sec_to_wait)

        try:
            _run(sensors)
        except OSError:
            print("ERROR: couldn't query sensor")

        # update time
        try:
            set_time_by_ntp()
        except OSError:
            print("ERROR: couldn't set time by ntp")


def run_loop(room_id: str = None):
    every = 60 * 10  # every half hour
    # every = 20

    # :( broken:
    # b4:e6:2d:37:38:3e ws://192.168.66.101:8266/
    rooms = {
        "kids_room": [Sensor("", 0, 2)],  # ws://192.168.66.103:8266/
        "bed_room": [Sensor("", 0, 2)],
        "living_room": [Sensor("", 0, 2)],
        "outdoor": [    # b4:e6:2d:36:db:28 ws://192.168.66.102:8266/
            Sensor("sensor1_", 0, 2),
            Sensor("sensor2_", 4, 5)
        ]}

    if room_id is None or room_id not in rooms:
        print("usage: run_loop(id)")
        print("ids:")
        for room in rooms:
            print("- \"{}\"".format(room))

    else:
        room = rooms[room_id]
        sensors = [Sensor(room_id + '_' + s.id, s.pinSda, s.pinScl) for s in room]

        print("Starting loop for {} every {}".format(room_id, every))
        _run_loop(sensors, every)


# def run_test1():
#    set_time_by_ntp()

    # Virtual (RTOS-based) timers with callback
#    tim = machine.Timer(-1)
#    sleep_for_ms = 10000
#    tim.init(period=sleep_for_ms, mode=machine.Timer.PERIODIC, callback=lambda t: _run_indoor())
