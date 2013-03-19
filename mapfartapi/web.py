from flask import render_template

def index():
    return render_template('index.html')

def documentation():
    return render_template('documentation.html')

def api_landing():
    return render_template('api_landing.html')

