try:
    import urllib
    import json
    import os
    from flask import Flask,request,make_response,jsonify
    import requests

except Exception as e:
    print("Some modules are missing {}".format(e))

app = Flask(__name__)

@app.route('/')
def home():
    return "Hello World!"


@app.route('/webhook', methods=['POST'])

def webhook():

    req = request.get_json(silent=True, force=True)
    print('Request: ')
    print(json.dumps(req, indent=4))

    try:
        action = req.get('queryResult').get('action')
    except AttributeError:
        return 'json error'

    if action == 'getBusRoute':
        # bus_no = getParamFromParam(req,'bus_no')
        orig,dest = getBusRoute(req)
        reply = {'fulfillmentText': orig+' to '+dest}

    elif action == 'GetRoute_ETA-direction':
        
        bus_no = getParamFromContext(req,'bus_no')
        direction = getParamFromParam(req,'direction')
        if direction=='origin':
            dir='inbound'
        else:
            dir='outbound'
        
        stop_list = getRouteStop(bus_no,dir)
        # d_stop_name = {k:getStopName(v) for k,v in enumerate(stop_list,1)}
        stop_name_list = ['Stop '+str(i)+' '+getStopName(stop) for i,stop in enumerate(stop_list,1)]

        # reply = {"fulfillmentMessages":[{"quickReplies":{"title":"Choose an option","quickReplies":[[i for i in stop_name_list]]},"platform":"TELEGRAM"},{"text":{"text":["Suggestion Chips"]}}]}
        reply = {"fulfillmentMessages":[{"quickReplies":{"title":"Choose an option","quickReplies":[stop_name_list[0],stop_name_list[1],stop_name_list[2],stop_name_list[3]]},"platform":"TELEGRAM"},{"text":{"text":["Suggestion Chips"]}}]}
         
        print(reply)
        # reply = {"fulfillmentText": dllm}


    elif action == 'GetRoute_ETA_askDirection':
        bus_no = getParamFromContext(req,'bus_no')
        orig,dest = getOrigDest(bus_no)
        reply = {"fulfillmentMessages":[{"quickReplies":{"title":"Choose an option","quickReplies":['Origin: '+orig,'Destination: '+dest]},"platform":"TELEGRAM"},{"text":{"text":["Suggestion Chips"]}}]}

    elif action == 'get_direction':
        reply = {"followupEventInput": {"name": "actions_intent_option","parameters": {"direction":"Wong Tai Sin"}}}
    else:
        log.error('Unexpected action.')

    # print('Action: ' + action)
    # print('Response: ' + res)

    return make_response(jsonify(reply))

def getParamFromParam(req,param):
    return req['queryResult']['parameters'][param]

def getParamFromContext(req,param): #e.g bus_no
    return req['queryResult']['outputContexts'][0]['parameters'][param]

def getBusRoute(req):
    
    route_api = 'https://rt.data.gov.hk/v1/transport/citybus-nwfb/route/'
    parameters = req['queryResult']['parameters']

    print('Dialogflow Parameters:')
    print(parameters['bus_no'])
    # print(json.dumps(parameters, indent=4))

    companyid = getCompanyid(parameters['bus_no'])
    route_url = route_api+companyid+'/'+parameters['bus_no']
    bus_route = requests.get(route_url).json()['data']

    orig_en = bus_route['orig_en']
    dest_en = bus_route['dest_en']
    
    return (orig_en,dest_en)

def getOrigDest(busno): # for busno from context
    
    route_api = 'https://rt.data.gov.hk/v1/transport/citybus-nwfb/route/'
 
    companyid = getCompanyid(busno)
    route_url = route_api+companyid+'/'+busno
    bus_route = requests.get(route_url).json()['data']

    orig_en = bus_route['orig_en']
    dest_en = bus_route['dest_en']
    
    return (orig_en,dest_en)

def getRouteStop(busno,dir):

    routestop_api = 'https://rt.data.gov.hk/v1/transport/citybus-nwfb/route-stop/'
    companyid = getCompanyid(busno)
    routestop_url = routestop_api+companyid+'/'+busno+'/'+dir
    bus_route = requests.get(routestop_url).json()['data']

    return [bus_route[i]['stop'] for i in range(len(bus_route))]    

def getStopName(stop_id):

    stop_api = 'https://rt.data.gov.hk/v1/transport/citybus-nwfb/stop/'
    stop_url = stop_api + stop_id
    return requests.get(stop_url).json()['data']['name_en']


def getCompanyid(bus_no):

    api_url = 'https://rt.data.gov.hk/v1/transport/citybus-nwfb/route/'

    if requests.get(api_url+'NWFB/'+ bus_no).json()['data']:
        return 'NWFB'
    elif requests.get(api_url+'CTB/'+ bus_no).json()['data']:
        return 'CTB'
    # else:
        # return 'Bus service for' + parameters['bus_no'] + ' may be shut down at the moment'


# def get_data():

#     speech = "ng lun g ar dllm"

#     return {
#         "fulfillmentText": speech,
#     }


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    print ("Starting app on port %d" %(port))
    app.run(debug=True, port=port, host='0.0.0.0')