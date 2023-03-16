# -*- coding: utf-8 -*-
import base64, json, time

## Define constant variable ##
## data Channel for MileSight devices ##
INFO  = b'\xff'
CONT  = b'\xff'
RPLY  = b'\xfe'
BATT  = b'\x01'
CHA1  = b'\x03'
CHA2  = b'\x04'
CHA3  = b'\x05'
CHA4  = b'\x06'

## Device Data Type, Size & Unit ##
BattLvl  = (117, 1, "%", "battery")
DataType = [(1, 1, "", "valve"),
            (200, 4, "", "counter"),
            (103, 2, "°C", "temperature"),
            (104, 1, "%RH", "humidity"),
            (115, 2, "hPa", "barometricPressure"),
            (119, 2, "cm", "depth"),
            (123, 2, "kPa", "pressure"),
            (125, 2, "ppm", "concentration"),
            (127, 2, "us/cm", "ec"),
            (130, 2, "mm", "distance"),
            (148, 4, "lux", "illumination"),
            (202, 2, "%", "moisture")]

## UC511 downlink payload encoding ##
Bin_Prefix  =  '0b'
Bin_Spacer  =  '000'
Valve_1     =  '00'
Valve_1     =  '01'
Seq         =  00
    
def valDe(buff):
    val = int.from_bytes(buff,"little", signed=True)
    return val

def valDeU(buff):
    val = int.from_bytes(buff,"little")
    return val

def valEnU(val, leng):
    buff = int(val).to_bytes(leng,"little")
    return buff

def UC511_Encoder(valv, act, dur=None, pul=None):
    global Seq
    cont = Bin_Prefix

    if bool(dur) != False:
        cont = cont+'1'
        dur = valEnU(dur,3)
    else:
        cont = cont+'0'

    if bool(pul) != False:
        cont = cont+'1'
        pul = valEnU(pul,4)
    else:
        cont = cont+'0'

    if act == 'open':
        cont = cont+'1'
    else:
        cont = cont+'0'

    cont = cont+Bin_Spacer

    if valv == '1':
        cont = cont+'00'
    elif valv == '2':
        cont = cont+'01'

    payload = b''.join([b'\xff\x1d',valEnU(int(cont,2),1),valEnU(Seq,1)])
    if bool(dur) != False:
        payload = b''.join([payload,dur])
    if bool(pul) != False:
        payload = b''.join([payload,pul])
        
    Seq += 1
    if Seq > 255:
        Seq = 00
        
    payload = base64.b64encode(payload)
    return payload.decode('utf-8')
        
def DevInfo(coded):
    ind = 0
    info = {}
    while ind < len(coded):
        if coded[ind+1:ind+2] == b'\x01':
            info["protocVer"] = "v"+coded[ind+2:ind+3].hex()
            ind=ind+2+1

        if coded[ind+1:ind+2] == b'\x09':
            info["hardVer"] = "v"+str(round(int(coded[ind+2:ind+4].hex())*0.01, 2))
            ind=ind+2+2
            
        if coded[ind+1:ind+2] == b'\x0a':
            info["softVer"] = "v"+str(round(int(coded[ind+2:ind+4].hex())*0.01, 2))
            ind=ind+2+2
            
        if coded[ind+1:ind+2] == b'\x0b':
            info["powerOn"] = True
            ind=ind+2+1
            
        if coded[ind+1:ind+2] == b'\x0f':
            cls = coded[ind+2:ind+3].hex()
            if cls == "00":
                info["devClass"] = "Class A"
            elif cls == "01":
                info["devClass"] = "Class B"
            elif cls == "02":
                info["devClass"] = "Class C"
            ind=ind+2+1
            
        if coded[ind+1:ind+2] == b'\x16':
            info["devSN"] = coded[ind+2:ind+10].hex()
            ind=ind+2+8
            
    return info

def DevData(coded):
    loop = 0
    ind = 0
    data = {}
    while ind < len(coded):
        if coded[ind:ind+1] == BATT and coded[ind+1] == BattLvl[0]:
            data["battery"] = coded[ind+2]
            ind=ind+2+1
        
        if CHA1 in coded:
            Ind = coded.index(CHA1)+1
            for i in range(len(DataType)):
                if coded[Ind] == DataType[0][0]:
                    data[DataType[0][3]+"1"] = coded[Ind+1]
                    ind=ind+2+DataType[0][1]
                elif coded[Ind] == DataType[i][0]:
                    if coded[Ind] == DataType[2][0] or DataType[5][0]:
                        data[DataType[i][3]] = valDe(coded[Ind+1:Ind+1+DataType[i][1]])
                    else:
                        data[DataType[i][3]] = valDeU(coded[Ind+1:Ind+1+DataType[i][1]])
                    ind=ind+2+DataType[i][1]
            
        if CHA2 in coded:
            Ind = coded.index(CHA2)+1
            if len(coded) > Ind:
                for i in range(len(DataType)):
                    if coded[Ind] == DataType[1][0]:
                        data[DataType[1][3]+"1"] = valDeU(coded[Ind+1:Ind+1+DataType[1][1]])
                        ind=ind+2+DataType[1][1]
                    elif coded[Ind] == DataType[i][0]:
                        data[DataType[i][3]] = valDeU(coded[Ind+1:Ind+1+DataType[i][1]])
                        ind=ind+2+DataType[i][1]
                
        if CHA3 in coded:
            Ind = coded.index(CHA3)+1
            for i in range(len(DataType)):
                if coded[Ind] == DataType[0][0]:
                    data[DataType[0][3]+"2"] = coded[Ind+1]
                    ind=ind+2+DataType[0][1]
                elif coded[Ind] == DataType[i][0]:
                    data[DataType[i][3]] = valDeU(coded[Ind+1:Ind+1+DataType[i][1]])
                    ind=ind+2+DataType[i][1]
                                                                                                                                   
        if (CHA4 in coded) and (ind > 12):
            Ind = coded.index(CHA4)+1
            for i in range(len(DataType)):
                if coded[Ind] == DataType[1][0]:
                    data[DataType[1][3]+"2"] = valDeU(coded[Ind+1:Ind+1+DataType[1][1]])
                    ind=ind+2+DataType[1][1]
                elif coded[Ind] == DataType[i][0]:
                    data[DataType[i][3]] = valDeU(coded[Ind+1:Ind+1+DataType[i][1]])
                    ind=ind+2+DataType[i][1]

        if loop > len(coded)*2:
            print("!!PARSING ERROR!!")
            print("Too much looping, unable to parse...")
            break
        loop+=1

    return decCors(data)

def decCors(data):
    if DataType[2][3] in data:
        data[DataType[2][3]] = round(data[DataType[2][3]]*0.1, 2)
    if DataType[3][3] in data:
        data[DataType[3][3]] = round(data[DataType[3][3]]*0.5, 2)
    if DataType[4][3] in data:
        data[DataType[4][3]] = round(data[DataType[4][3]]*0.1, 2)
    if DataType[11][3] in data:
        data[DataType[11][3]] = round(data[DataType[11][3]]*0.01, 2)
    return data

def Parser(message):
    Device = {}
    try:
        message = json.loads(str(message))
    except:
        pass
    Device["time"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    Device["ts"] = time.time()
    Device["devName"] = message["deviceName"]
    Device["devEUI"] = message["devEUI"]
    Device["fCnt"] = message["fCnt"]
    Device["fPort"] = message["fPort"]
    coded_b64 = message["data"]
    coded = base64.b64decode(coded_b64)
##    print(type(coded), len(coded), coded.hex())
    
    if INFO in coded:
        Device["info"] = DevInfo(coded)
    else:
        decoded = DevData(coded)
        if decoded != {}:
            Device["data"] = decoded
        
    return Device

if "__main__" == __name__:
    while True:
        func = input('function to test : ')
        if func == 'decoder':
            message = input("Enter message/telemetry string: ")
            message = Parser(message)
            print('\n', json.dumps(message, indent=2))
            
        elif func == 'encoder':
            valv = input('valve ID(1 or 2): ')
            act = input('action(open/close) : ')
            dur = input('duration(in sec) : ')
            pul = input('pulse counter : ')
            print('\n',UC511_Encoder(valv, act, dur, pul))

        print('\n')

            
