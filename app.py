from flask import Flask
from flask import request
from flask import render_template

from core.data_provider import get_status_updates
from core import prepare_data
from core import analyze_status_updates

import urllib.parse as url_parser

app = Flask(__name__)


@app.route('/check/', methods=['GET', 'POST'])
def check():
    if request.method == 'POST':
        url = request.form.get('account_url', 'hpi_de')
        parsed_url = url_parser.urlparse(url)
        user_id = parsed_url.path.split('/')[1]
        user_status_updates = get_status_updates('twitter', user_id=user_id)
        ext_status_updates = prepare_data('fth', dataset_path="./follow_the_hashtag_usa.csv")
        result = analyze_status_updates(user_status_updates, ext_status_updates, 'perceptron')
        return str(result)
    else:
        return render_template('check.html')
