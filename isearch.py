from flask import Flask
from flask_ask import Ask, statement, question, session

import requests
#import json
#import time
#import unidecode
import logging

# DEBUGGING
# import pdb

# Params
SOLR = 'https://asudir-solr.asu.edu/asudir/'
# Example people query:
# https://asudir-solr.asu.edu/asudir/directory/select?q=firstName:michael+lastName:crow&rows=3&wt=json
PEOPLE_PATH = 'directory/select'
# Example department query:
# https://asudir-solr.asu.edu/asudir/asu_departments/select?q=uto&rows=3&wt=json
DEPT_PATH = 'asu_departments/select'

# Constant defining session attribute key for the event index
SESSION_INDEX = 'index'

# Constant defining session attribute key for the event test key
SESSION_TEXT = 'text'
SESSION_SLOT_FIRSTNAME = 'slot_firstname'
SESSION_SLOT_LASTNAME = 'slot_lastname'
SESSION_SLOT_DEPTNAME = 'slot_deptname'

RESPONSE_SIZE = 15
PAGINATION_SIZE = 1

# Define the Flask app.
app = Flask(__name__)
ask = Ask(app, "/directory")
log = logging.getLogger('flask_ask').setLevel(logging.DEBUG)

# Helpers

def get_people_results(firstName='', lastName=''):
    url_query = SOLR + PEOPLE_PATH + '?q=displayName:{} {}&rows={}&wt=json'.format(firstName, lastName, RESPONSE_SIZE)
    resp = requests.get(url_query)

    if resp.status_code == 200:
        records = resp.json()  # dict datatype
        results = []
        for item in records['response']['docs']:
            record = {
                'firstName': item.get('firstName', ''),
                'lastName': item.get('lastName', ''),
                'displayName': item.get('displayName', ''),
                'primaryTitle': item.get('primaryTitle', ''),
                'primaryiSearchDepartmentAffiliation': item.get('primaryiSearchDepartmentAffiliation', ''),
                'emailAddress': item.get('emailAddress', ''),
                'phone': item.get('phone', ''),
                'primaryMailcode': item.get('primaryMailcode', ''),
                'photoUrl': item.get('photoUrl', '')
            }
            results.append(record)
        return results

    else:
        return "There as a problem querying the people directory."

def get_people_results_output(record):

    # out = record['firstName'] + ' ' + record['lastName'] + ', '
    out = record.get('displayName', '')
    out += ',,,Title:,, ' + record.get('primaryTitle') if record.get('primaryTitle') else ''
    out += ',,,Department:,, ' + record.get('primaryiSearchDepartmentAffiliation') if record.get('primaryiSearchDepartmentAffiliation') else ''
    out += ',,,Email address:,, ' + record.get('emailAddress') if record.get('emailAddress') else ''
    out += ',,,Phone:,, ' + record.get('phone') if record.get('phone') else ''
    # out += ',,,Phone:,, <say-as interpret-as="telephone">' + record.get('phone') + '</say-as>' if record.get('phone') else ''
    out += ',,,Mail code:,, ' + record.get('primaryMailcode') if record.get('primaryMailcode') else ''
    # out += ',,,Mail code:,, <say-as interpret-as="digits">' + record.get('primaryMailcode') + '</say-as>' if record.get('primaryMailcode') else ''
    return out

def get_people_results_card(record):

    # out = record['firstName'] + ' ' + record['lastName'] + ', '
    out = '{}'.format(record.get('displayName', ''))
    out += '\n{}'.format(record.get('primaryTitle', ''))
    out += '\n{}'.format(record.get('primaryiSearchDepartmentAffiliation', ''))
    out += '\n{}'.format(record.get('emailAddress', ''))
    out += '\n{}'.format(record.get('phone', ''))
    out += '\n{}'.format(record.get('primaryMailcode', ''))
    return out

def get_people_results_card_photo_url(record):

    out = '{}'.format(record.get('photoUrl', ''))
    return out

@ask.launch  # User starts skill without any intent.
def launch():
    welcome_message = 'Welcome to the ASU I Search Directory. Search people by saying something like "ask ASU directory to find Michael Crow."'
    return statement("{}".format(welcome_message))

@ask.intent('iSearchIntentPeopleFirst')
def get_first_isearch_people_results(firstName, lastName):
    reprompt_text = 'To search the ASU I Search Directory for a person, try asking something like "find Michael Crow"'
    if firstName or lastName:
        results = get_people_results(firstName, lastName)
    else:
        return statement("{}".format(reprompt_text))

    no_results_response = "I didn't find any results for {} {}.".format(firstName, lastName)
    if results == None:
        return statement("{}".format(no_results_response))
    if len(results) < 1:
        return statement("{}".format(no_results_response))

    speech_output = "For search {} {}\n".format(firstName, lastName)
    card_title = "Results for {} {}".format(firstName, lastName)
    card_output = ""
    card_photo = ""
    range_value = PAGINATION_SIZE if len(results) >= PAGINATION_SIZE else len(results)
    for i in range(range_value):
        speech_output += get_people_results_output(results[i])
        card_output += get_people_results_card(results[i])
        # TODO uncomment when CORS is enabled.
        #card_photo += get_people_results_card_photo_url(results[i])
    speech_output += " Would you like more results?"
    session.attributes[SESSION_INDEX] = PAGINATION_SIZE + 1
    session.attributes[SESSION_TEXT] = results
    session.attributes[SESSION_SLOT_FIRSTNAME] = firstName
    session.attributes[SESSION_SLOT_LASTNAME] = lastName

    # CORS enabled photo for testing
    #card_photo='https://i.imgur.com/hYQzVO3.jpg'

    if len(card_photo) > 0:
        # TODO issue with CORS for images?
        # See "Hosting the Images" on https://developer.amazon.com/public/solutions/alexa/alexa-skills-kit/docs/providing-home-cards-for-the-amazon-alexa-app

        return question("{}".format(speech_output)) \
            .reprompt(reprompt_text) \
            .standard_card(title=card_title,
                           text=card_output,
                           small_image_url=card_photo + '?size=small',
                           large_image_url=card_photo + '?size=large')
    else:
        return question("{}".format(speech_output)) \
            .reprompt(reprompt_text) \
            .simple_card(title=card_title,
                         content=card_output)

@ask.intent('iSearchIntentPeopleNext')
def get_next_isearch_people_results():
    results = session.attributes[SESSION_TEXT]
    index = session.attributes[SESSION_INDEX]
    firstName = session.attributes[SESSION_SLOT_FIRSTNAME]
    lastName = session.attributes[SESSION_SLOT_LASTNAME]

    speech_output = "For {} {} in people\n".format(firstName, lastName)
    card_title = "More results for {} {} in people".format(firstName, lastName)
    card_output = ""
    card_photo = ""
    i = 0
    if index >= len(results):
        speech_output += " End of results."
        return statement("{}".format(speech_output))

    else:
        while i < PAGINATION_SIZE and index < len(results):
            speech_output += get_people_results_output(results[index])
            card_output += get_people_results_card(results[index])
            # TODO uncomment when CORS is enabled.
            #card_photo += get_people_results_card(results[i])
            i += 1
            index += 1
        speech_output += " For more results say yes. Otherwise say quit."
        reprompt_text = "Do you want to hear more results?"

    session.attributes[SESSION_INDEX] = index
    session.attributes[SESSION_SLOT_FIRSTNAME] = firstName
    session.attributes[SESSION_SLOT_LASTNAME] = lastName

    if len(card_photo) > 0:
        return question('{}'.format(speech_output)) \
            .reprompt(reprompt_text) \
            .standard_card(title=card_title,
                           text=card_output,
                           small_image_url=card_photo + '?size=small',
                           large_image_url=card_photo + '?size=large')
    else:
        return question('{}'.format(speech_output)) \
            .reprompt(reprompt_text) \
            .simple_card(title=card_title,
                         content=card_output)

@ask.intent('AMAZON.StopIntent')
def stop():
    return statement("Goodbye")

@ask.intent('AMAZON.CancelIntent')
def cancel():
    return statement("Goodbye")

@ask.intent('AMAZON.HelpIntent')
def help():
    # Use same as launch.
    return launch()

@ask.session_ended
def session_ended():
    return "{}", 200

if __name__ == '__main__':
    app.run(debug=True)


# NOTES
#
# To run locally, use ngrok:
# $ ngrok http 5000
# Will give an http and https forwarding address. Amazon will want https value when you configure the Alexa skill.
# Go to developer.amazon.com to create a new Alexa skill.
# Use https endpoint option, and subdomain SSL option in settings.
# Start both ngrok (as above) and this script:
# $ python isearch.py
# Then you can test it in the console, or with an Alexa device linked to the development account.
