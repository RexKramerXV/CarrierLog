from flask import Flask, jsonify, request
from loguru import logger
import json
import sys

app = Flask(__name__)

last_event: dict = None


@app.route('/')
def index():
    return '<h1>Hello!</h1>'


@app.route('/journalevent/', methods=['GET', 'POST'])
def journalevent():
    global last_event
    posted_json : str = "" # that will be a JSON string
    if request.method == 'POST':
        posted_json = request.get_json()
        logger.debug(f'JSON received: {posted_json=}')
        posted_dict = json.loads(posted_json)
        logger.debug(f'dict loaded: {posted_dict=}')
        event = posted_dict['event']
        r = jsonify(event=event)
        logger.info(f'{r=}')
        last_event = r
        return r

    if request.method == 'GET':
        if last_event:
            return last_event
        return jsonify(event="None")


if __name__ == "__main__":
    # from waitress import serve
    try:
        # serve(app, host="0.0.0.0", port=5020)
        app.run(debug=True)
    except KeyboardInterrupt:
        print('Caught Ctrl+C')
    finally:
        sys.exit(0)
