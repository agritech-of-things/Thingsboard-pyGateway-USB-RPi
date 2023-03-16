import time, json, requests, psutil, subprocess, serial, os
import MSPayloadHandler as mspl
import ArduinoCLppHandler as aclpp
import RenkeerPayloadHandler as rkpl
from os import system, name, path
from tb_gateway_mqtt import TBGatewayMqttClient
from serial.tools import list_ports

gtwyName      = ""
HOSTNAME      = ""
tbHOSTNAME    = ""
GATEWAY_TOKEN = ""
interval      = 900
rebootTime    = 1200
msEnabled     = False
rkEnabled     = False
lppEnabled    = False

# local variables
rpiHomeDir = "/home/pi"
winUserDir = ""
rootDir = rpiHomeDir+"/tb-pyGateway"
logDir = rootDir+"/logs"
configFile = rootDir+"/configuration"
cmd_attr = {"client": {"devEUI": "24e124414b101174", "fPort": "85"}, "shared": {"valve": "1", "act": "open", "dur": 0, "counter": 0}}
Run = True
        
# MileSight Variables
Devices = []
msurl_uplink = "http://"+HOSTNAME+":5999/api/msiot/uplink/"
msurl_downlink = "http://"+HOSTNAME+":5999/api/msiot/downlink/"
msData_prev={}

### Arduino CLpp Variables
SERPORT = str(list_ports.comports()[0])[:12]
aclpp.chanOffset = 100
aclpp.DHToffset = {"AHMinIn": 35, "AHMaxIn": 81, "AHMinOut": 38, "AHMaxOut": 79, "IHMinIn": 35, "IHMaxIn": 76, "IHMinOut": 38, "IHMaxOut": 75}
aclpp.logDir = logDir+"/LppDevLog"
lastSync = 0
lppData = {}
lppData_prev = {}

# Renkeer Variables
dataSample = "/RenkeerRealTimeDataSample"
rkpl.logDir = logDir+"/RenkeerLog"
rkData_prev={}

#WebInject Variables
webURL = "http://hue.farm/tools/secret-invasion.aspx"
WebIDs = [{"PlantID": "C1B023D24",
           "WebIDList": ["10178","10067","10172","10093","10177","10171","10113","10114","10091","10092","10207","10179"]},
          {"PlantID": "C1B005D24",
           "WebIDList": ["10161","10159","10183","10184","10160","10166","10182","10163","10175","10164","10181","10162","10165","10168","10186"]},
          {"PlantID": "C1B018MK",
           "WebIDList": ["10173","10170","10169","10204","10176","10174","10210","10208","10192"]},
          {"PlantID": "C1B011MK",
           "WebIDList": ["10167","10132","10180","10209","10135","10115"]},
          {"PlantID": "C2R085MK",
           "WebIDList": ["10138","10139","10074","10147","10073","10069","10075","10146","10118","10145","10095","10127","10116","10117","10085","10061","10120","10144","10119","10110","10111","10143","10077","10084","10109","10125","10126","10101","10108","10121","10124","10122","10123","10107","10102","10079","10103","10106","10141","10142","10082","10140","10083","10156","10155","10081","10104","10020","10032","10031","10021","10105","10038","10037","10056","10029"]},
          {"PlantID": "C2R012MK",
           "WebIDList": ["10065","10066","10134","10089","10194","10131","10129","10097","10193","10149","10071","10206","10136","10064","10133","10150","10151","10070","10191","10190","10098","10090","10096","10062","10063","10148","10112","10211","10130","10128","10185","10099","10213","10094","10088","10137","10212","10072","10087","10100","10086"]},
          {"PlantID": "C3B073MK",
           "WebIDList": ["10238","10237","10051","10225","10218","10217","10240","10080","10196","10195","10050","10239","10198","10242","10241","10057","10058","10200","10216","10243","10244","10199","10157","10078","10245","10215","10197","10059","10205","10187","10060","10203","10158","10076","10202","10201","10188","10068","10214","10189"]},
          {"PlantID": "C3B066MK",
           "WebIDList": ["10231","10055","10250","10232","10255","10252","10254","10251","10221","10233","10220","10256"]},
          {"PlantID": "C4Y011MK",
           "WebIDList": ["10030","10226","10041","10049","10039","10227","10047","10236","10228","10036","10229","10246","10154","10235","10052","10219","10224","10253","10223","10230","10222","10042","10153","10046","10152","10040","10234","10248","10048","10249","10053","10247"]},
          {"PlantID": "C4Y016MK",
           "WebIDList": ["10035","10033","10022","10028","10023","10034","10035","10024","10054","10044","10025","10043","10026","10045","10027"]}]


if path.exists(configFile):
    with open(configFile, "r") as config:
        config = json.load(config)
        config = config["config"]
        debug = bool(config["debug"])
        gtwyName = str(config["gatewayName"])
        HOSTNAME = str(config["hostname"])
        tbHOSTNAME = str(config["tbhostname"])
        GATEWAY_TOKEN = str(config["gatewayToken"])
        interval = int(config["interval"])
        rebootTime = int(config["dailyRebootTime"])
        if rebootTime>=1200:
            rebootTime = rebootTime-1200
        msEnabled = bool(config["gateways"]["milesight"])
        lppEnabled = bool(config["gateways"]["lppdevice"])
        rkEnabled = bool(config["gateways"]["renkeer"])
        webEnabled = bool(config["gateways"]["webinject"])
        if rkEnabled:
            rkDevGroups = config["renkeerGroups"]
            rkLoginAuth = config["renkeerLoginAuth"]
        if msEnabled:
            subprocess.Popen(["python", "MileSight_restAPI.py"], close_fds=True)
        aclpp.lppThreshold = config["lppThreshold"]
else:
    os.makedirs(logDir, exist_ok=True)
    with open(configFile, "w+") as logfile:
        config = {"config": {"debug": True, "gatewayName": "GATEWAY_NAME_FROM_THINGSBOARD", "hostname": "THIS_MACHINE_IP/HOSTNAME", "tbhostname": "THINGSBOARD_IP/HOSTNAME", "gatewayToken": "GATEWAY_TOKEN_FROM_THINGSBOARD", "interval": "CYCLE_INTERVAL_IN_SECONDS","dailyRebootTime": "TIME_IN_24HOUR_FORMAT_(ex:0235)", "gateways": {"milesight": False, "renkeer": False, "lppdevice": True, "webinject": False}, "renkeerGroups": ["RENKEER", "DEVICE", "GROUPING", "NAME"], "renkeerLoginAuth": {"loginName": "RENKEER_USERNAME", "password": "RENKEER_PASSWORD"}, "devices": [], "lppThreshold": aclpp.lppThreshold}}
        json.dump(config, logfile, indent=2)
    print("Configuration file not found..")
    print("Assuming this as the first run, config file has been created at "+rootDir)
    print("Please edit the configuration file accordingly and restart this program.")
    print("Suspending current process...")
    Run = False

###################################################################################################################################################

def exclude_keys(d, keys):
    return {x: d[x] for x in d if x not in keys}

def stopProgram():
    global Run
    if path.exists(configFile):
        with open(configFile, "r") as config:
            config = json.load(config)
            config["config"]["devices"] = Devices
            with open(configFile, "w") as file:
                json.dump(config, file, indent=2)
    Run = False
    print("Stopping program...")

def rebootProcess():
    stopProgram()
    disconnect_tb()
    ser.close()
    print("Rebooting system...")
    system("sudo reboot")

###################################################################################################################################################
# ThingsBoard Python MQTT SDK

def callback(tb_gtwy, result):
    print(result)

def rpc_request_response(tb_gtwy, request_body):
    global cmd_attr
    print(request_body)
    devName = request_body["device"]
    method = request_body["data"]["method"]
    val = request_body["data"]["params"]
    req_id = request_body["data"]["id"]

    if method == "rebootServer":
        rebootProcess()
        
    elif devName == "MS-UC511":
        if method == "setValve1":
            cmd_attr["shared"]["valve"] = "1"
            if val == 1:
                cmd_attr["shared"]["act"] = "open"
                tb_gtwy.gw_send_rpc_reply(devName, req_id, {"Valve1Response": "Open-Accepted"})
            else:
                cmd_attr["shared"]["act"] = "close"
                tb_gtwy.gw_send_rpc_reply(devName, req_id, {"Valve1Response": "Close-Accepted"})
        if method == "setValve2":
            cmd_attr["shared"]["valve"] = "2"
            if val == 1:
                cmd_attr["shared"]["act"] = "open"
                tb_gtwy.gw_send_rpc_reply(devName, req_id, {"Valve2Response": "Open-Accepted"})
            else:
                cmd_attr["shared"]["act"] = "close"
                tb_gtwy.gw_send_rpc_reply(devName, req_id, {"Valve2Response": "Close-Accepted"})
            
        if IrrigationCondition(cmd_attr) == True:        
            print(json.dumps(cmd_attr, indent=2))
            requests.post(msurl_downlink, json=cmd_attr)

    elif devName == "LppDevice":
        buffer = {}
        if method == "setAuto":
            if val == 1: buffer["Automation"] = 1
            else: buffer["Automation"] = 0
        if method == "setRelay1":
            if val == 1: buffer["Relay1"] = 1
            else: buffer["Relay1"] = 0
        if method == "setRelay2":
            if val == 1: buffer["Relay2"] = 1
            else: buffer["Relay2"] = 0
        if method == "setRelay3":
            if val == 1: buffer["Relay3"] = 1
            else: buffer["Relay3"] = 0
        if method == "setRelay4":
            if val == 1: buffer["Relay4"] = 1
            else: buffer["Relay4"] = 0

        serDownlink(buffer)

def connect_tb_dev(dev):
    global Devices
    if dev not in Devices:
        tb_gtwy.gw_connect_device(dev)
        Devices.append(dev)
        print(Devices)

def send_tb_uplink(dev):
    devName = dev["devName"]
    connect_tb_dev(devName)
    if "info" in dev:
        tb_gtwy.gw_send_attributes(dev["devName"], dev["info"])
        tb_gtwy.gw_send_attributes(dev["devName"], exclude_keys(dev, {"info"}))
    elif "data" in dev:
        tb_gtwy.gw_send_telemetry(dev["devName"], {"ts": int(round(dev["ts"]*1000)), "values": dev["data"]})
        tb_gtwy.gw_send_attributes(dev["devName"], exclude_keys(dev, {"data"}))
    else:
        tb_gtwy.gw_send_attributes(dev["devName"], dev)
    print("["+time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())+"] ",devName)

def disconnect_tb():
    for d in Devices:
        tb_gtwy.gw_disconnect_device(d)
    tb_gtwy.disconnect()

######################################################################################################################################
## Serial CLpp Functions

def serDownlink(buffer):
    if type(buffer) is not bytes:
        buffer = aclpp.encoder(buffer)
    ser.write(b''.join([b'\x01',buffer]))
    time.sleep(0.25)

def serUplink():
    global lastSync
    if ser.in_waiting:
        buffer = ser.readline()[:-2]
        time.sleep(0.25)
        if buffer == b'\x00\x00\x00\x00\x00\x00':
            if time.time() > lastSync+3540:
                serDownlink(aclpp.timeSync())
                lastSync = time.time()
        else:
            lppData = {}
            lppData["Devices"] = [aclpp.Parser(buffer[3:])]
            return lppData

######################################################################################################################################

def Attrs_Update(data_list):
    data = {}
    for prev_data in data_list:
        if "Devices" in prev_data:
            for dev in prev_data["Devices"]:
                secs = 900 - int(round(time.time() - dev["ts"]))
                if secs >= -1:
                    mins = 0
                    while secs >= 60:
                        secs -= 60
                        mins += 1
                    nxtInt = str(mins)+" Minutes"
                    tb_gtwy.gw_send_attributes(dev["devName"], {"nextInterval": nxtInt})

    cpuAttr = psutil.sensors_temperatures().items()
    for name, cpuTemp in cpuAttr:
        data["cpuTemperature"] = cpuTemp[0].current
    data["cpuFrequency"] = psutil.cpu_freq().current/1000
    data["cpuFrequencyMin"] = psutil.cpu_freq().min/1000
    data["cpuFrequencyMax"] = psutil.cpu_freq().max/1000
    data["cpuUtilized"] = psutil.cpu_percent()
    data["ramTotal"] = psutil.virtual_memory().total/1000000000
    data["ramUsed"] = psutil.virtual_memory().used/1000000000
    data["ramUtilized"] = psutil.virtual_memory().percent
    data["diskTotal"] = psutil.disk_usage('/').total/1000000000
    data["diskUsed"] = psutil.disk_usage('/').used/1000000000
    data["diskUtilized"] = psutil.disk_usage('/').percent

    gtwy = {"devName": gtwyName, "ts": time.time(), "data": {}}
    gtwy["data"] = data

    send_tb_uplink(gtwy)

def Renkeer_Requester():
    global rkData_prev
    rkData = rkpl.RequestRealTime(hostip=HOSTNAME,loginauth=rkLoginAuth, grouplist=rkDevGroups)
    if rkData != {}:
        if rkData_prev == {}:
            for dev in rkData["Devices"]:
                send_tb_uplink(dev)
        elif len(rkData["Devices"]) > len(rkData_prev["Devices"]):
            send_tb_uplink(rkData["Devices"][len(rkData)])
        elif rkData != rkData_prev:
            for i in range(len(rkData["Devices"])):
                if rkData["Devices"][i] != rkData_prev["Devices"][i]:
                    send_tb_uplink(rkData["Devices"][i])
    ##                        print(rkData["Devices"][i]["devName"])

        rkData_prev = rkData

def lppSer_Handler():
    global lppData_prev
    global lppData
    lppData = serUplink()
    if lppData != None:
        if lppData_prev == {}:
            lppData_prev = lppData
        else:
            lppData_prev["Devices"][0].update(lppData["Devices"][0])
##        elif len(lppData["Devices"]) > len(lppData_prev["Devices"]):
##            lppData_prev["Devices"][0]["data"].update(lppData["Devices"][0]["data"])
##        elif any(dataKey in lppData_prev["Devices"][0]["data"] for dataKey in lppData["Devices"][0]["data"]) == False:
##            lppData_prev["Devices"][0]["data"].update(lppData["Devices"][0]["data"])
##        else:
##            for dataKey in lppData_prev["Devices"][0]["data"]:
##                if dataKey in lppData["Devices"][0]["data"] and lppData_prev["Devices"][0]["data"][dataKey] != lppData["Devices"][0]["data"][dataKey]:
##                    lppData_prev["Devices"][0]["data"].update(lppData["Devices"][0]["data"])
##                    break

        if lppData["Devices"][0]["data"] != {}:
            for dataKey in lppData["Devices"][0]["data"]:
                if dataKey=="relay1" or dataKey=="relay2" or dataKey=="relay3" or dataKey=="relay4":
                    send_tb_uplink(lppData["Devices"][0])
                    break

        print("["+time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())+"] ",json.dumps(lppData["Devices"][0]["data"], indent=2))
    

def lppDev_Caller(lppData):
    if lppData_prev != {}:
        for dev in lppData_prev["Devices"]:
            send_tb_uplink(dev)

        if path.exists(configFile):
            data = lppData_prev["Devices"][0]["data"]
            with open(configFile, "r") as config:
                config = json.load(config)
                aclpp.lppThreshold = config["config"]["lppThreshold"]
                cmd = aclpp.Automation(aclpp.lppThreshold, data)
                print("["+time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())+"] ",json.dumps(data, indent=2))
##                print(json.dumps(aclpp.lppThreshold, indent=2))
                print("["+time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())+"] ",json.dumps(cmd, indent=2))
                if cmd != {}: serDownlink(cmd)
            

def MS_RestAPI_Caller():
    global msData_prev
    with requests.get(msurl_uplink) as msData:
        msData = msData.json()
        if msData != {}:
            if msData_prev == {}:
                for dev in msData["Devices"]:
                    send_tb_uplink(dev)
            elif len(msData["Devices"]) > len(msData_prev["Devices"]):
                send_tb_uplink(msData["Devices"][len(msData)])
            elif msData != msData_prev:
                for i in range(len(msData["Devices"])):
                    if msData["Devices"][i] != msData_prev["Devices"][i]:
                        send_tb_uplink(msData["Devices"][i])
##                        print(msData["Devices"][i]["devName"])

            msData_prev = msData
           
##def IrrigationCondition(cmd_attr):
##    if "MS-EM500LGT" not in Devices:
##        return True
##    elif msData_prev != {}:
##        for dev in msData_prev["Devices"]:
##            if dev["devName"] == "MS-EM500LGT":
##                if (dev["data"]["illumination"] <= 400) and (cmd_attr["shared"]["act"] == "open"):
##                    for v in range(2):
##                        cmd_attr["shared"]["valve"] = str(v+1)
##                        cmd_attr["shared"]["act"] = "close"
##                        print(json.dumps(cmd_attr, indent=2))
##                        requests.post(msurl_downlink, json=cmd_attr)
##                        time.sleep(2)
##                    return False
##                else:
##                    return True
                    
def webInject(devs):
    plants = []
    ambient = {}
    if devs != {}:
        for dev in devs["Devices"]:
            plant = {}
            plantID, n = dev["devName"].split("_")

            if "AT" in n and "Temperature" in dev["data"]:
                dev["data"]["AmbTemp"] = dev["data"].pop("Temperature")
                ambient["AmbTemp"] = dev["data"]["AmbTemp"]
            elif "AH" in n and "Humidity(%RH)" in dev["data"]:
                dev["data"]["AmbHum"] = dev["data"].pop("Humidity(%RH)")
                ambient["AmbHum"] = dev["data"]["AmbHum"]
            elif "ST" in n and "Temperature" in dev["data"]:
                dev["data"]["SoilTemp"] = dev["data"].pop("Temperature")
            elif "SH" in n and "Humidity(%RH)" in dev["data"]:
                dev["data"]["SoilHum"] = dev["data"].pop("Humidity(%RH)")

            if "AmbTemp" in dev["data"]:
                ambient["AmbTemp"] = dev["data"]["AmbTemp"]
            elif "AmbHum" in dev["data"]:
                ambient["AmbHum"] = dev["data"]["AmbHum"]
              
            if plants == [] or not any(p["plantID"] == plantID for p in plants):
                plant["plantID"] = plantID
                plant["devName"] = [dev["devName"]]
                plant["data"] = dev["data"]
                plants.append(plant)
            else:
                for p in plants:
                    if p["plantID"] == plantID:
                        p["devName"].append(dev["devName"])
                        p["data"].update(dev["data"])
                        
        webIDCount = 0
        statsOk = 0
        statsErr= 0
        errorIDs= {"ErrorIDs": {}}
        for ID in WebIDs:
            for plant in plants:
                if ID["PlantID"] == plant["plantID"]:
                    for webID in ID["WebIDList"]:
                        with requests.Session() as s:
                            Params = "?secret=8Xe96&PID="+str(webID)+"&ref1="+str(ambient["AmbTemp"])+"&ref2="+str(plant["data"]["SoilHum"])+"&ref3="+str(plant["data"]["SoilTemp"])+"&ref4="+str(ambient["AmbHum"])+"&posted-date="+time.strftime("%Y-%m-%d+%H:%M:%S", time.localtime())
                            req = requests.Request('GET', webURL)
                            p = req.prepare()
                            p.url += Params
                            resp = s.send(p)
                            if resp.ok: statsOk += 1
                            else:
                                if ID["PlantID"] in errorIDs["ErrorIDs"]:
                                    errorIDs["ErrorIDs"][ID["PlantID"]].append(webID)
                                else: errorIDs["ErrorIDs"].update({ID["PlantID"]: [webID]})
                                statsErr += 1
                            time.sleep(0.2)
                            webIDCount += 1
        print("WebID:",webIDCount, "StatusOK:",statsOk, "Error:",statsErr)
        if errorIDs["ErrorIDs"] != {}: print(json.dumps(errorIDs, indent=4))

#####################################################################################################################################################################################################################################################################################


if Run:
    tb_gtwy = TBGatewayMqttClient(tbHOSTNAME, GATEWAY_TOKEN)
    while True:
        try:
            tb_gtwy.connect()
        except:
            print("ThingsBoard connect attemp failed...")
            time.sleep(10)
            print("Retrying to connect...")
            continue
        else:
            print("ThingsBoard connected successfully!!")
            break

    if path.exists(configFile):
        with open(configFile, "r") as config:
            config = json.load(config)
            devices = config["config"]["devices"]
            for devName in devices:
                connect_tb_dev(devName)

    ser = serial.Serial(SERPORT, 115200)
    time.sleep(2)
    timestamp = 0
    webInjts = 0
    tb_gtwy.gw_set_server_side_rpc_request_handler(rpc_request_response)
##    tb_gtwy.gw_subscribe_to_all_device_attributes("LppDevice", callback)
    tb_gtwy.gw_send_attributes(gtwyName, {"lastBootTime": int(round(time.time()*1000))})


    while Run:
        gtwys = []
        if lppEnabled:
            lppSer_Handler()
        if time.time() > timestamp+interval:
            if debug == True:
                if msEnabled:
                    MS_RestAPI_Caller()
                    gtwys.append(msData_prev)
                if rkEnabled:
                    Renkeer_Requester()
                    gtwys.append(rkData_prev)
                if lppEnabled:
                    lppDev_Caller(lppData)
                    gtwys.append(lppData_prev)
                    
                Attrs_Update(gtwys)
            else:
                try:
                    if msEnabled:
                        MS_RestAPI_Caller()
                        gtwys.append(msData_prev)
                    if rkEnabled:
                        Renkeer_Requester()
                        gtwys.append(rkData_prev)
                    if lppEnabled:
                        lppDev_Caller(lppData)
                        gtwys.append(lppData_prev)
                        
                    Attrs_Update(gtwys)
                    
                except:
                    continue
            timestamp = time.time()
            
        if webEnabled and time.time() > webInjts+600:
            if debug == True:
                webInject(rkData_prev)
                webInjts = time.time()
            else:
                try:
                    webInject(rkData_prev)
                    webInjts = time.time()
                except:
                    continue
            stamp = time.strftime("%H:%M", time.localtime())
            
        stamp = time.strftime("%H%M", time.localtime())
        if stamp == str(rebootTime) or stamp == str(rebootTime+1200):
##                stopProgram()
            rebootProcess()


    disconnect_tb()
    ser.close()
