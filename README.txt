ABOUT
An Alexa skill to query the ASU iSearch people directory. https://isearch.asu.edu

Built using the Flask-ask library.

Project is in Proof of Concept stage.

Directory_VUI_v_2_0 : https://www.lucidchart.com/invitations/accept/64facdbf-dba7-4c2c-9292-14e6d4d23f8b

ROADMAP
- Uncomment code for displaying photos in cards when CORS has been enabled on the Photos service. Laura C. TODO
- fuzzy up the Solr query for better matching on names
- add VIP's last names to sample LAST_NAME slot values
- better pronunciation for ASU-specific words and abbreviations via SSML <phoneme> and <say-as> tags.
- X can we use Flask caching for results within Flask-ask? http://flask.pocoo.org/docs/0.12/patterns/caching/
  - caching already in Flask-ask library: cache.py
- separate code and response formatting better. Perhaps levarage Flask-ask Jinja templating.

NOTES
- Dialog Delegation support notes: https://github.com/johnwheeler/flask-ask/pull/165