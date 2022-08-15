from flask import Flask, jsonify, request
from loguru import logger
import sys

app = Flask(__name__)

@app.route('/')
def index():
    return '<h1>Hello!</h1>'

@app.route('/journalevent', methods=['POST'])
def read_journalevent():
    if request.method=='POST':
        posted_data = request.get_json()
        data = posted_data['event']
        logger.info(f'{data=}')
        return jsonify(f'Successfully stored  {data}')

if __name__ == "__main__":
    from waitress import serve
    try:
        serve(app, host="0.0.0.0", port=5020)
    except KeyboardInterrupt:
        print('Caught Ctrl-C')
    finally:
        sys.exit(0)
