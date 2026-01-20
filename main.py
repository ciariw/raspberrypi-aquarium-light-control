from config import *
import asyncio
from datetime import datetime, timedelta, timezone
import json
from gpiozero import LED


# Connected pins are 23,24,25,26
# each used to control W, R,G,B unless relay controlled
#

global schedule
global state
state = -1
state_changed = asyncio.Event()

def pin(x):
    if x != '':
        return x
    else:
        return None


with open("schedule.json", "r") as f:
    global schedule
    schedule = json.load(f)



'''
Wants:
[ ] load schedule
[ ] get the current state
[ ] set light state 

'''

async def color():
    global state
    global schedule
    R = LED(pin_R) if pin(pin_R) is not None else None
    G = LED(pin_G) if pin(pin_G) is not None else None
    B = LED(pin_B) if pin(pin_B) is not None else None
    V = LED(pin_W) if pin(pin_W) is not None else None

   while True:
        await state_changed.wait()
        state_changed.clear()
        if schedule["set"][state] == "ON":
            print("Trigger ON")
            if R is not None:
                R.on()
        else:
            print("Trigger OFF")
            if R is not None:
                R.off()


async def get_state():
    while True:
        global schedule
        global state
        current_state = state
        for index,x in enumerate(schedule["interval"]):
            if datetime.now().time() > datetime.strptime(x,"%H:%M:%S").time():
                state = index
        if current_state != state:
            print("state changed")
            state_changed.set()
        await asyncio.sleep(300) # check every 5 minutes


async def main():
    t1 = asyncio.create_task(get_state())
    t2 = asyncio.create_task(color())
    await asyncio.gather(t1, t2)

if __name__ == '__main__':
    asyncio.run(main())
