import json, requests, time
import MSPayloadHandler as mspl
from flask import Flask, jsonify, make_response, request
from os import system, name, path

import socket
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.connect(("8.8.8.8", 80))
HOSTNAME = s.getsockname()[0]
s.close()

app = Flask(__name__)
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True

MSRawLog = "/tb-pyGateway/logs/MSRawLog"
MSParsedLog ="/tb-pyGateway/logs/MSLog" 
pocketUp = {}
pocketDown = {}
ACK = {}

#############################################################################################################################################################

## URL for MileSight UG65 http API ##
URL_CGI = 'http://192.168.7.9/cgi'
URL_REQ_TOKEN = 'http://192.168.7.9/api/internal/login'
URL_GET_APP_LIST = 'http://192.168.7.9/api/urapplications?limit=9999&offset=0&organizationID=1'
URL_GET_DEVICES = 'http://192.168.7.9/api/urdevices?search=&order=asc&offset=0&limit=10&organizationID=1'
URL_LOGOUT = 'http://192.168.7.9/logout'
URL_ISLOGIN = 'http://192.168.7.9/islogin'
def URL_DOWNLINK(devEUI):
    return 'http://192.168.7.9/api/devices/'+str(devEUI)+'/queue'

## data content to pass for MileSight UG65 http API ##
TOKEN_AUTH = '{"username":"admin","password":"NicJjG18XOV3U1efQyo8AQ=="}'
def CGI_CONTENT(funct, ID):
    if funct == "login":
        return str({"id":"1","execute":1,"core":"user","function":"login","values":[{"username":"admin","password":"dIAvhuLsATpCgLlJf1fRwA=="}]})
    elif funct == "status":
        return str({"id":str(ID),"execute":1,"core":"yruo_loragw","function":"get","values":[{"base":"ns_general"}]})
    elif funct == "logout":
        return str({"id":str(ID),"execute":1,"core":"","function":""})
def DOWNLINK_PAYLOAD(devEUI, payload, fPort):
    return '{"devEUI":"'+str(devEUI)+'","data":"'+str(payload)+'","fPort":'+str(fPort)+',"confirmed":true}'

HEADERS = {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
           "Connection": "keep-alive"}

def downlink_MSUG65(cmd_attr):
    with requests.Session() as s:
        global HEADERS
        ID = 1
        s.post(URL_CGI, data=CGI_CONTENT("login", ID), headers=HEADERS)
        ID += 1

        AUTH_BEARER = s.post(URL_REQ_TOKEN, data=TOKEN_AUTH, headers=HEADERS)
        ID += 1

        AUTH_BEARER = json.loads(AUTH_BEARER.text)
        HEADERS |= {"authorization": "Bearer "+AUTH_BEARER["jwt"]}
        payload = mspl.UC511_Encoder(cmd_attr["shared"]["valve"],cmd_attr["shared"]["act"],cmd_attr["shared"]["dur"],cmd_attr["shared"]["counter"])

        s.post(URL_DOWNLINK(cmd_attr["client"]["devEUI"]), data=DOWNLINK_PAYLOAD(cmd_attr["client"]["devEUI"],payload,cmd_attr["client"]["fPort"]), headers=HEADERS)
        ID += 1

        s.post(URL_LOGOUT, data=CGI_CONTENT("logout", ID), headers={"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"})

###################################################################################################################################################

@app.errorhandler(404)
def not_found(error):

    print(error)

    return make_response(jsonify({'error': 'Not found'}), 404)

@app.route('/api/msiot/uplink/', methods=['POST', 'GET'])
def api_uplink():
    global pocketUp
    if request.method == 'POST':
        if not request.json:
            packet = request.data
            print(packet)
        else:
            packet = request.json

            if path.exists(MSRawLog):
                with open(MSRawLog, "a") as logfile:
                    logfile.write(",\n")
                    json.dump(packet, logfile)
            else:
                with open(MSRawLog, "x") as logfile:
                    json.dump(packet, logfile)

            packet = mspl.Parser(packet)

            if path.exists(MSParsedLog):
                with open(MSParsedLog, "a") as logfile:
                    logfile.write(",\n")
                    json.dump(packet, logfile)
            else:
                with open(MSParsedLog, "x") as logfile:
                    json.dump(packet, logfile)

        if pocketUp == {}:
            pocketUp["Devices"] = [packet]
        elif any(packet["devEUI"] in dev["devEUI"] for dev in pocketUp["Devices"]) == False:
            pocketUp["Devices"].append(packet)
        else:
            for dev in pocketUp["Devices"]:
                if packet["devEUI"] == dev["devEUI"]:
                    pocketUp["Devices"][pocketUp["Devices"].index(dev)] = packet
                    
        return make_response("packet received", 201)

    elif request.method == 'GET':
        return jsonify(pocketUp)

@app.route('/api/msiot/downlink/', methods=['POST', 'GET'])
def api_downlink():
    global pocketDown
    if request.method == 'POST':
        if not request.json:
            packet = request.data
            print(packet)
        else:
            packet = request.json
            print(packet)
            downlink_MSUG65(packet)

        pocketDown = packet
        return make_response("packet received", 201)

    elif request.method == 'GET':
        return jsonify(pocketDown)

@app.route('/api/msiot/ack/', methods=['POST', 'GET'])
def api_ack():
    global ACK
    if request.method == 'POST':
        if not request.json:
            packet = request.data
            print(packet)
        else:
            packet = request.json
            print(jsonify(ACK))

        ACK = packet
        return make_response("packet received", 201)
    
    elif request.method == 'GET':
        return jsonify(ACK)
        
if __name__ == '__main__':
    app.run(host = HOSTNAME, port = 5999)
