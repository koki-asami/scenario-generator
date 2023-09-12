# import os

import werkzeug  # noqa
# from auth import do_auth, set_auth
# from constant import IS_PRODUCTION
from flask import Flask, jsonify

# from log import start_send_log_worker
# from predictor import predictor_apis
from sagemaker import sagemaker_apis

app = Flask(__name__)

# if IS_PRODUCTION:
#     do_auth(os.environ.get('AUTHENTICATION_KEY', ''))
#     start_send_log_worker()
# else:
#     set_auth(True)

# docker API/SDK
# for _, predictor_api in predictor_apis.items():
#     app.register_blueprint(predictor_api)

# sagemaker api
app.register_blueprint(sagemaker_apis)


@app.errorhandler(404)
def page_not_found(error):
    return jsonify({'error': {
        'code': 'Not found',
        'message': 'Page not found',
    }}), 404


if __name__ == '__main__':
    print(app.url_map)
    app.run(host='0.0.0.0', port=8080, debug=True)
