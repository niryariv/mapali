####
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
####


from flask import Flask, render_template, request, redirect, Response, url_for, make_response
import time, os, json, base64, hmac, urllib
from hashlib import sha1
import pymongo
from pymongo.errors import ConnectionFailure
from bson import json_util

app = Flask(__name__)

MONGO_URL = os.environ.get('MONGOLAB_URI')

if MONGO_URL:  # on Heroku, get a connection
    m_conn = pymongo.Connection(MONGO_URL)
    db = m_conn[urlparse(MONGO_URL).path[1:]]
    RUNNING_LOCAL = False
else:  # work locally
    try:
        m_conn = pymongo.Connection('localhost', 27017)
    except ConnectionFailure:
        print('You should have mongodb running')

    db = m_conn['citymap']
    RUNNING_LOCAL = True
    app.debug = True  # since we're local, keep debug on



# Listen for POST requests to yourdomain.com/submit_form/
@app.route("/submit_form/", methods=["POST"])
def submit_form():
    # Collect the data posted from the HTML form in account.html:
    description = request.form["description"]
    image_url = request.form["image_url"]
    lng = request.form["lng"]
    lat = request.form["lat"]

    db.locations.insert({
        'description'   : description,
        'image_url'     : image_url,
        'loc'           : { 'lat' : lat, 'lng' : lng }
        })

    
    # Redirect to the user's profile page, if appropriate
    #return redirect(url_for('profile'))
    return "hello %s %s %s" % (description, latlng, image_url)


# Listen for GET requests to yourdomain.com/sign_s3/
@app.route('/sign_s3/')
def sign_s3():
    # Load necessary information into the application:
    AWS_ACCESS_KEY = os.environ.get('AWS_ACCESS_KEY_ID')
    AWS_SECRET_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
    S3_BUCKET = os.environ.get('S3_BUCKET')

    # return "AWS_ACCESS_KEY=%s AWS_SECRET_KEY=%s S3_BUCKET=%s" % (AWS_ACCESS_KEY, AWS_SECRET_KEY, S3_BUCKET)

    # Collect information on the file from the GET parameters of the request:
    object_name = urllib.quote_plus(request.args.get('s3_object_name'))
    mime_type = request.args.get('s3_object_type')

    # Set the expiry time of the signature (in seconds) and declare the permissions of the file to be uploaded
    expires = int(time.time()+10)
    amz_headers = "x-amz-acl:public-read"
 
    # Generate the PUT request that JavaScript will use:
    put_request = "PUT\n\n%s\n%d\n%s\n/%s/%s" % (mime_type, expires, amz_headers, S3_BUCKET, object_name)
     
    # print put_request 
    # print AWS_SECRET_KEY

    # Generate the signature with which the request can be signed:
    signature = base64.encodestring(hmac.new(AWS_SECRET_KEY, put_request, sha1).digest())
    # Remove surrounding whitespace and quote special characters:
    signature = urllib.quote_plus(signature.strip())

    # Build the URL of the file in anticipation of its imminent upload:
    url = 'https://%s.s3.amazonaws.com/%s' % (S3_BUCKET, object_name)

    content = json.dumps({
        'signed_request': '%s?AWSAccessKeyId=%s&Expires=%d&Signature=%s' % (url, AWS_ACCESS_KEY, expires, signature),
        'url': url
    })

    r = make_response(content)
    r.headers['Access-Control-Allow-Origin'] = "*"
    r.headers['Content-Type'] = "application/json; charset=utf-8"
    return r

    # Return the signed request and the anticipated URL back to the browser in JSON format:
    # return Response(content, mimetype='text/plain; charset=x-user-defined', )
    
# Main code
if __name__ == '__main__':
    app.debug = True
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
    
