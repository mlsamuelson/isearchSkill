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
- uncomment code for displaying photos in cards when CORS has been enabled on the Photos service. Laura C. TODO
- test fuzzy-ing up the Solr query for better matching on names. A challenge with this is we've already gone through
  a layer of Alexa NLP before the query is issued, so things can get skewed before we fuzzy on it.
- X Add "repeat" as option alongside next result process
- Figure out what's up with 'for' utterances not mapping to search intent unless search involves a recorded slot value
- X add VIP's last names to sample LAST_NAME custom slot values for enhanced recognition.
- better pronunciation for ASU-specific words and abbreviations via SSML <phoneme> and <say-as> tags.
  We had a go at this implemented, however Flask-ask detection of SSML was spotty and it would often read-aloud the
  tags. Initial inspection failed to determine why. Backed out SMSML for now. We'll need to debug the issue from
  within Flask-ask.
- X can we use Flask caching for results within Flask-ask? http://flask.pocoo.org/docs/0.12/patterns/caching/
  - caching already in Flask-ask library: cache.py
- check options for better separation of concerns: code and responses. Perhaps leverage Flask-ask Jinja templating.
- Echo Show display support

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

