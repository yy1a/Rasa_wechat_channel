import http
import http.client
import json
import asyncio



async def rasa_server(content):
    '''
    input -- user's message, type: byte
    output -- rasa's reply, type: str
    '''

    connection = http.client.HTTPConnection('192.168.1.172:80') #IP address for rasa server
    values = {
    "sender": "Rasa",
    "message": content.decode("utf-8")
    #"message": content
    }
    json_foo = json.dumps(values) #convert to json format
    connection.request('POST', '/webhooks/rest/webhook', json_foo)
    response = connection.getresponse()
    res = (response.read().decode("utf-8"))
    res = json.loads(res)

    # TO-DO: Multiple replies within one request; 
    # Currently http can only send one reply after user's request
    output = []
    for i in res:
        output.append(i)
    if not output:
        output = [{'text':'hello'}]
    return output
