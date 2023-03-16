import time, json
from cayennelpp import LppFrame,LppUtil
from os import system, name, path

lppTemplate = [("digital", 1, "Automation"),
               ("digital", 22, "Relay1"),
               ("digital", 23, "Relay2"),
               ("digital", 24, "Relay3"),
               ("digital", 25, "Relay4"),
               ("analog", 6, "pumpPeriod"),
               ("analog", 7, "fertPeriod"),
               ("analog", 51, "AmbientHumidity"),
               ("analog", 52, "AmbientTemperature"),
               ("analog", 53, "InternalHumidity"),
               ("analog", 54, "InternalTemperature"),
               ("analog", 55, "WaterTDS"),
               ("analog", 56, "WaterEC"),
               ("analog", 57, "WaterpH"),
               ("digital", 58, "WaterLevel"),
               ("analog", 59, "Voltage"),
               ("analog", 60, "PowermWh"),
               ("analog", 61, "PowerWh"),
               ("analog", 62, "PowerkWh")]

lppThreshold = {"pumpPeriod": 0, "fertPeriod": 0, "HumMin": 0, "TempMax": 0, "TDSMax": 0, "TDSMin": 0, "ECMax": 0, "ECMin": 0, "pHMax": 0, "pHMin": 0}

DHToffset = {"AHMinIn": 0, "AHMaxIn": 0, "AHMinOut": 0, "AHMaxOut": 0, "IHMinIn": 0, "IHMaxIn": 0, "IHMinOut": 0, "IHMaxOut": 0}
chanOffset = 100
logDir = "C:/Users/MAE/Documents/rpi400/LppDevLog"

## Thus, if your EC is 1: 1 * 1000/2= 500 ppm
## And if your ppm is 500: 500 * 2/1000= 1 mS/cm

def mapValue(x, in_min, in_max, out_min, out_max):
  return (x - in_min) * (out_max - out_min) // (in_max - in_min) + out_min

def Logging(dev):
    if path.exists(logDir):
        with open(logDir, "a") as logfile:
            logfile.write(",\n")
            json.dump(dev, logfile)
    else:
        with open(logDir, "w") as logfile:
            json.dump(dev, logfile)

def timeSync():
    buffer = "T"+str(int(time.time()))
    return bytes(buffer.encode('utf-8'))

def Calibration(data, DHToffset):
    if "AmbientHumidity" in data:
        data["AmbientHumidity"] = mapValue(data["AmbientHumidity"], DHToffset["AHMinIn"], DHToffset["AHMaxIn"], DHToffset["AHMinOut"], DHToffset["AHMaxOut"])
    if "InternalHumidity" in data:
        data["InternalHumidity"] = mapValue(data["InternalHumidity"], DHToffset["IHMinIn"], DHToffset["IHMaxIn"], DHToffset["IHMinOut"], DHToffset["IHMaxOut"])
    if "WaterTDS" in data:
        data["WaterEC"] = round(data["WaterTDS"]*1.12, 2)
    return data

def decoder(buffer):
    data = {}
    try:
        uplink = LppFrame().from_bytes(buffer)
        uplink = json.dumps(uplink, default=LppUtil.json_encode_type_str)
        uplink = json.loads(uplink)
        for temp in lppTemplate:
            for d in uplink:
                if d["channel"] == temp[1]:
                    data[temp[2]] = d["value"][0]
        return Calibration(data, DHToffset)
    except:
        print('\n', "invalid bytes string...")

def encoder(downlink):
    buffer = LppFrame()
    buffer.reset()
    for temp in lppTemplate:
        if temp[2] in downlink:
            if temp[0] == "digital":
                buffer.add_digital_output(temp[1]+chanOffset,int(downlink[temp[2]]))
            elif temp[0] == "analog":
                buffer.add_analog_output(temp[1]+chanOffset,int(downlink[temp[2]]))
    return b''.join([bytes("D".encode('utf-8')),bytes(buffer)])

def Parser(message):
    Device = {}
    Device["time"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    Device["ts"] = time.time()
    Device["devName"] = "LppDevice"
    Device["data"] = decoder(message)
    Logging(Device)
    return Device

def Automation(threshold, lppData):
    cmd = {}
    if "AmbientHumidity" in lppData and lppData["AmbientHumidity"] <= threshold["HumMin"]:
        cmd["pumpPeriod"] = threshold["pumpPeriod"]
    elif "InternalHumidity" in lppData and lppData["InternalHumidity"] <= threshold["HumMin"]:
        cmd["pumpPeriod"] = threshold["pumpPeriod"]
    elif "AmbientTemperature" in lppData and lppData["AmbientTemperature"] >= threshold["TempMax"]:
        cmd["pumpPeriod"] = threshold["pumpPeriod"]
    elif "InternalTemperature" in lppData and lppData["InternalTemperature"] >= threshold["TempMax"]:
        cmd["pumpPeriod"] = threshold["pumpPeriod"]

    if "WaterTDS" in lppData or "WaterEC" in lppData:
      if lppData["WaterTDS"] < threshold["TDSMin"] or lppData["WaterEC"] < threshold["ECMin"]:
          cmd["fertPeriod"] = threshold["fertPeriod"]
          cmd["pumpPeriod"] = threshold["pumpPeriod"]
    return cmd
    
if "__main__" == __name__:
    while True:
        func = input('function to test : ')
        if func == 'decoder':
            message = input("Enter bytes buffer string: ")
            message = Parser(message.encode('latin-1'))
            print('\n', json.dumps(message, indent=2))
            
        elif func == 'encoder':
            message = input('Enter Json string of specific keys :')
            buffer = json.loads(str(message))
            buffer = encoder(buffer)
            print(buffer.decode('latin-1'))

        elif func == 'timesync':
            buffer = timeSync()
##            print(buffer.decode('latin-1'))

        print('\n')
