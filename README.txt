ABOUT
An Alexa skill to query the ASU iSearch people directory. https://isearch.asu.edu

Built using the Flask-ask library.

Project is in Proof of Concept stage.

Directory_VUI_v_2_0 : https://www.lucidchart.com/invitations/accept/64facdbf-dba7-4c2c-9292-14e6d4d23f8b

Last Name custom slot sample values can be obtained by querying Solr
https://asudir-solr.asu.edu/asudir/directory/select?q=*&fl=lastName&wt=csv&rows=50000
And then deduping the output in a spreadsheet program. However, that produces over 20k
unique values, and from what other Alexa devs indicate, while 50k is a technical limit,
2k is a more practical limit. Further details on ALEXADEV-131.

ROADMAP
- Improve abstraction of Solr querying - perhaps bring in a 3rd party library or add our own class.
- Add a VUI route for querying Dept phone numbers and info. As reference, for how this might work, see
  https://www.amazon.com/The-University-of-Oklahoma-Directory/dp/B073WL5BYR/
- Figure out what's up with 'for' utterances not mapping to search intent unless search involves a recorded slot value
- PARTIAL IMPLEMENTATION. SEE templates.yaml. CONTINUE TEMPLATING: check options for better separation of concerns:
  code and responses. Perhaps leverage Flask-ask Jinja templating.
- Explore CORS image options going forward for cards delivered via the App. We've shut those off, but they do display
  on the Show.
- Touch activate phone numbers on the Show to initiate a call. (If ASK API allows.)
- Touch display not always honoring line breaks in output. (documented Alexa issue)
COMPLETED
- X Improve repeat queries during a single launch.
- X Add "who is the ___" titleSearchIntent using ListTemplate1 display for text lists with optional images.
- X Rethink deploying to Show with a more touch-interactive results browsing experience, i.e. use of list templates.
  - Added for title search. Still doesn't make sense for
- X Added spellName intent for names Alexa doesn't recognize.
- X (revisit later, in iSearch 2.0) Explore use of phonetic filters in Solr queries:
    https://lucene.apache.org/solr/guide/6_6/phonetic-matching.html
    Currently employs Double Metaphone algorithm.
- X Test fuzzy-ing up the Solr query for better matching on names. A challenge with this is we've already gone through
  a layer of Alexa NLP before the query is issued, so things can get skewed before we fuzzy on it.
- X Add "repeat" as option alongside next result process
- X add VIP's last names to sample LAST_NAME custom slot values for enhanced recognition.
- X Better pronunciation for ASU-specific words and abbreviations via SSML <phoneme> and <say-as> tags.
  We had a go at this implemented, however Flask-ask detection of SSML was spotty and it would often read-aloud the
  tags. Initial inspection failed to determine why. Backed out SSML for now. We'll need to debug the issue from
  within Flask-ask.
- X can we use Flask caching for results within Flask-ask? http://flask.pocoo.org/docs/0.12/patterns/caching/
  - caching already in Flask-ask library: cache.py
- X Echo Show display support- works with cards and photos, but better template, perhaps?
- X Backwards compatibility between display and non-display devices.

NOTES
- Dialog Delegation support notes: https://github.com/johnwheeler/flask-ask/pull/165

BUILD
Original reference: https://developer.amazon.com/blogs/post/8e8ad73a-99e9-4c0f-a7b3-60f92287b0bf/new-alexa-tutorial-deploy-flask-ask-skills-to-aws-lambda-with-zappa
Steps:
1. Auth with the AWS CLI to the account you'll be deploying to:
  $ aws configure
  Use us-east-1 for the default region name.
2. Activate the Python Virtual Environment from virtualenv
  $ source venv/bin/activate
3. Deploy with Zappa. Can also try doing update, for faster process if you've deployed before.
  $ zappa deploy <environ-name-from-zappa_settings.json>
4. You may need to copy the deployment URL output by Zappa to Configuration > Endpoint: https, Default: <the-URL>/directory
  NOTE: the /directory needs to be added to the endpoint URL due to how we're routing the Flask app in isearch.py.

Tail a deployed resource:
  $ zappa tail <environ-name>

Alternate local testing:
You can create an endpoint locally using ngrok.
Start ngrok
 $ ./ngrok http 5000
and the isearch.py script.
 $ python isearch.py
Then set the https endpoint address + "/directory" as reported by ngrok to be the skill endpoint in the developer site.

