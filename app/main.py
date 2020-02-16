try:
    import urllib
    import json
    import os
    from flask import Flask,request,make_response,jsonify
    import requests
    import csv
    from operator import itemgetter
    from datetime import datetime
    from requests_futures.sessions import FuturesSession
    from df_response_lib import telegram_response, fulfillment_response

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

        bus_no = getParamFromParam(req,'bus_no')
        route_od = getBusRoute(req,bus_no)
        reply = {'fulfillmentText': 'Bus is going from ' + route_od[0] + ' to ' + route_od[1] }

    elif action == 'route.entered_getDirection':

        bus_no = getParamFromContext(req,'awaiting_bus_no','bus_no')
        route_od = getBusRoute(req,bus_no)
        orig_en = 'Origin: '+route_od[0]
        dest_en = 'Destination: '+route_od[1]

        fulfillmentText = 'Where are you heading off to?'

        # create telegram quick replies for suggestions
        tg = telegram_response()
        tg_qr = tg.quick_replies(fulfillmentText,[orig_en,dest_en])

        ff_response = fulfillment_response()
        ff_text = ff_response.fulfillment_text(fulfillmentText)
        ff_messages = ff_response.fulfillment_messages([tg_qr])
        
        reply = ff_response.main_response(ff_text, ff_messages)


    elif action == 'direction.selected_getStopList':
        
        bus_no = getParamFromContext(req,'awaiting_bus_no','bus_no')
        direction = getParamFromParam(req,'direction')
        
        if direction[0].strip('\:').lower()=='origin':
            dir='inbound'
        else:
            dir='outbound'
        
        all_stop = getRouteStop(bus_no,dir)
        all_stop_name_json = makeStopRequest(all_stop)
        stop_str_list = [str(i)+'. '+stop_obj['data']['name_en'] for i,stop_obj in enumerate(all_stop_name_json,1)]
        
        fulfillmentText = 'Which bus stop are you at?\n'+'\n'.join([stop_name for stop_name in stop_str_list])
        reply = {'fulfillmentText': fulfillmentText }
        

    elif action == 'stop.selected_getETA':
        
        nth = {1:"First",2:"Second",3:"Third"}

        bus_no = getParamFromContext(req,'awaiting_bus_no','bus_no')
        stop_no = getParamFromParam(req,'number')
        eta_in_min = getBusETA(bus_no,int(stop_no))

        if eta_in_min != -1:
            res = '.\n'.join(nth[k]+' bus is coming in '+str(v)+' min(s)' for k,v in enumerate(eta_in_min,1))
            reply = {"fulfillmentText": res}
        else:
            reply = {"fulfillmentText": 'Sorry, the last bus has departed at the bus stop.'}


    elif action == 'getBusStopLocation':
        
        stop_no = getParamFromContext(req,'awaiting_bus_no','number')
        lat,long = getStopLocation(stop_no)

        fulfillmentText = 'location'
        tg = telegram_response()

        custom_payload = {
        "payload": {
          "telegram": {
            "text": "Here is the bus stop! [Google Map](https://maps.google.com/?q="+lat+","+long+")",
            "parse_mode": "Markdown"
          }
        },
        "platform": "TELEGRAM"
      }

        ff_response = fulfillment_response()
        ff_text = ff_response.fulfillment_text(fulfillmentText)
        ff_messages = ff_response.fulfillment_messages([custom_payload])
        
        reply = ff_response.main_response(ff_text, ff_messages)
        
    else:
        reply = {"fulfillmentText": 'Unexpected action.'}

    return make_response(jsonify(reply))

def getParamFromParam(req,param):
    return req['queryResult']['parameters'][param]

def getParamFromContext(req,context,param):
    outputContexts = req['queryResult']['outputContexts']
    index = [item['name'].split('/')[-1] for item in outputContexts].index(context)
    return outputContexts[index]['parameters'][param]

def getBusRoute(req,busno):
    
    route_api = 'https://rt.data.gov.hk/v1/transport/citybus-nwfb/route/'
    parameters = req['queryResult']['parameters']

    companyid = getCompanyid(busno)
    route_url = route_api+companyid+'/'+busno
    bus_route = requests.get(route_url).json()['data']

    route_od = []
    route_od.append(bus_route['orig_en'])
    route_od.append(bus_route['dest_en'])

    return route_od

def getRouteStop(busno,dir):

    routestop_api = 'https://rt.data.gov.hk/v1/transport/citybus-nwfb/route-stop/'
    companyid = getCompanyid(busno)
    routestop_url = routestop_api+companyid+'/'+busno+'/'+dir
    bus_route = requests.get(routestop_url).json()['data']

    stop_list = [bus_route[i]['stop'] for i in range(len(bus_route))]

    with open('tmp_stop.csv', 'w') as csv_file:
        wr = csv.writer(csv_file)
        wr.writerow(stop_list)

    return stop_list

def getBusETA(busno,stopno):    # return a list of eta time in minutes

    stop_dict = StopFiletoDict()
    eta_api = 'https://rt.data.gov.hk/v1/transport/citybus-nwfb/eta/'
    companyid = getCompanyid(busno)
    stopid = stop_dict[stopno-1]
    eta_url = eta_api+companyid+'/'+stopid+'/'+busno
    eta_result = requests.get(eta_url).json()['data']

    if len(eta_result)>0:
        # sort by eta seq then return list of eta time
        sorted_list = sorted([[eta_result[i]['eta_seq'],eta_result[i]['eta']] for i in range(len(eta_result))],key=itemgetter(1))
        eta_time = list(map(itemgetter(1), sorted_list))
        return list(map(timeDiff,eta_time))
    else:
        return -1

    """ 
    add exception handler for KMB timeslot issue
     """

def getStopLocation(stopno):

    stop_dict = StopFiletoDict()
    stopid = stop_dict[stopno]
    stop_api = "https://rt.data.gov.hk/v1/transport/citybus-nwfb/stop/"
    stop_url = stop_api+stopid
    stop_result = requests.get(stop_url).json()['data']
    stoploc = []
    stoploc.append(stop_result['lat'])
    stoploc.append(stop_result['long'])
    return stoploc

def StopFiletoDict():

    with open('tmp_stop.csv') as f:
        reader = csv.reader(f)
        row1 = next(reader)
        stop_dict = {k:v for k,v in enumerate(row1)}
    return stop_dict

def makeStopRequest(stop_list):

    session = FuturesSession(max_workers=16)
    futures = [make_stop_request(session,stopid) for stopid in stop_list]
    all_stops = []
    for f in futures:
        all_stops.append(f.result().data)
    return all_stops

def make_stop_request(session, stopid):
    api_url = "https://rt.data.gov.hk/v1/transport/citybus-nwfb/stop/"
    future = session.get(api_url+stopid, hooks={'response': response_hook,})
    return future

def getCompanyid(bus_no):

    api_url = 'https://rt.data.gov.hk/v1/transport/citybus-nwfb/route/'

    if requests.get(api_url+'NWFB/'+ bus_no).json()['data']:
        return 'NWFB'
    elif requests.get(api_url+'CTB/'+ bus_no).json()['data']:
        return 'CTB'

def timeDiff(time):
    fmt = '%Y-%m-%dT%H:%M:%S'
    d1 = datetime.strptime(time[:-6],fmt)
    return int((d1-datetime.now()).total_seconds()/60)

def response_hook(resp, *args, **kwargs):
    resp.data = resp.json()
    

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    print ("Starting app on port %d" %(port))
    app.run(debug=True, port=port, host='0.0.0.0')