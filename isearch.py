from flask import Flask, json, render_template
from flask_ask import Ask, statement, question, session, context

import requests
import logging
from datetime import datetime
#import unidecode
#import urllib2

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
#log = logging.getLogger('flask_ask').setLevel(logging.DEBUG)
log = logging.getLogger()

# Helpers

def get_people_results(firstName='', lastName=''):
    url_query = SOLR + PEOPLE_PATH + '?q=displayName:{} {}&rows={}&wt=json'.format(firstName, lastName.capitalize(), RESPONSE_SIZE)
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
    out += '\n\n{}'.format(record.get('primaryTitle', ''))
    out += '\n{}'.format(record.get('primaryiSearchDepartmentAffiliation', ''))
    out += '\n{}'.format(record.get('emailAddress', ''))
    out += '\n{}'.format(record.get('phone', ''))
    out += '\n{}'.format(record.get('primaryMailcode', ''))
    return out

def get_people_results_card_photo_url(record):

    out = '{}'.format(record.get('photoUrl', ''))
    return out

# Session starter
#
# This intent is fired automatically at the point of launch (= when the session starts).
# Use it to register a state machine for things you want to keep track of, such as what the last intent was, so as to be
# able to give contextual help.
@ask.on_session_started
def start_session():
    """
    Fired at the start of the session, this is a great place to initialise state variables and the like.
    """
    logging.debug("Session started at {}".format(datetime.now().isoformat()))


# Launch intent
#
# This intent is fired automatically at the point of launch.
# Use it as a way to introduce your Skill and say hello to the user. If you envisage your Skill to work using the
# one-shot paradigm (i.e. the invocation statement contains all the parameters that are required for returning the
# result).
@ask.launch  # User starts skill without any intent.
def launch():
    """
    (QUESTION) Responds to the launch of the Skill with a welcome statement and a card.
    Templates:
    * Initial statement: 'welcome'
    * Reprompt statement: 'welcome_re'
    * Card title: 'ASU iSearch Directory'
    * Card body: 'welcome_card'
    """
    welcome_text = render_template('welcome')
    welcome_re_text = render_template('welcome_re')
    welcome_card_text = render_template('welcome_card')

    welcome_title = 'ASU iSearch Directory'

    out = question(welcome_text)\
        .reprompt(welcome_re_text)\
        .standard_card(title=welcome_title, text=welcome_card_text)
    # If Show.
    if context.System.device.supportedInterfaces.Display:
        out.display_render(template='BodyTemplate1', title=welcome_title, token=None, text=None, backButton='HIDDEN',
        background_image_url="https://s3.amazonaws.com/asu.amazonecho/asu_directory_images/ASU_Echo_Show_Background_Image_1.jpg")

    return out

@ask.intent('iSearchIntentPeopleFirst')
def get_first_isearch_people_results(firstName, lastName):
    """
    (QUESTION) Responds to the launch of the Skill with a welcome statement and a card.
    Templates:
    * Initial statement: 'welcome'
    * Reprompt statement: 'welcome_re'
    * Card title: 'Arizona HQ2'
    * Card body: 'welcome_card'
    """

    reprompt_text = render_template('welcome_re')

    # TODO some of this to go to template and majority of this will just be the return
    # TODO map "more" and "next" to more results intent, not just "yes"

    reprompt_text = reprompt_text

    if firstName or lastName:
        results = get_people_results(firstName, lastName)
    else:
        return statement("{}".format(reprompt_text))

    no_results_response = "I didn't find any results for {} {}.".format(firstName, lastName.capitalize())
    if results == None:
        return statement("{}".format(no_results_response))
    if len(results) < 1:
        return statement("{}".format(no_results_response))

    speech_output = "For search {} {} ... \n".format(firstName, lastName.capitalize())
    card_title = "Results for {} {}".format(firstName, lastName.capitalize())
    card_output = ""
    card_photo = ""
    range_value = PAGINATION_SIZE if len(results) >= PAGINATION_SIZE else len(results)
    for i in range(range_value):
        speech_output += get_people_results_output(results[i])
        card_output += get_people_results_card(results[i])
        card_photo += get_people_results_card_photo_url(results[i])
    speech_output += " Would you like more results?"
    session.attributes[SESSION_INDEX] = PAGINATION_SIZE + 1
    session.attributes[SESSION_TEXT] = results
    session.attributes[SESSION_SLOT_FIRSTNAME] = firstName
    session.attributes[SESSION_SLOT_LASTNAME] = lastName

    # CORS enabled photo for testing
    #card_photo='https://i.imgur.com/hYQzVO3.jpg'
    # Attempt at using urllib2 to open the data and read it into variable. FAILS due to expected HTTPS.
    #photo_data = urllib2.urlopen('https://webapp4.asu.edu/photo-ws/directory_photo/cors/mcrow')
    #card_photo = 'data:image/jpeg;base64,' + photo_data.read()

    if len(card_photo) > 0:

        out = question("{}".format(speech_output)) \
            .reprompt(reprompt_text) \
            .standard_card(title=card_title, text=card_output)
        # If Show.
        if context.System.device.supportedInterfaces.Display:
            out.display_render(template='BodyTemplate3', title=card_title, token=None, text={
                'primaryText': {
                    'type': "PlainText",
                    'text': card_output
                }
            }, backButton='VISIBLE', image=card_photo + '?size=large',
            #background_image_url="https://s3.amazonaws.com/asu.amazonecho/asu_directory_images/background-4.png")
            background_image_url="https://s3.amazonaws.com/asu.amazonecho/asu_directory_images/background_image_girl_dark.png")

        return out

    else:
        out = question("{}".format(speech_output)) \
            .reprompt(reprompt_text) \
            .simple_card(title=card_title, content=card_output)
        # If Show.
        if context.System.device.supportedInterfaces.Display:
            out.display_render(template='BodyTemplate3', title=card_title, token=None, text={
                'primaryText': {
                    'type': "PlainText",
                    'text': card_output
                }
            }, backButton='VISIBLE',
            #background_image_url="https://s3.amazonaws.com/asu.amazonecho/asu_directory_images/background-4.png")
            background_image_url="https://s3.amazonaws.com/asu.amazonecho/asu_directory_images/background_image_girl_dark.png")

        return out


@ask.intent('iSearchIntentPeopleRepeat')
def get_repeat_isearch_people_results():
    return get_next_isearch_people_results(repeat=True)

@ask.intent('iSearchIntentPeopleNext')
def get_next_isearch_people_results(repeat=None):
    results = session.attributes[SESSION_TEXT]
    if (repeat):
        index = session.attributes[SESSION_INDEX] - 1
    else:
        index = session.attributes[SESSION_INDEX]
    firstName = session.attributes[SESSION_SLOT_FIRSTNAME]
    lastName = session.attributes[SESSION_SLOT_LASTNAME]

    speech_output = "For {} {} in people ... \n".format(firstName, lastName.capitalize())
    card_title = "More results for {} {} in people".format(firstName, lastName.capitalize())
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
            card_photo += get_people_results_card_photo_url(results[index])
            i += 1
            index += 1
        speech_output += " For more results say yes. To hear again, say repeat. Otherwise say quit."
        reprompt_text = "Do you want to hear more results?"

    session.attributes[SESSION_INDEX] = index
    session.attributes[SESSION_SLOT_FIRSTNAME] = firstName
    session.attributes[SESSION_SLOT_LASTNAME] = lastName

    if len(card_photo) > 0:

        out = question("{}".format(speech_output)) \
            .reprompt(reprompt_text) \
            .standard_card(title=card_title, text=card_output)
        # If Show.
        if context.System.device.supportedInterfaces.Display:
           out.display_render(template='BodyTemplate3', title=card_title, token=None, text={
           'primaryText': {
               'type': "PlainText",
               'text': card_output
           }
        }, backButton='VISIBLE', image=card_photo + '?size=large',
        #background_image_url="https://s3.amazonaws.com/asu.amazonecho/asu_directory_images/background-4.png")
        background_image_url="https://s3.amazonaws.com/asu.amazonecho/asu_directory_images/background_image_girl_dark.png")

        return out

    else:
        out = question("{}".format(speech_output)) \
            .reprompt(reprompt_text) \
            .simple_card(title=card_title, content=card_output)
        # If Show.
        if context.System.device.supportedInterfaces.Display:
            out.display_render(template='BodyTemplate3', title=card_title, token=None, text={
            'primaryText': {
                'type': "PlainText",
                'text': card_output
            }
        }, backButton='VISIBLE',
        #background_image_url="https://s3.amazonaws.com/asu.amazonecho/asu_directory_images/background-4.png")
        background_image_url="https://s3.amazonaws.com/asu.amazonecho/asu_directory_images/background_image_girl_dark.png")

        return out

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

@ask.intent('AMAZON.NavigateSettingsIntent')
def handle_navigate_settings():
    """
    (?) Handles the 'navigate settings' built-in intention.
    """
    pass

@ask.intent('AMAZON.MoreIntent')
def handle_more():
    """
    (?) Handles the 'more' built-in intention.
    """
    pass

@ask.intent('AMAZON.NextIntent')
def handle_next():
    """
    (?) Handles the 'next' built-in intention.
    """
    pass

@ask.intent('AMAZON.PageDownIntent')
def handle_page_down():
    """
    (?) Handles the 'page down' built-in intention.
    """
    pass

@ask.intent('AMAZON.PageUpIntent')
def handle_page_up():
    """
    (?) Handles the 'page up' built-in intention.
    """
    pass

@ask.intent('AMAZON.NoIntent')
def handle_no():
    """
    (?) Handles the 'no' built-in intention.
    """
    pass

@ask.intent('AMAZON.YesIntent')
def handle_yes():
    """
    (?) Handles the 'yes'  built-in intention.
    """
    pass

@ask.intent('AMAZON.PreviousIntent')
def handle_back():
    """
    (?) Handles the 'go back!'  built-in intention.
    """
    pass

@ask.intent('AMAZON.StartOverIntent')
def start_over():
    """
    (QUESTION) Handles the 'start over!'  built-in intention.
    """
    pass

@ask.session_ended
def session_ended():
    """
    Returns an empty for `session_ended`.
    .. warning::
    The status of this is somewhat controversial. The `official documentation`_ states that you cannot return a response
    to ``SessionEndedRequest``. However, if it only returns a ``200/OK``, the quit utterance (which is a default test
    utterance!) will return an error and the skill will not validate.
    """
    # return "{}", 200
    return statement("")

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
