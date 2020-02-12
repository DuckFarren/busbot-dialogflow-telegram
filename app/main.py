try:
    import urllib
    import json
    import os
    from flask import Flask,request,make_response,jsonify
    import requests

except Exception as e:
    print("Some modules are missing {}".format(e))


# Flask app should start in global layout
app = Flask(__name__)


# whenever you make request /webhook
# Following calls are made
# webhook ->
# -----------> Process requests
# ---------------------------->get_data()

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

    if action == 'get_dest':
        res = get_dest(req)
    # elif action == 'weather.activity':
    # res = weather_activity(req)
    # elif action == 'weather.condition':
    #     res = weather_condition(req)
    # elif action == 'weather.outfit':
    #     res = weather_outfit(req)
    # elif action == 'weather.temperature':
    #     res = weather_temperature(req)
    else:
        log.error('Unexpected action.')

    print('Action: ' + action)
    print('Response: ' + res)

    return make_response(jsonify({'fulfillmentText': res}))

    # res = json.dumps(res, indent=4)
    
    # r = make_response(res)
    # r.headers['Content-Type'] = 'application/json'
    # return r


def get_dest(req):
    """Returns a string containing text with a response to the user
    with the weather forecast or a prompt for more information
    Takes the city for the forecast and (optional) dates
    uses the template responses found in weather_responses.py as templates
    """
    parameters = req['queryResult']['parameters']

    print('Dialogflow Parameters:')
    print(json.dumps(parameters, indent=4))

    response = requests.get(
        'https://rt.data.gov.hk/v1/transport/citybus-nwfb/route/NWFB/'+ parameters['bus_no']
        # ,
            # params=wwo_data
    )

    bus_data = response.json()['data']

    # error = bus_data.get('error')
    if bus_data:
        return bus_data['dest_en']
    else:
        response = requests.get(
        'https://rt.data.gov.hk/v1/transport/citybus-nwfb/route/CTB/'+ parameters['bus_no'])
        bus_data = response.json()['data']
        return bus_data['dest_en']
        
    # return response



# def get_dest(req):

#     # Get all the Query Parameter
#     query_response = req["queryResult"]
#     print('Query Response: ')
#     print(query_response)
#     text = query_response.get('queryText', None)
#     parameters = query_response.get('parameters', None)

#     res = get_data()

#     return res


# def get_data():

#     speech = "ng lun g ar dllm"

#     return {
#         "fulfillmentText": speech,
#     }


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    print ("Starting app on port %d" %(port))
    app.run(debug=True, port=port, host='0.0.0.0')