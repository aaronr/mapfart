# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify
from flask import make_response, render_template
from flask import flash, redirect, url_for, session, escape, g

# General web serving
from mapfartapi.web import index, documentation, api_landing
# The good old fart generate code
from mapfartapi.api import fart, fart_srid, fart_srid_xy, fart_default
# The fart serve code
from mapfartapi.api import fart_serve
# Testing...
from mapfartapi.api import testcurl

app = Flask(__name__)

app.config.from_pyfile('default.cfg')
app.config.from_pyfile('local.cfg')

# URLs
# Landing Page
app.add_url_rule('/', 'index', index)
# Fart Serve
app.add_url_rule('/fart_<fart_id>', 'fart_serve', fart_serve, methods=['GET'])
# Building farts
# Default farts
app.add_url_rule('/api/fart', 'fart_default', fart_default, methods=['POST'])
# Reprojected farts
app.add_url_rule('/api/<int:srid>/fart', 'fart_srid', fart_srid, methods=['POST'])
# Reprojected farts of any size
app.add_url_rule('/api/<int:srid>/<int:xsize>/<int:ysize>/fart', 'fart_srid_xy', fart_srid_xy, methods=['POST'])

# Docs (in the future)
app.add_url_rule('/api', 'api', api_landing)
app.add_url_rule('/documentation', 'documentation', documentation)

# Testing
app.add_url_rule('/api/testcurl', 'testcurl', testcurl, methods=['POST'])

@app.errorhandler(500)
def page_not_found(e):
    return "your farts stink... try again!\n", 500

@app.errorhandler(404)
def page_not_found(e):
    return "Your fart request could not be served...\n", 404
  
if __name__ == "__main__":
    app.run(debug=True,host='0.0.0.0')
