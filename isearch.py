from flask import Flask, json, render_template
from flask_ask import Ask, statement, question, session, context, delegate, request

import requests
import logging
from datetime import datetime
from xml.sax.saxutils import escape, unescape

# DEBUGGING
# import pdb

# Params
SOLR = 'https://asudir-solr.asu.edu/asudir/'
# Example people query:
# https://asudir-solr.asu.edu/asudir/directory/select?q=firstName:michael+lastName:crow&rows=3&wt=json
# Example title query (with debugs left in for reference):
# https://asudir-solr.asu.edu/asudir/directory/select?defType=edismax&q=chiefinformation officer analytics&q.op=AND&qf=primaryTitle%5E200.0%20titles%20primaryDepartment%5E100.0%20departments%20bio&pf=primaryTitle%5E20.0&bq=primaryDepartment:"office%20of%20the%20president"^100.0&df=primaryTitle&wt=json&rows=100&debugQuery=true
PEOPLE_PATH = 'directory/select'
# Example department query:
# https://asudir-solr.asu.edu/asudir/asu_departments/select?q=uto&rows=3&wt=json
DEPT_PATH = 'asu_departments/select'

# Constant defining session attribute key for the event index
SESSION_INDEX = 'index'

# Constant defining session attribute key for the event text key
SESSION_RESULTS = 'results'
SESSION_SLOT_FIRSTNAME = 'slot_firstname'
SESSION_SLOT_LASTNAME = 'slot_lastname'
SESSION_SLOT_DEPTNAME = 'slot_deptname'
SESSION_SLOT_TITLE_SEARCH_PHRASE = 'slot_title_search_phrase'

# When a search happens we'll set a context for use in results handling
# Use the initial intent's name as the context value.
SESSION_SEARCH_CONTEXT = 'search_context'

RESPONSE_SIZE = 20
PAGINATION_SIZE = 1

# Define the Flask app.
app = Flask(__name__)
ask = Ask(app, "/directory")
# log = logging.getLogger('flask_ask').setLevel(logging.DEBUG)
log = logging.getLogger()


# HELPERS

def get_people_results(firstName='', lastName=''):

    # Solr query.
    # Query allows for stemming and possibly phonemic matches on names. Also, while not optimized for title and bio
    # searches, this will hit those fields, so a query for "Chief Information Officer" is likely to return decent hits.
    # Boost hits on displayName by 20 and lastNameExact by 50, specify all fields to query (qf), and mark displayName
    # as a phrase field (pf).
    url_query = SOLR + PEOPLE_PATH + '?defType=edismax&q={}%20{}&qf=displayName%5E20.0%20firstName%20lastName%20lastNameExact%5E50.0%20primaryTitle%20primaryDepartment%20researchInterests&pf=displayName%5E20.0&rows={}&wt=json'.format(firstName, lastName.capitalize(), RESPONSE_SIZE)

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

    # Note, need to ensure escaping on values as & and other special characters will force this to be interpreted as
    # text instead of ssml.

    out = escape(record.get('displayName', ''))
    out += ' is ' + escape(record.get('primaryTitle')) if record.get('primaryTitle') else ''
    out += ' in  ' + escape(record.get('primaryiSearchDepartmentAffiliation')) if record.get('primaryiSearchDepartmentAffiliation') else ''
    out += '<break/> You can reach ' + escape(record.get('displayName', '')) + ' at ' if record.get('emailAddress') or record.get('phone') or record.get('primaryMailcode') else ''
    out += '<break/> the email <break/><prosody rate="slow"><say-as interpret-as="spell-out">' + escape(record.get('emailAddress')) + '</say-as></prosody>' if record.get('emailAddress') else '' # .replace('@asu.edu', ',at A S U dot E D U') if record.get('emailAddress') else ''
    out += '<break/> the phone number <break/> <say-as interpret-as="telephone">' + escape(record.get('phone')) + "</say-as>" if record.get('phone') else ''
    out += '<break/> the mail code <break/> ' + escape(record.get('primaryMailcode')) if record.get('primaryMailcode') else ''
    return out

# For Alexa app cards.
def get_people_results_card(record):

    out = '\n{}'.format(escape(record.get('displayName', ''))) if record.get('displayName') else ''
    out += '\n{}'.format(escape(record.get('primaryTitle', ''))) if record.get('primaryTitle') else ''
    out += '\n{}'.format(escape(record.get('primaryiSearchDepartmentAffiliation', ''))) if record.get('primaryiSearchDepartmentAffiliation') else ''
    out += '\n{}'.format(escape(record.get('emailAddress', ''))) if record.get('emailAddress') else ''
    out += '\n{}'.format(escape(record.get('phone', ''))) if record.get('phone') else ''
    out += '\n{}'.format(escape(record.get('primaryMailcode', ''))) if record.get('primaryMailcode') else ''
    return out

# For Show and related display.
def get_people_results_rich_output(record):

    out = '<br/><b>{}</b>'.format(escape(record.get('displayName', ''))) if record.get('displayName') else ''
    out += '<br/>{}'.format(escape(record.get('primaryTitle', ''))) if record.get('primaryTitle') else ''
    out += '<br/>{}'.format(escape(record.get('primaryiSearchDepartmentAffiliation', ''))) if record.get('primaryiSearchDepartmentAffiliation') else ''
    out += '<br/>{}'.format(escape(record.get('emailAddress', ''))) if record.get('emailAddress') else ''
    out += '<br/>{}'.format(escape(record.get('phone', ''))) if record.get('phone') else ''
    out += '<br/>{}'.format(escape(record.get('primaryMailcode', ''))) if record.get('primaryMailcode') else ''
    return out

def get_people_results_card_photo_url(record):

    out = '{}'.format(record.get('photoUrl', ''))
    return out


def get_title_results(titleSearchPhrase=''):

    # Solr title query with special boost for president in a bq (boost query).
    # bq prevents all the "President's Professors" and similar from pushing
    # the university president too far down into the results.
    url_query = SOLR + PEOPLE_PATH + '?defType=edismax&q={}&q.op=AND&qf=primaryTitle%5E200.0%20titles%20primaryDepartment%5E100.0%20departments%20bio&pf=primaryTitle%5E20.0&bq=primaryDepartment:"office%20of%20the%20president"^100.0&df=primaryTitle&rows={}&wt=json'.format(titleSearchPhrase, RESPONSE_SIZE)

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


# Dialog state, used in dialog.delegate scenarios.
# See https://stackoverflow.com/questions/48053778/how-to-create-conversational-skills-using-flask-ask-amazon-alexa-and-python-3-b/48209279
def get_dialog_state():

    return session['dialogState']


# INTENTS

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
    # logging.debug("INTENT: launch")
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
        out.display_render(
            template='BodyTemplate1',
            title=welcome_title,
            token=None,
            text=None,
            backButton='HIDDEN',
            background_image_url="https://s3.amazonaws.com/asu.amazonecho/asu_directory_images/ASU_Echo_Show_Background_Image_1.jpg"
        )

    return out

#
@ask.intent('iSearchIntentPeople')
def get_isearch_people_results(firstName, lastName):
    # logging.debug("INTENT: iSearchIntentPeople")
    """
    (QUESTION) Responds to name search.
    Templates:
    * Initial statement: dynamic response
    * Reprompt statement: 'welcome_re'
    * No results: 'no_results'
    * Results: 'people_results'
    * Card title: 'Results for [firstname] [lastname]...'
    * Card body: dynamic response 
    """

    # Set search context in the session. For eventual use in iSearchIntentItemDetail.
    # This is a key piece in search results handling.
    session.attributes[SESSION_SEARCH_CONTEXT] = 'iSearchIntentPeople'

    reprompt_text = render_template('welcome_re')

    if firstName or lastName:
        results = get_people_results(firstName, lastName)
    else:
        return statement("{}".format(reprompt_text))

    if results == None:
        return question("{}".format(render_template('no_results', search_phrase=firstName + ' ' + lastName.capitalize())))
    if len(results) < 1:
        return question("{}".format(render_template('no_results', search_phrase=firstName + ' ' + lastName.capitalize())))

    speech_output = "For search {} {} ... \n".format(firstName, lastName.capitalize())
    card_title = "Results for {} {}".format(firstName, lastName.capitalize())
    card_output = ""
    card_photo = ""
    screen_output = ""
    range_value = PAGINATION_SIZE if len(results) >= PAGINATION_SIZE else len(results)
    for i in range(range_value):
        speech_output += get_people_results_output(results[i])
        card_output += get_people_results_card(results[i])
        card_photo += get_people_results_card_photo_url(results[i])
        screen_output += get_people_results_rich_output(results[i])
    speech_output += " Would you like more results?"
    session.attributes[SESSION_INDEX] = PAGINATION_SIZE + 1
    session.attributes[SESSION_RESULTS] = results
    session.attributes[SESSION_SLOT_FIRSTNAME] = firstName
    session.attributes[SESSION_SLOT_LASTNAME] = lastName

    # CORS enabled photo for testing
    #card_photo='https://i.imgur.com/hYQzVO3.jpg'
    # Attempt at using urllib2 to open the data and read it into variable. FAILS due to expected HTTPS.
    #photo_data = urllib2.urlopen('https://webapp4.asu.edu/photo-ws/directory_photo/cors/mcrow')
    #card_photo = 'data:image/jpeg;base64,' + photo_data.read()

    # Load template wrapper for results.
    speech_output = render_template('people_results', results=speech_output)

    if len(card_photo) > 0:

        out = question(speech_output) \
            .reprompt(reprompt_text) \
            .standard_card(title=card_title, text=card_output)
        # If Show.
        if context.System.device.supportedInterfaces.Display:
            out.display_render(
                template='BodyTemplate2',
                title=card_title,
                token=None,
                text={
                    'primaryText': {
                        'text': screen_output,
                        'type': "RichText"
                    }
                },
                backButton='VISIBLE',
                image=card_photo + '?size=large',
                #background_image_url="https://s3.amazonaws.com/asu.amazonecho/asu_directory_images/background-4.png")
                background_image_url="https://s3.amazonaws.com/asu.amazonecho/asu_directory_images/background_image_girl_dark.png"
            )

        return out

    else:
        out = question(speech_output) \
            .reprompt(reprompt_text) \
            .simple_card(title=card_title, content=card_output)
        # If Show.
        if context.System.device.supportedInterfaces.Display:
            out.display_render(
                template='BodyTemplate2',
                title=card_title,
                token=None,
                text={
                    'primaryText': {
                        'text': screen_output,
                        'type': "RichText"
                    }
                },
                backButton='VISIBLE',
                #background_image_url="https://s3.amazonaws.com/asu.amazonecho/asu_directory_images/background-4.png")
                background_image_url="https://s3.amazonaws.com/asu.amazonecho/asu_directory_images/background_image_girl_dark.png"
            )

        return out


@ask.intent('iSearchIntentPeopleRepeat')
def get_repeat_isearch_people_results():
    # logging.debug("INTENT: iSearchIntentPeopleRepeat")
    return get_next_isearch_people_results(repeat=True)

@ask.intent('iSearchIntentPeopleNext')
def get_next_isearch_people_results(repeat=None):
    # logging.debug("INTENT: iSearchIntentPeopleNext")
    """
    (QUESTION) Responds to advancing in people name search results.
    Templates:
    * Initial statement: dynamic response
    * Reprompt statement: 'welcome_re'
    * No results: 'no_results'
    * Results: 'people_results'
    * Card title: 'More results for [firstname] [lastname] in people'
    * Card body: dynamic response 
    """

    reprompt_text = render_template('welcome_re')

    results = session.attributes[SESSION_RESULTS]
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
    screen_output = ""
    i = 0
    if index >= len(results):
        speech_output += " End of results. ...You can do another search, ask to spell a name, or say quit."
        return question("{}".format(speech_output))

    else:
        while i < PAGINATION_SIZE and index < len(results):
            speech_output += get_people_results_output(results[index])
            card_output += get_people_results_card(results[index])
            card_photo += get_people_results_card_photo_url(results[index])
            screen_output += get_people_results_rich_output(results[index])
            i += 1
            index += 1
        speech_output += " For more results say next. To hear again, say repeat."


    session.attributes[SESSION_INDEX] = index
    session.attributes[SESSION_SLOT_FIRSTNAME] = firstName
    session.attributes[SESSION_SLOT_LASTNAME] = lastName

    # Load template wrapper for results.
    speech_output = render_template('people_results', results=speech_output)

    if len(card_photo) > 0:

        out = question(speech_output) \
            .reprompt(reprompt_text) \
            .standard_card(title=card_title, text=card_output)
        # If Show.
        if context.System.device.supportedInterfaces.Display:
           out.display_render(
               template='BodyTemplate2',
               title=card_title,
               token=None,
               text={
                   'primaryText': {
                       'text': screen_output,
                       'type': "RichText"
                   }
               },
               backButton='VISIBLE',
               image=card_photo + '?size=large',
               #background_image_url="https://s3.amazonaws.com/asu.amazonecho/asu_directory_images/background-4.png")
               background_image_url="https://s3.amazonaws.com/asu.amazonecho/asu_directory_images/background_image_girl_dark.png"
           )

        return out

    else:
        out = question(speech_output) \
            .reprompt(reprompt_text) \
            .simple_card(title=card_title, content=card_output)
        # If Show.
        if context.System.device.supportedInterfaces.Display:
            out.display_render(
                template='BodyTemplate2',
                title=card_title,
                token=None,
                text={
                    'primaryText': {
                        'text': screen_output,
                        'type': "RichText"
                    }
                },
                backButton='VISIBLE',
                #background_image_url="https://s3.amazonaws.com/asu.amazonecho/asu_directory_images/background-4.png")
                background_image_url="https://s3.amazonaws.com/asu.amazonecho/asu_directory_images/background_image_girl_dark.png"
            )

        return out

@ask.intent('iSearchIntentSpellName')
def get_spell_isearch_names(firstNameSpelled, lastNameSpelled):
    # logging.debug("INTENT: iSearchIntentSpellName")
    """
    (QUESTION) Responds to "spell name" utterance. Uses dialog delegation.
    Templates:
    Uses dialog delegation then routes to get_isearch_people_results().
    """

    dialog_state = get_dialog_state()
    if dialog_state != "COMPLETED":
        return delegate(speech=None)

    # Pre-Solr search processing.
    # Strip out spaces, if any are still in the string after Alexa's processing. Capitalize first character only.
    lastNameSpelled = lastNameSpelled.replace(" ", "").capitalize()
    firstNameSpelled = firstNameSpelled.replace(" ", "").capitalize()

    # Invokes iSearchIntentPeople intent, once spelling/delegation and pre-processing is done.
    return get_isearch_people_results(firstNameSpelled, lastNameSpelled)

@ask.intent('iSearchIntentTitle')
def get_isearch_title_results(titleSearchPhrase):
    # logging.debug("INTENT: iSearchIntentTitle")
    """ 
    (QUESTION) Responds to a "who is [title + (optional) dept]" utterance with 
    a list of results and a card.
    Templates:
    * Initial statement: dynamic response
    * Display: ListTemplate1
    * Reprompt statement: 'title_re'
    * No results: 'no_results'
    * Results: dynamic response
    * Card title: 'Results for your title search for [search phrase] ...'
    * Card body: dynamic response
    """

    # Utterance examples (noted for testing)
    #   who is {president}
    #   who is {president of ASU}
    #   who is {university president}
    #   who is {vice president registrar}
    #   who is {chief information officer}
    #   who is {chief information officer university technology office}
    #   who is {chief information officer analytics}
    #   who is {systems analyst applications and design}

    # Set search context in the session.
    # This is key for any intent querying for serach results, and planning to
    # list those results.
    # See iSearchIntentItemDetail and iSearchIntentBackToResults intents for
    # how this comes into play.
    session.attributes[SESSION_SEARCH_CONTEXT] = 'iSearchIntentTitle'
    session.attributes[SESSION_SLOT_TITLE_SEARCH_PHRASE] = titleSearchPhrase

    reprompt_text = render_template('title_re')

    # Do the search query if we have a search.
    if titleSearchPhrase:
        results = get_title_results(titleSearchPhrase)
    else:
        return question("{}".format(reprompt_text))

    if results == None:
        return question("{}".format(render_template('no_results', search_phrase=titleSearchPhrase)))
    if len(results) < 1:
        return question("{}".format(render_template('no_results', search_phrase=titleSearchPhrase)))

    # Stash results in session
    session.attributes[SESSION_RESULTS] = results

    # DEBUG
    # logging.debug("*********** RESULTS {}".format(results))

    speech_output = "Results from your title search for {}... \n".format(titleSearchPhrase)
    card_title = "Results from your title search for {}... \n".format(titleSearchPhrase)
    card_output = ""
    card_photo = ""
    screen_output = ""

    # Build ListTemplate1 list of results
    display_items = []
    for i in range(len(results)):  # So we have an accessible key index.
        display_items = display_items + [
            {
                'token': 'result_{}'.format(i),  # Tokenize by results index.
                'image': {
                    'sources': [
                        {
                            'url': results[i]['photoUrl']
                        }
                    ],
                    'contentDescription': 'photo of {}'.format(results[i]['displayName'])
                },
                'textContent': {
                    'primaryText': {
                        'text': '<font size = "4">{}</font>'.format(results[i]['displayName']),
                        'type': 'RichText'
                    },
                    'secondaryText': {
                        'text': '{strtitle}{seperator}{strdept}'.format(
                            strtitle=results[i]['primaryTitle'],
                            seperator=', ' if results[i]['primaryTitle'] and results[i]['primaryiSearchDepartmentAffiliation'] else '',
                            strdept=results[i]['primaryiSearchDepartmentAffiliation']),
                        'type': 'PlainText'
                    },
                }
            }
        ]
        # Build speech output. Only first 5 results for voice and card situations.
        if (i < 5):
            speech_output += "{}. {}".format(i + 1, results[i]['displayName'])  # Item number and displayName
            card_output += "{}. {}".format(i + 1, results[i]['displayName'])
            if (results[i]['primaryTitle']):  # primaryTitle if we have it
                speech_output += " is {}".format(results[i]['primaryTitle'])
                card_output += ", {}".format(results[i]['primaryTitle'])
            if (results[i]['primaryiSearchDepartmentAffiliation']):  # Dept affiliation if we have it
                speech_output += " of {},".format( results[i]['primaryiSearchDepartmentAffiliation'])
                card_output += ", {}\r\n".format(results[i]['primaryiSearchDepartmentAffiliation'])
            card_photo += get_people_results_card_photo_url(results[i])

    speech_output += " If you'd like more details on one of these, ask me to open the item by number."

    # DEBUG
    # logging.debug("*********** ITEMS {}".format(display_items))

    out = question(speech_output) \
        .reprompt(reprompt_text) \
        .simple_card(title=card_title, content=card_output)
    # If Show.
    if context.System.device.supportedInterfaces.Display:
        out.list_display_render(
            template='ListTemplate1',
            title=card_title,
            background_image_url="https://s3.amazonaws.com/asu.amazonecho/asu_directory_images/background-4.png",
            token='titlePhraseResults',
            backButton='VISIBLE',
            listItems=display_items,
        )

    return out

@ask.intent('iSearchIntentItemDetail')
def get_isearch_item_detail_intent(itemNumber = None):
    # logging.debug("INTENT: iSearchIntentItemDetail")
    """ 
    (QUESTION) Responds to a numeric list item utterance or item touch.
    Templates:
    * Initial statement: dynamic response
    * Display: dynamic response, based on SESSION_SEARCH_CONTEXT 
    * Reprompt statement: 'welcome_re'
    * No results: 'no_results'
    * Results: dynamic response, based on SESSION_SEARCH_CONTEXT
    * Card title: none
    * Card body: dynamic response, based on SESSION_SEARCH_CONTEXT
    """

    # Spoken item selections utterances will hit this directly. Touch-based
    # selections will route through element_selected() first.

    # Making this detail/search type agnostic so if we were to switch out
    # to doing a list template presentation for people search, or if we
    # added another search type, we could use the same numeric selection
    # utterance mapping and just manage handling based on context.

    reprompt_text = render_template('welcome_re')

    # If we arrived by touch, we'll need to extract itemNumber from the token
    # as it won't be in itemNumber slot from an utterance.
    if (itemNumber == None):
        # Cut the "result_" off the token, then cast as int.
        itemNumber = int(request['token'][7:]) + 1  # +1 to match voice selection. logging.debug("*********** NOW itemNumber {}".format(itemNumber))

    # Route handling based on context
    if (session.attributes[SESSION_SEARCH_CONTEXT] == 'iSearchIntentTitle'):

        # Obtain the results previously stashed in session.
        session_results = session.attributes[SESSION_RESULTS]

        # Use itemNumber as index for pinpointing desired session_results.
        index = int(itemNumber) - 1  # Realign to our index

        speech_output = ""
        card_title = ""
        card_output = ""
        card_photo = ""
        screen_output = ""

        speech_output += get_people_results_output(session_results[index])
        card_output += get_people_results_card(session_results[index])
        card_photo += get_people_results_card_photo_url(session_results[index])
        screen_output += get_people_results_rich_output(session_results[index])
        speech_output += " "

        # Load template wrapper for people detail/results.
        speech_output = render_template('people_results', results=speech_output)

        if len(card_photo) > 0:  # If we have a card photo

            out = question(speech_output) \
                .reprompt(reprompt_text) \
                .standard_card(title=card_title, text=card_output)
            # If Show.
            if context.System.device.supportedInterfaces.Display:
                out.display_render(
                    template='BodyTemplate2',
                    title=card_title,
                    token=None,
                    text={
                        'primaryText': {
                            'text': screen_output,
                            'type': "RichText"
                        }
                    },
                    backButton='VISIBLE',
                    image=card_photo + '?size=large',
                    background_image_url="https://s3.amazonaws.com/asu.amazonecho/asu_directory_images/background_image_girl_dark.png"
                )

            return out

        else:  # No card photo

            out = question(speech_output) \
                .reprompt(reprompt_text) \
                .simple_card(title=card_title, content=card_output)
            # If Show.
            if context.System.device.supportedInterfaces.Display:
                out.display_render(
                    template='BodyTemplate2',
                    title=card_title,
                    token=None,
                    text={
                        'primaryText': {
                            'text': screen_output,
                            'type': "RichText"
                        }
                    },
                    backButton='VISIBLE',
                    background_image_url="https://s3.amazonaws.com/asu.amazonecho/asu_directory_images/background_image_girl_dark.png"
                )

            return out

    elif (session.attributes[SESSION_SEARCH_CONTEXT] == 'iSearchIntentPeople'):

        # Reserved but not used yet. We don't do a list template response for
        # people search at this time, due to UX considerations.
        return statement('')

    else:

        # We should never end up here. What.Did.You.Do?
        return statement('')

@ask.intent('iSearchIntentBackToResults')
def get_isearch_back_to_results_intent():
    # logging.debug("INTENT: iSearchIntentBackToResults")
    """
    Respond to utterances asking to go back to results listings.
    """

    # Route to results based on SESSION_SEARCH_CONTEXT

    if session.attributes[SESSION_SEARCH_CONTEXT] == 'iSearchIntentTitle':

        titleSearchPhrase = session.attributes[SESSION_SLOT_TITLE_SEARCH_PHRASE]

        return get_isearch_title_results(titleSearchPhrase)

    if session.attributes[SESSION_SEARCH_CONTEXT] == 'iSearchIntentPeople':

        # Not handling people name search flow through list view handling,
        # yet due to UX concerns, so this is mostly just a placeholder.
        return launch()

    return launch()

@ask.display_element_selected
def element_selected():
    # logging.debug("INTENT: display_element_selected")
    """
    All list template touch selections route through here. If selection is
    is spoken, this method is bypassed and goes straight to
    get_isearch_item_detail_intent().
    """

    # Get the selected token.
    token = request['token']

    # Setup token-to-details-intent mappings for all results.
    # We create tokens in the pattern of "result_N" where N is the numeric
    # index mapping to our list items.
    # All tokens map to the same detail method for processing. The detail
    # method (get_isearch_item_detail_intent()) extrapolates indexes from
    # tokens and displays the appropriate result from the results stored
    # in the session by context (aka intent type).
    token_to_intent_lookup = {}
    for i in range(RESPONSE_SIZE):
        # Same detail method for all.
        token_to_intent_lookup['result_{}'.format(i)] = get_isearch_item_detail_intent

    return token_to_intent_lookup[token]()


@ask.intent('AMAZON.StopIntent')
def stop():
    # logging.debug("INTENT: StopIntent")
    return statement("Goodbye")

@ask.intent('AMAZON.CancelIntent')
def cancel():
    # logging.debug("INTENT: CancelIntent")
    return statement("Goodbye")

@ask.intent('AMAZON.HelpIntent')
def help():
    # logging.debug("INTENT: HelpIntent")
    return question(render_template('help_text'))

@ask.intent('AMAZON.NavigateSettingsIntent')
def handle_navigate_settings():
    # logging.debug("INTENT: NavigateSettingsIntent")
    """
    (?) Handles the 'navigate settings' built-in intention.
    """
    pass

@ask.intent('AMAZON.MoreIntent')
def handle_more():
    # logging.debug("INTENT: MoreIntent")
    """
    (?) Handles the 'more' built-in intention.
    """
    pass

@ask.intent('AMAZON.NextIntent')
def handle_next():
    # logging.debug("INTENT: NextIntent")
    """
    (?) Handles the 'next' built-in intention.
    """
    pass

@ask.intent('AMAZON.PageDownIntent')
def handle_page_down():
    # logging.debug("INTENT: PageDownIntent")
    """
    (?) Handles the 'page down' built-in intention.
    """
    pass

@ask.intent('AMAZON.PageUpIntent')
def handle_page_up():
    # logging.debug("INTENT: PageUpIntent")
    """
    (?) Handles the 'page up' built-in intention.
    """
    pass

@ask.intent('AMAZON.NoIntent')
def handle_no():
    # logging.debug("INTENT: NoIntent")
    """
    (?) Handles the 'no' built-in intention.
    """
    pass

@ask.intent('AMAZON.YesIntent')
def handle_yes():
    # logging.debug("INTENT: YesIntent")
    """
    (?) Handles the 'yes'  built-in intention.
    """
    pass

@ask.intent('AMAZON.PreviousIntent')
def handle_back():
    # logging.debug("INTENT: PreviousIntent")
    """
    (?) Handles the 'go back!'  built-in intention.
    """
    pass

@ask.intent('AMAZON.StartOverIntent')
def start_over():
    # logging.debug("INTENT: StartOverIntent")
    """
    (QUESTION) Handles the 'start over!'  built-in intention.
    """
    pass

@ask.session_ended
def session_ended():
    logging.debug("INTENT: session_ended")
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
