from config import *
from datetime import datetime, timedelta, timezone
import json
from flask import Flask, request, send_from_directory
import asyncio
import tempfile
import os
import threading
from gpiozero import LED, PWMOutputDevice

DIST_DIR = os.path.join(os.path.dirname(__file__), "Aquatimation/dist")
print(DIST_DIR)
# Connected pins are 23,24,25,26
# each used to control W, R,G,B unless relay controlled
#
''' Need to work this out. Problem when running on PC

class PinAssignment(PWMOutputDevice):
    duty = 0
    frequency = 0
    pinObj = None
    pin = None

    def __init__(self, pin=None):
        self.pin = pin
        super().__init__(pin = self.pin)

    def update_HW_(self):
        pass

    def set_duty(self,duty):
        self.duty = duty
        

    def set_frequency(self,frequency):
        self.frequency = frequency
        try:
            self.pinObj = PWMOutputDevice(pin=self.pin, frequency=self.frequency)
        except:
            print("attempted to set frequency. It failed")

    def get_duty(self):
        return self.duty

    def get_frequency(self):
        return self.frequency

'''

'''
Former method
if not IS_SIMULATED:
    R = PWMOutputDevice(pin=pin_R, frequency=1000 ) if pin(pin_R) is not None else None
    G = PWMOutputDevice(pin=pin_G, frequency=1000 ) if pin(pin_G) is not None else None
    B = PWMOutputDevice(pin=pin_B, frequency=1000 ) if pin(pin_B) is not None else None
    W = PWMOutputDevice(pin=pin_W, frequency=1000 ) if pin(pin_W) is not None else None

'''

class PinAssignment():

    pinObj = None
    pin = None

    frequency = 100
    duty = 0

    def __init__(self, pin):
        self.pin = pin
        try:
            self.pinObj = PWMOutputDevice(pin=self.pin)
        except:
            print("attempted to create pin object. It failed")


    def set_duty(self,duty):
        self.duty = duty
        try:
            self.pinObj.value = self.duty
        except:
            print("attempted to set Duty. It failed")


    def set_frequency(self,frequency):
        self.frequency = frequency
        try:
            self.pinObj.frequency = frequency
        except:
            print("attempted to set frequency. It failed")

    def get_duty(self):
        return self.duty

    def get_frequency(self):
        return self.frequency



global schedule
global state
global today
loop = None
IS_SIMULATED = False




today = datetime.now().strftime("%Y-%m-%d")
state = -1
state_changed = asyncio.Event()
update_schedule = asyncio.Event()


app = Flask(__name__, static_folder=DIST_DIR, static_url_path="/")


def pin(x):
    if x != '':
        return x
    else:
        return None


def write_schedule(key,value, st=None):
    global state
    global schedule
    fp = os.path.dirname("schedule.json")


    with open("schedule.json", "r") as f:
        schedule = json.load(f)

    with tempfile.NamedTemporaryFile("w",dir=fp, delete=False) as file:
        #print(schedule)
        if schedule:
            #print(schedule)
            print(state)
            schedule[key][state if st is None else st] = value
            json.dump(schedule, file,indent = 2)
            file.flush()
            os.fsync(file.fileno())

    os.replace(file.name,"schedule.json")


with open("schedule.json", "r") as f:
    global schedule
    schedule = json.load(f)



'''
Wants:
[X] load schedule
[X] get the current state
[X] set light state 

'''

async def color():
    global state
    global schedule
    R = PinAssignment(pin_R)
    G = PinAssignment(pin_G)
    B = PinAssignment(pin_B)
    W = PinAssignment(pin_W)
    print(f"update state {state}. Turning unit {schedule['enabled']}")

    while True:
        await state_changed.wait()
        state_changed.clear()

        assignment = schedule["rgbw"][state]
        R.set_duty(round(assignment[0]/255,2))
        G.set_duty(round(assignment[1]/255,2))
        B.set_duty(round(assignment[2]/255,2))
        W.set_duty(round(assignment[3]/255,2))

        print(f"Rpin: {R.get_duty()}\nGpin: {G.get_duty()}\nBpin: {B.get_duty()}\nWpin: {W.get_duty()}\n")

async def get_state():
    while True:
        global schedule
        global state
        global today
        current_state = state
        nextcheck = 3600
        # state initializes at -1. Find correct state and continue

        datetime_at_loop_start = datetime.now()
        datetime_at_loop_start = datetime_at_loop_start - timedelta(microseconds=datetime_at_loop_start.microsecond)
        if state == -1:
            if datetime_at_loop_start < datetime.strptime(f"{today} {schedule["interval"][0]}","%Y-%m-%d %H:%M:%S"):
                await asyncio.sleep((datetime.strptime(f"{today} {schedule["interval"][0]}","%Y-%m-%d %H:%M:%S")-datetime_at_loop_start).seconds)
                datetime_at_loop_start = datetime.now()
                # wait amount of time it takes to get to the first schedule
                # this will only happen once on init
            while datetime_at_loop_start > datetime.strptime(f"{today} {schedule["interval"][state+1]}","%Y-%m-%d %H:%M:%S"):
                state+=1
                if state == len(schedule["interval"])-1: # exit once we are at the end of the loop
                    break

        current_schedule_datetime = datetime.strptime(f"{today} {schedule["interval"][state]}", "%Y-%m-%d %H:%M:%S")

        if state == len(schedule["interval"])-1:
            print("last")
            # at the last schedule, we look for the delay until the next day first

            next_scheduled_day = datetime.strptime(today, "%Y-%m-%d") + timedelta(days=1)  # the next day

            # compare the time now to the time of the . We will come back once arrive

            next_scheduled_datetime = datetime.strptime(f"{next_scheduled_day.strftime("%Y-%m-%d")} {schedule["interval"][0]}","%Y-%m-%d %H:%M:%S") #  the next scheduled event

            if ( datetime_at_loop_start < next_scheduled_datetime):
                delta = next_scheduled_datetime-datetime_at_loop_start # we run into this if we havent gotten there yet
            else:
                state = 0 # we run into this if we are at or above the scheduled time. We set the state to 0 and update the global day variable
                today = next_scheduled_day # turn the stored day.
                delta = timedelta(seconds=0)

        else: # we are in [0 - len(n)-1)
            next_scheduled_datetime = datetime.strptime(f"{today} {schedule["interval"][state + 1]}","%Y-%m-%d %H:%M:%S")
            if datetime_at_loop_start > next_scheduled_datetime:
                state+=1
                delta = timedelta(seconds=0)
            else:

                delta  = next_scheduled_datetime - datetime_at_loop_start


        if current_state != state:
            today = datetime_at_loop_start.strftime("%Y-%m-%d")
            state_changed.set()
        print(f"Waiting for {delta.seconds+1} seconds")
        await asyncio.sleep(delta.seconds+1) # check every 5 minutes


def start_asyncio_thread():
    global loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    loop.create_task(get_state())
    loop.create_task(color())
    loop.run_forever()


@app.route("/",methods=['GET'])
async def index():
    return send_from_directory(app.static_folder,"index.html")

@app.route('/api',methods=['POST'])
async def update_RGB():
    global loop
    data = request.get_json()
    #print(data)
    output = [0,0,0,0]
    if 'r' in data and 'b' in data and 'g' in data and 'w' in data:
        output = [data['r'],data['g'],data['b'],data['w']]
        write_schedule("rgbw", output)
        loop.call_soon_threadsafe(state_changed.set)
    else:
        print("error: Invalid format")
    return {"status": "Good"}

@app.route("/api/state",methods=['GET'])
async def send_state():
    global schedule
    global state
    global loop
    return schedule | {"state": state}
@app.route("/<path:path>")
async def serve_spa(path):
    full_path = os.path.join(app.static_folder, path)

    # If file exists (assets/js/css), serve it; otherwise serve index.html (SPA routing)
    if os.path.isfile(full_path):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, "index.html")


if __name__ == '__main__':
    t = threading.Thread(target=start_asyncio_thread, daemon=False)
    t.start()
    app.run(host='0.0.0.0', port=80)