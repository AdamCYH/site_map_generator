This is a simple service that generates a site map of target url.

Site with custmized tag is not supported. for example figure tag

## Run by terminal ##
$ python site_map.py <url> <max_depth> <max_thread> \
ex. python site_map.py https://www.mozilla.org 3 4

## Run by web service ##
1. start the virtual environment
2. run the following command to start server

$env FLASK_APP=server.py flask run


Supported request type - POST
Parameters
url, max_depth, max_thread
