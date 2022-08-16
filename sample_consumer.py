from flask import Flask, jsonify, request
from werkzeug import exceptions
from loguru import logger
import json
import sys

app = Flask(__name__)

last_event: dict = None

@app.route('/journalevent/', methods=['GET', 'POST'])
def journalevent():
    global last_event
    if request.method == 'POST':
        posted_data = request.get_json() # returns a dict
        logger.debug(f'{posted_data=} ({type(posted_data)})')
        posted_data = json.loads(posted_data)
        event = posted_data['event']
        r = jsonify(event=event)
        logger.debug(f'{r=}')
        last_event = r
        return r, 200

    if request.method == 'GET':
        if last_event:
            return last_event, 200
        return jsonify(event="None"), 200

@app.errorhandler(exceptions.BadRequest)
def handle_bad_request(e):
    return 'bad request!', 400

@app.errorhandler(exceptions.BadRequest)
def handle_file_not_found(e):
    return 'file not found!', 404

if __name__ == "__main__":
    # from waitress import serve
    try:
        # use waitress instead of flask if you want to
        # serve(app, host="0.0.0.0", port=5000)
        app.run(debug=True)
    except KeyboardInterrupt:
        print('Caught Ctrl+C')
    finally:
        sys.exit(0)
