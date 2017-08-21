import os
import sys
import json

import requests
from flask import Flask, request
from xml.etree import ElementTree
import copy

app = Flask(__name__)


@app.route('/', methods=['GET'])
def verify():
    # when the endpoint is registered as a webhook, it must echo back
    # the 'hub.challenge' value it receives in the query arguments
    if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.challenge"):
        if not request.args.get("hub.verify_token") == os.environ["VERIFY_TOKEN"]:
            return "Verification token mismatch", 403
        return request.args["hub.challenge"], 200

    return "Hello world", 200


@app.route('/', methods=['POST'])
def webhook():

    # endpoint for processing incoming messaging events

    data = request.get_json()
    log(data)  # you may not want to log every incoming message in production, but it's good for testing

    if data["object"] == "page":

        for entry in data["entry"]:
            for messaging_event in entry["messaging"]:

                if messaging_event.get("message"):  # someone sent us a message

                    sender_id = messaging_event["sender"]["id"]        # the facebook ID of the person sending you the message
                    recipient_id = messaging_event["recipient"]["id"]  # the recipient's ID, which should be your page's facebook ID
                    message_text = messaging_event["message"]["text"]  # the message's text

                    send_message(sender_id, message_text)

                if messaging_event.get("delivery"):  # delivery confirmation
                    pass

                if messaging_event.get("optin"):  # optin confirmation
                    pass

                if messaging_event.get("postback"):  # user clicked/tapped "postback" button in earlier message
                    pass

    return "ok", 200


def send_message(recipient_id, message_text):
    log("MESSAGE_TEST")
    log(message_text)

    weartherData = requests.get("http://www.ilmateenistus.ee/ilma_andmed/xml/maailma_linnad.php")
    root = ElementTree.fromstring(weartherData.content);

    cardTemplate = {
                       "title": "",
                       "subtitle": "",
                       "image_url": "",
                       "buttons": [{
                           "type": "web_url",
                           "url": "",
                           "title": ""
                       }],
                   };

    response = {
        "attachment": {
            "type": "template",
            "payload": {
                "template_type": "generic",
                "elements": []
            }
        }
    };

    for country in root.findall('station'):
        nameEst = country.find('name_est').text
        nameEng = country.find('name_eng').text

        if nameEng.lower() in message_text.lower() or nameEst.lower() in message_text.lower():
            template = copy.deepcopy(cardTemplate);

            template["title"] = nameEng;

            temperatureElement = country.find('temperature')
            temperature = valueFromElement(temperatureElement)
            temperatureUnit = temperatureElement.get('units')

            rainfallElement = country.find('precipitations')
            rainfall = valueFromElement(rainfallElement)
            rainfallUnit = rainfallElement.get('units')

            windElement = country.find('wind');
            wind = valueFromElement(windElement)
            windUnit = windElement.get('units')

            template["subtitle"] = "Temperature " + temperature + temperatureUnit + ", rainfall " + rainfall + rainfallUnit + ", wind " + wind + windUnit;

            template["image_url"] = "https://placeholdit.co/i/500x250";
            template["buttons"][0]["url"] = "http://www.google.com/search?q=" + nameEng;
            template["buttons"][0]["title"] = nameEng;

            response["attachment"]["payload"]["elements"].append(template);

    log("RESPONSE")
    log(response)
    log("END RESPONSE")

    log("sending message to {recipient}: {text}".format(recipient=recipient_id, text=message_text))

    params = {
        "access_token": os.environ["PAGE_ACCESS_TOKEN"]
    }
    headers = {
        "Content-Type": "application/json"
    }

    data = json.dumps({
        "recipient": {
            "id": recipient_id
        },
        "message": {
            "text": "Could not find the requested city"
        }
    })

    if len(response["attachment"]["payload"]["elements"]) > 0:
        data = json.dumps({
            "recipient": {
                "id": recipient_id
            },
            "message": response
        })

    r = requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers, data=data)
    if r.status_code != 200:
        log(r.status_code)
        log(r.text)

def valueFromElement(element):
    if element.text is None:
        return 0
    else:
        return element.text

def log(message):  # simple wrapper for logging to stdout on heroku
    print str(message)
    sys.stdout.flush()


if __name__ == '__main__':
    app.run(debug=True)
