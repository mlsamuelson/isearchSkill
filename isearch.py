from flask import Flask
from flask_ask import Ask, statement, question, session

import json
import requests
import time
import unidecode
import logging


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
    # url_query = SOLR + PEOPLE_PATH + '?q=firstName:{}+lastName:{}&rows={}&wt=json'.format(first, last, PEOPLE_LIMIT)
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

# DEBUG uncomment to test
# peeps = get_people_results('michael smith')
# print(peeps)
# depts = get_dept_results('uto')
# print(depts)

def get_people_results_output(record):

    # out = record['firstName'] + ' ' + record['lastName'] + ', '
    out = record.get('displayName', '')
    out += ',,Title: ' + record.get('primaryTitle', '')
    out += ',,Department: ' + record.get('primaryiSearchDepartmentAffiliation', '')
    out += ',,Email address: ' + record.get('emailAddress', '')
    out += ',,Phone: <say-as interpret-as="telephone">' + record.get('phone', '') + '</say-as>'  # say-as telephone
    out += ',,Mail code: <say-as interpret-as="digits">' + record.get('primaryMailcode', '') + '</say-as>'  # say-as digits
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

# TODO
# Can we use Flask caching for results within Flask-ask? http://flask.pocoo.org/docs/0.12/patterns/caching/


@ask.launch  # User starts skill without any intent.
def launch():
    welcome_message = '<speak>Welcome to the <say-as interpret-as="spell-out">ASU</say-as> iSearch Directory. Search people by saying something like "ask directory to find Michael Crow."</speak> '  # \
    #                  "To search departments try 'search department Registrar.'"
    return statement(welcome_message)

"""
We break people and dept search into separate utterances -> intent. It simplifies things to let Alexa handle 
routing logic based on utterances, vs. us rourting based on slot values in utterances.
"""

# TODO details page -> do just one at a time and step one at a time?
# TODO integrate depts search and resolve the overlapping "next" utterance issue.

# TODO Jinja templating?

# TODO Need none-found response

@ask.intent('iSearchIntentPeopleFirst')
def get_first_isearch_people_results(firstName, lastName):
    reprompt_text = '<speak>To search the <say-as interpret-as="spell-out">ASU</say-as> iSearch Directory for a person, try asking something like "find Michael Crow"</speak>'
    if (firstName or lastName):
        results = get_people_results(firstName, lastName)
    else:
        return statement(reprompt_text)
    if (results == None):
        return statement(reprompt_text)
    # TODO separate formatting better
    speech_output = "For {} {} in people".format(firstName, lastName)  # Start speech string.
    card_title = "Results for {} {} in people".format(firstName, lastName)
    card_output = ""
    card_photo = ""
    print('results')
    print(results)
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
    speech_output = "<speak>{}</speak>".format(speech_output)

    # CORS enabled photo for testing
    #card_photo='https://i.imgur.com/hYQzVO3.jpg'

    if len(card_photo) > 0:
        # TODO issue with CORS for images?
        # See "Hosting the Images" on https://developer.amazon.com/public/solutions/alexa/alexa-skills-kit/docs/providing-home-cards-for-the-amazon-alexa-app

        # TODO better guarding against missing data bits/errors.
        return question(speech_output) \
            .reprompt(reprompt_text) \
            .standard_card(title=card_title,
                           text=card_output,
                           small_image_url=card_photo + '?size=small',
                           large_image_url=card_photo + '?size=large')
    else:
        return question(speech_output) \
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
    # TODO Fix how we iterate, so this works correctly.
    i = 0
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
    speech_output = '<speak>{}</speak>'.format(speech_output)
    # return question(speech_output).reprompt(reprompt_text).simple_card(card_title, card_output)
    if len(card_photo) > 0:
        return question(speech_output) \
            .reprompt(reprompt_text) \
            .standard_card(title=card_title,
                           text=card_output,
                           small_image_url=card_photo + '?size=small',
                           large_image_url=card_photo + '?size=large')
    else:
        return question(speech_output) \
            .reprompt(reprompt_text) \
            .simple_card(title=card_title,
                         content=card_output)


"""
# Idea for doing dispatch between two types of next...
@ask.intent('iSearchIntentResultNext')
def get_next_isearch_next_results():
    results = session.attributes[SESSION_TEXT]
    index = session.attributes[SESSION_INDEX]

    # Based on session attributes, we can determine state
    firstName = session.attributes[SESSION_SLOT_FIRSTNAME]
    lastName = session.attributes[SESSION_SLOT_LASTNAME]
    deptName = session.attributes[SESSION_SLOT_DEPTNAME]

    if (deptName):
        return get_next_isearch_dept_results()
    elif(firstName or lastName):
        return get_next_isearch_people_results()

    return question(speech_output).reprompt(reprompt_text).simple_card(card_title, card_output)

@ask.intent('iSearchIntentDeptFirst')
def get_first_isearch_dept_results(deptName):
    reprompt_text = "To search the ASU iSearch Directory for a department, try asking something like 'find department Registrar'"
    if (deptName):
        results = get_dept_results(deptName)
    else:
        return statement(reprompt_text)
    if (results == None):
        return statement(reprompt_text)
    # DEBUG
    #print('-----------')
    #print(results)
    #print('-----------')
    card_title = "Department results for {}".format(deptName)
    speech_output = "For {}".format(deptName)
    card_output = ""
    range_value = PAGINATION_SIZE if len(results) >= PAGINATION_SIZE else len(results)
    for i in range(range_value):
        speech_output += "{}".format(results[i])
        card_output += "{}\n".format(results[i])
    speech_output += " Would you like more results?"
    card_output += " Would you like more results?"
    session.attributes[SESSION_INDEX] = PAGINATION_SIZE
    session.attributes[SESSION_TEXT] = results
    session.attributes[SESSION_SLOT_DEPTNAME] = deptName
    speech_output = '{}'.format(speech_output)
    return question(speech_output).reprompt(reprompt_text).simple_card(card_title, card_output)

#@ask.intent('iSearchIntentDeptNext')
def get_next_isearch_dept_results():
    results = session.attributes[SESSION_TEXT]
    index = session.attributes[SESSION_INDEX]
    deptName = session.attributes[SESSION_SLOT_DEPTNAME]

    card_title = "More department results for {}".format(deptName)
    speech_output = "For {}".format(deptName)
    card_output = ""
    i = 0
    while i < PAGINATION_SIZE and index < len(results):
        speech_output += "{}".format(results[index])
        card_output += "{}\n".format(results[index])
        i += 1
        index += 1
    speech_output += " Would you like more results?"
    card_output += " Would you like more results?"
    reprompt_text = "Do you want to hear more results?"
    session.attributes[SESSION_INDEX] = index
    session.attributes[SESSION_SLOT_DEPTNAME] = deptName
    speech_output = '{}'.format(speech_output)
    return question(speech_output).reprompt(reprompt_text)
"""

@ask.intent('AMAZON.StopIntent')
def stop():
    return statement("Goodbye")

@ask.intent('AMAZON.CancelIntent')
def cancel():
    return statement("Goodbye")

@ask.intent('AMAZON.HelpIntent')
def help():
    #help_text = "With the ASU iSearch directory, you can search people and departments at ASU. " + \
    #            "Just tell me whether you want to search for a person or department and then the name."
    return launch()

@ask.session_ended
def session_ended():
    return "{}", 200

"""
@ask.intent("PeopleFound")
def people_found():
    # TODO add slots...
    people = get_people_results()
    people_msg = 'I found {}'.format(people)
    return statement(people_msg)

@ask.intent("DepartmentsFound")
def departments_found():
    bye_text = 'Not sure what you want then. Bye.'
    return statement(bye_text)
"""


if __name__ == '__main__':
    app.run(debug=True)
    #app.run()




# NOTES
#
# To run, use ngrok:
# $ ngrok http 5000
# Will give an http and https forwarding address. Amazon will want https value when you configure the Alexa skill.
# Go to developer.amazon.com to create a new Alexa skill.
# Use https endpoint option, and subdomain SSL option in settings.
# Start both ngrok (as above) and this script:
# $ python redditreader.py
# Then you can test it in the console, or with an Alexa device linked to the development account.


# TODO
# watch videos on Flask
# more flask-ask
# zappa


