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
SESSION_SLOT_SEARCH_TYPE = 'slot_search_type'
SESSION_SLOT_NAME = 'slot_name'

RESPONSE_SIZE = 15
PAGINATION_SIZE = 3

# Define the Flask app.
app = Flask (__name__)
ask = Ask(app, "/isearchSkill")
log = logging.getLogger('flask_ask').setLevel(logging.DEBUG)

# Helpers

def get_people_results(searchName):
    #url_query = SOLR + PEOPLE_PATH + '?q=firstName:{}+lastName:{}&rows={}&wt=json'.format(first, last, PEOPLE_LIMIT)
    url_query = SOLR + PEOPLE_PATH + '?q=displayName:{}&rows={}&wt=json'.format(searchName, RESPONSE_SIZE)
    resp = requests.get(url_query)

    if resp.status_code == 200:
        records = resp.json()  # dict datatype
        results = ''
        for item in records['response']['docs']:
            # TODO numbering and caching
            # TODO card
            result_name = item['firstName'] + ' ' + item['lastName'] + '... '
            results = results + result_name
        return results

    else:
        return "There as a problem querying the people directory."

def get_dept_results(searchName):
    url_query = SOLR + DEPT_PATH + '?q={}&rows={}&wt=json'.format(searchName, RESPONSE_SIZE)
    resp = requests.get(url_query)

    if resp.status_code == 200:
        records = resp.json()  # dict datatype
        results = ''
        for item in records['response']['docs']:
            # TODO determine what we want to share about dept.
            # Is this dept centered, or a jumping off point to identifying individuals in the dept?
            # TODO numbering and caching
            # TODO card
            result_name = item['tm_title'][0] + '... '
            results = results + result_name
        return results

    else:
        return "There as a problem querying the department directory."

# DEBUG uncomment to test
# peeps = get_people_results('michael smith')
# print(peeps)
# depts = get_dept_results('uto')
# print(depts)


# TODO
# Can we use Flask caching for results within Flask-ask? http://flask.pocoo.org/docs/0.12/patterns/caching/


@ask.launch  # User starts skill without any intent.
def launch():
    welcome_message = "Welcome to the ASU iSearch Directory. Search people by saying something like 'search Michael Crow in people.' To search departments use the following example 'search Registrar in departments.'"
    return statement(welcome_message)


# Dialog Delegation collects iSearchType and searchName

# To use the dialog model from skill builder's prompts and utterances, return the Dialog.Delegate directive in your
# skill's response.
# More https://developer.amazon.com/public/solutions/alexa/alexa-skills-kit/docs/dialog-interface-reference

@ask.intent('iSearchIntentFirst')
def get_first_isearch_results(iSearchType, searchName):
    reprompt_text = "With the ASU iSearch directory, you can search people and departments at ASU. " + \
                    "Just tell me whether you want to search for a person or department and then the name."
    if (iSearchType == 'people' and searchName):
        # TODO if no results
        results = get_people_results(searchName)
    elif (iSearchType == 'department' and searchName):
        # TODO if no results
        results = get_dept_results(searchName)
    else:
        return statement(reprompt_text)
    card_title = "Results for {} in {}".format(searchName, iSearchType)
    speech_output = "<p>For {} in {}</p>".format(searchName, iSearchType)
    card_output = ""
    for i in range (PAGINATION_SIZE):
        speech_output += "<p>{}</p>".format(results[i])
        card_output += "{}\n".format(results[i])
    speech_output += " Would you like more results?"
    card_output += " Would you like more results?"
    session.attributes[SESSION_INDEX] = PAGINATION_SIZE
    session.attributes[SESSION_TEXT] = results
    session.attributes[SESSION_SLOT_SEARCH_TYPE] = iSearchType
    session.attributes[SESSION_SLOT_NAME] = searchName
    speech_output = '<speak>{}</speak>'.format(speech_output)
    return question(speech_output).reprompt(reprompt_text).simple_card(card_title, card_output)

@ask.intent('iSearchIntentNext')
def get_next_isearch_results():
    results = session.attributes[SESSION_TEXT]
    index = session.attributes[SESSION_INDEX]
    searchName = session.attributes[SESSION_SLOT_NAME]
    iSearchType = session.attributes[SESSION_SLOT_SEARCH_TYPE]

    card_title = "More results for {} in {}".format(searchName, iSearchType)
    speech_output = "<p>For {} in {}</p>".format(searchName, iSearchType)
    card_output = ""
    i = 0
    while i < PAGINATION_SIZE and index < len(results):
        speech_output += "<p>{}</p>".format(results[index])
        card_output += "{}\n".format(results[index])
        i += 1
        index += 1
    speech_output += " Would you like more results?"
    card_output += " Would you like more results?"
    reprompt_text = "Do you want to hear more results?"
    session.attributes[SESSION_INDEX] = index
    session.attributes[SESSION_SLOT_SEARCH_TYPE] = iSearchType
    session.attributes[SESSION_SLOT_NAME] = searchName
    speech_output = '<speak>{}</speak>'.format(speech_output)
    return question(speech_output).reprompt(reprompt_text)


# TODO break people and dept search into separate utterances -> intent. Let Alexa handle routing logic based on utterances.


@ask.intent('AMAZON.StopIntent')
def stop():
    return statement("Goodbye")

@ask.intent('AMAZON.CancelIntent')
def cancel():
    return statement("Goodbye")

@ask.intent('AMAZON.HelpIntent')
def help():
    help_text = "With the ASU iSearch directory, you can search people and departments at ASU. " + \
                "Just tell me whether you want to search for a person or department and then the name."
    return statement(help_text)

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
