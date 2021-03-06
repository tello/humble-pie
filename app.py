import flask
import os, sys
from datetime import datetime
try:
    import simplejson as json
except ImportError:
    import json
import logging

import passtools


app = flask.Flask(__name__)

try:
    import config
except ImportError:
	# set custom values in config.py 
	PROD_KEY = '3384f7e5-e195-4c2f-94ac-5a1c7ae37b33'
	DEV_KEY = 'a7633f06-b1b3-4c34-beaf-36e8905ea9ed'

PROD_BASE_URL = 'http://www.passtools.com'
DEV_BASE_URL = 'http://localhost:3000'

if '/app/.heroku/' in os.environ.get('PATH',''): # production
	API_KEY = PROD_KEY
	BASE_URL = PROD_BASE_URL
	API_URL = None # default
else: # development
	API_KEY = DEV_KEY
	BASE_URL = DEV_BASE_URL 
	API_URL = 'http://localhost:8080/v1'

BASE_CONTEXT = {
	'base_url' : BASE_URL,
	'api_key': API_KEY
}

"""
	Template Views 
"""

@app.route('/')
def templates():
	context = BASE_CONTEXT.copy()
	context.update({ 'page': 'templates' })
	pt_service = passtools.Service(api_key=API_KEY,api_url=API_URL)
	context['templates'] = pt_service.list_templates()
	return flask.render_template('templates.html', **context)

@app.route('/template/<int:template_id>')
def template(template_id):
	context = BASE_CONTEXT.copy()
	context.update({ 'page': 'template' })
	pt_service = passtools.Service(api_key=API_KEY,api_url=API_URL)
	context['template'] = pt_service.get_template(template_id)
	return flask.render_template('template.html', **context)

@app.route('/template/<int:template_id>/delete')
def delete_template(template_id):
	pt_service = passtools.Service(api_key=API_KEY,api_url=API_URL)
	pt_service.delete_template(template_id)
	return flask.redirect('/')


"""
	Pass Views 
"""

@app.route('/passes')
def passes():
	context = BASE_CONTEXT.copy()
	context.update({ 'page': 'passes' })
	pt_service = passtools.Service(api_key=API_KEY,api_url=API_URL)
	context['passes']  = pt_service.list_passes()
	context['api_key'] = pt_service.api_client.api_key
	return flask.render_template('passes.html', **context)

@app.route('/pass/<int:pass_id>')
def pt_pass(pass_id):
	context = BASE_CONTEXT.copy()
	context.update({ 'page': 'pass' })
	pt_service = passtools.Service(api_key=API_KEY,api_url=API_URL)
	context['pt_pass'] = pt_service.get_pass(pass_id)
	return flask.render_template('pass.html', **context)

@app.route('/template/<int:template_id>/pass')
def create_pass(template_id):
	pt_service = passtools.Service(api_key=API_KEY,api_url=API_URL)
	pass_template = pt_service.get_template(template_id) # TODO: this shouldn't be necessary
	new_pass  = pt_service.create_pass(template_id, template_fields_model=pass_template.fields_model)
	return flask.redirect('/pass/%s' % new_pass.pass_id)	

@app.route('/pass/<int:pass_id>/update')
def update_pass(pass_id):
	pt_service = passtools.Service(api_key=API_KEY,api_url=API_URL)
	update_fields = json.loads(flask.request.args.get('fields'))
	pt_service.update_pass(pass_id, update_fields)
	pt_service.push_pass(pass_id)
	return flask.redirect('/pass/%s' % pass_id)	

@app.route('/pass/<int:pass_id>/delete')
def delete_pass(pass_id):
	pt_service = passtools.Service(api_key=API_KEY,api_url=API_URL)
	pt_service.delete_pass(pass_id)
	return flask.redirect('/')	

"""
	Errors Views 
"""

@app.route('/errors')
def errors():
	context = BASE_CONTEXT.copy()
	context.update({ 'page': 'errors', 'e': flask.request.args.get('e') })
	return flask.render_template('errors.html', **context)

@app.route('/errors/<error_type>')
def generate_error(error_type):
	pt_service = passtools.Service(api_key=API_KEY,api_url=API_URL)

	class ErrorGenerator():
		def list_templates(self):
			pt_service.list_templates(order='invalid_value')
		def get_template(self):
			pt_service.get_template(00000)
		def list_passes(self):
			pt_service.list_passes(order='invalid_value')
		def create_pass(self):
			pt_service.create_pass(00000)
		def get_pass(self):
			pt_service.get_pass(00000)	
		def update_pass(self):
			pt_service.update_pass(00000)
		def download_pass(self):
			pt_service.download_pass(00000)
		def delete_pass(self):
			pt_service.delete_pass(00000)									

	error_generator = ErrorGenerator()
	try:
		getattr(error_generator, error_type)()
	except passtools.exceptions.PassToolsException:
		logging.debug('Passtools Exception generated for %s' % error_type)
	return flask.redirect('/errors?e=' + error_type)	


"""
	Settings Views 
"""

@app.route('/settings')
def settings():
	context = BASE_CONTEXT.copy()
	context.update({ 'page': 'settings' })
	return flask.render_template('settings.html', **context)


"""
	Custom Template Filters
"""

@app.template_filter()
def timesince(dt, default="just now"):
    """
    Returns string representing "time since" e.g.
    3 days ago, 5 hours ago etc.
    """

    now = datetime.utcnow()
    diff = now - dt
    
    periods = (
        (diff.days / 365, "year", "years"),
        (diff.days / 30, "month", "months"),
        (diff.days / 7, "week", "weeks"),
        (diff.days, "day", "days"),
        (diff.seconds / 3600, "hour", "hours"),
        (diff.seconds / 60, "minute", "minutes"),
        (diff.seconds, "second", "seconds"),
    )

    for period, singular, plural in periods:
        
        if period:
            return "%d %s ago" % (period, singular if period == 1 else plural)

    return default

@app.template_filter()
def pretty_dict(d, indent=4):
	return json.dumps(d, sort_keys=True, indent=indent).replace('\n','<br/>').replace(' ','&nbsp;')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
