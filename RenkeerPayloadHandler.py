import time, json, random, requests
from os import system, name, path
from googletrans import Translator, constants

logDir          = "C:/%HOMEPATH%/Documents/docker-volume/tb-pyGateway/logs/RenkeerLogs"
translator      = Translator()
HostIP          = "Renkeer_Software_HostIP"
HostURL         = "http://"+HostIP+":9001"
TestAPI         = "/app/TestConnect"
LoginAPI        = "/app/Login"
GetDevGroupAPI  = "/app/GetUserDeviceGroups"
GetRealTimeData = "/app/GetDeviceData"
loginInfo       = {"loginName": "master", "password": "master"}
groups          = []

def Logging(dev):
    if path.exists(logDir):
        with open(logDir, "a") as logfile:
            logfile.write(",\n")
            json.dump(dev, logfile)
    else:
        with open(logDir, "x") as logfile:
            json.dump(dev, logfile)

def GTranslate(message, exclude=""):
    for key in message:
        if isinstance(message[key], str) == True:
            if key not in exclude:
                try:
                    valTrans = translator.translate(message[key], dest='en')
                    val = valTrans.text
                except:
                    pass

                if "\u2103" in val:
                    val = val.replace("(\u2103)", "")
                if " (%RH)" in val or "(%RH)" in val:
                    val = val.replace(" (%RH)", "")
                if "temperature" in val:
                    val = val.replace("temperature", "Temperature")

                message[key] = val
        elif isinstance(message[key], dict) == True:
            GTranslate(message[key], exclude)
            
        elif isinstance(message[key], list) == True:
            for i in message[key]: GTranslate(i, exclude)
            
    return message

def RequestRealTime(hostip=HostIP, loginauth=loginInfo, grouplist=groups):
    with requests.Session() as s:
        Devices  = {"Devices": []}
        HostURL = "http://"+hostip+":9001"
        userID   = ""
        groupIDs = []
        route    = 0
        while route<4:
            if route==0:
                try:
                    resp=s.get(url=HostURL+TestAPI, params={"id": str(route)})
                except:
                    print("Connection to Renkeer Software error...")
                    time.sleep(1)
                    print("Retrying...")
                    continue
                else:
                    message = resp.json()
                    route+=1
            elif route==1:
                resp=s.post(url=HostURL+LoginAPI, json=loginauth)
                message = resp.json()
                if message["message"] == "login successful" or message["message"] == "登录成功":
                    userID = message["data"]["userId"]
                    route+=1
            elif route==2:
                resp=s.get(url=HostURL+GetDevGroupAPI, headers={"userId": userID})
                message = resp.json()
                if message["message"] == "get success" or message["message"] == "获取成功":
                    for devGroup in message["data"]:
                        if devGroup["groupName"] in grouplist: groupIDs.append(devGroup["groupId"])
                    route+=1
            elif route==3:
                for gID in groupIDs:
                    resp=s.get(url=HostURL+GetRealTimeData, headers={"userId": userID}, params={"groupId": gID})
                    message = resp.json()
                    message = Parser(message)
                    Devices["Devices"].extend(message["Devices"])   
                break
            message = GTranslate(message, ["groupId", "parentId"])
            time.sleep(0.5)
            
        return Devices 

def Parser(message):
    Devices = {"Devices": []}
    try:
        message = json.loads(str(message))
    except:
        pass

    try:
        message = GTranslate(message)
    except:
        pass

    if message["message"] == "获取成功" or message["message"] == "get success":
        data = message["data"]
        for dev in data:
            if "realTimeData" in dev:
##                print("Real Time Data")
                Devices["Devices"].append(RealTimeData(dev))
            else:
##                print("Historical Data")
                Devices["Devices"].append(HistoricalData(dev))
##        Logging(Devices)
    else:
        pass
    return Devices

def RealTimeData(message):
    Device = {}
    data = {}
    message = GTranslate(message)
    Device["time"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    Device["ts"] = time.time()
    Device["devBrand"] = "Renkeer"
    Device["devName"] = message["deviceName"]
    Device["devEUI"] = message["deviceKey"]
    Device["xPos"] = message["lat"]
    Device["yPos"] = message["lng"]
    
    for i in range(len(message["realTimeData"])):
        message["realTimeData"][i] = GTranslate(message["realTimeData"][i])
    
    for d in message["realTimeData"]:
        data[d["dataName"]] = d["dataValue"]
##        data[d["dataName"]] = round(random.uniform(29.00, 35.99), 2)
        data[d["dataName"]+"Alarm"] = False
        if d["isAlarm"] != False:
            data[d["dataName"]+"Alarm"] = d["alarmMsg"]

    Device["data"] = data
        
    return Device

def HistoricalData(message):
    Device = {}
    message = GTranslate(message)
    Device["brand"] = "Renkeer"
    Device["time"] = message["RecordTime"]
    Device["ts"] = int(message["RecordTimeStamp"])/1000
    Device["devBrand"] = "Renkeer"
    Device["devName"] = message["DeviceName"]
    Device["devEUI"] = message["DeviceKey"]
    Device["xPos"] = message["Lat"]
    Device["yPos"] = message["Lng"]
    Device["data"] = {}
    Device["data"]["Temperature"] = message["Tem"]
    Device["data"]["Humidity"] = message["Hum"]
        
    return Device

if "__main__" == __name__:
    while True:
        func = input('function to test : ')
        if func == 'decoder':
            message = input("Enter message/telemetry string: ")
##            message = dataSample2
            message = Parser(message)
            print('\n', json.dumps(message, indent=2))
            
        elif func == 'encoder':
            pass

        elif func == 'realtime requests':
            HostIP = input("Enter HostIP: ")
            groups = '{"grouplist": ['+input("Enter strings of devices group name seperated by comma: ")+']}'
            groups = json.loads(groups)
            message = RequestRealTime(HostIP, groups["grouplist"])
            print('\n', json.dumps(message, indent=2))

        print('\n')
