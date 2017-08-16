ABOUT
An Alexa skill to query the ASU iSearch people directory. https://isearch.asu.edu

Built using the Flask-ask library.

Project is in Proof of Concept stage.

ROADMAP
- Uncomment code for displaying photos in cards when CORS has been enabled on the Photos service. Laura C. TODO
- fuzzy up the Solr query for better matching on names
- add VIP's last names to sample LAST_NAME slot values
- can we use Flask caching for results within Flask-ask? http://flask.pocoo.org/docs/0.12/patterns/caching/
- separate code and response formatting better. Perhaps levarage Flask-ask Jinja templating.