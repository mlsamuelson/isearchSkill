ABOUT
An Alexa skill to query the ASU iSearch people directory. https://isearch.asu.edu

Built using the Flask-ask library.

Project is in Proof of Concept stage.

Directory_VUI_v_2_0 : https://www.lucidchart.com/invitations/accept/64facdbf-dba7-4c2c-9292-14e6d4d23f8b

Last Name custom slot sample values can be obtained by querying Solr
https://asudir-solr.asu.edu/asudir/directory/select?q=*&fl=lastName&wt=csv&rows=50000
And then deduping the output in a spreadsheet program.

ROADMAP
- uncomment code for displaying photos in cards when CORS has been enabled on the Photos service. Laura C. TODO
- test fuzzy-ing up the Solr query for better matching on names
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