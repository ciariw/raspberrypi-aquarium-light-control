from config import *
import asyncio
from datetime import datetime, timedelta, timezone
import json
from gpiozero import LED, PWMOutputDevice


# Connected pins are 23,24,25,26
# each used to control W, R,G,B unless relay controlled
#

global schedule
global state
global today
today = datetime.now().strftime("%Y-%m-%d")
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

    print(f"update state {state}. Turning unit {schedule['set'][state]}")

    R = PWMOutputDevice(pin=pin_R, frequency=1000 ) if pin(pin_R) is not None else None
    G = PWMOutputDevice(pin=pin_G, frequency=1000 ) if pin(pin_G) is not None else None
    B = PWMOutputDevice(pin=pin_B, frequency=1000 ) if pin(pin_B) is not None else None
    W = PWMOutputDevice(pin=pin_W, frequency=1000 ) if pin(pin_W) is not None else None
    while True:
        await state_changed.wait()
        state_changed.clear()
        if schedule["set"][state] == "ON":
            print("Trigger ON")
            R.value= 0
            G.value= 0
            B.value= 1
            W.value= 1
                
        else:
            print("Trigger OFF")
            if R is not None:
                R.value=0
                G.value=0
                B.value=0
                W.value=0


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

        await asyncio.sleep(delta.seconds+1) # check every 5 minutes


async def main():
    t1 = asyncio.create_task(get_state())
    t2 = asyncio.create_task(color())
    await asyncio.gather(t1, t2)

if __name__ == '__main__':
    print("starting")
    asyncio.run(main())
