from flask import Flask, request

import site_map

app = Flask(__name__)


@app.route('/', methods=['POST'])
def generate_site_map():
    # show the user profile for that user
    url = request.form['url']
    max_depth = int(request.form['max_depth'])
    max_thread = int(request.form['max_thread'])
    site_map_request = site_map.SiteMap(url, max_depth, max_thread)
    return site_map_request.build_site_map()
