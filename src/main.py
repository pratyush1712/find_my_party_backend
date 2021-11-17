import json
from db import db
from flask import Flask
from flask import request
from flask import Response
from db import Party
from db import User
from werkzeug.utils import secure_filename
from db import Img
from db import ImgEvent
import os
import re


app = Flask(__name__)


app = Flask(__name__)
db_filename = "findmyparty.db"

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///%s" % db_filename
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = True
app.config["SQLALCHEMY_ECHO"] = True

db.init_app(app)
with app.app_context():
    db.create_all()

def success_response(data, code=200):
    return json.dumps(data), code

def failure_response(message, code=404):
    return json.dumps({"error": message}), code

def valid_email_address(self, mail):
        email_regex = re.compile(r"[^@]+@[^@]+\.[^@]+")
        return email_regex.match(mail) != None

@app.route("/api/parties/")
def get_all_parties():
    return success_response(
        {"parties":[party.serialize() for party in Party.query.all()]}
    )

@app.route("/api/parties/host/", methods=['POST'])
def host_party():
    body = json.loads(request.data)
    host = body.get("host")
    location = body.get("location")
    dateTime = body.get("dateTime")
    if not (body or host or location or dateTime):
        return failure_response("The request is badly formatted.", 400)
    new_party = Party(
        host=host,
        location=location,
        dateTime=dateTime,
        attendees=[]
    )
    print(new_party)
    db.session.add(new_party)
    db.session.commit()
    return success_response(
        new_party.serialize(),
        201
    )

@app.route("/api/party/<int:party_id>/")
def get_party_by_id(party_id):
    party = Party.query.filter_by(id=party_id).first()
    if not party:
        return failure_response(f"Party with ID {party_id} does not exist!")
    return success_response(party.serialize())

@app.route('/api/party/<int:party_id>/photo/', methods=['POST'])
def upload_party_photo(party_id):
    party = Party.query.filter_by(id=party_id).first()
    if not party:
        return failure_response("Party not found")
    pic = request.files['pic']
    if not pic:
        return failure_response('No pic uploaded!', 400)
    filename = secure_filename(pic.filename)
    mimetype = pic.mimetype
    if not filename or not mimetype:
        return failure_response('Bad upload!', 400)
    img = ImgEvent(img=pic.read(), name=filename, mimetype=mimetype, party_id = party_id)
    db.session.add(img)
    db.session.commit()
    return success_response('Img Uploaded!', 200)

@app.route('/api/party/<int:party_id>/photo/')
def get_img(party_id):
    party = Party.query.filter_by(id=party_id).first()
    if not party:
        return failure_response(f"Party with ID {party_id} does not exist!")
    image_id = party.serialize_img_id()["photo"][0]["id"]
    img = ImgEvent.query.filter_by(id=image_id).first()
    if not img:
        return failure_response('Img Not Found!', 404)
    return Response(img.img, mimetype=img.mimetype)

@app.route("/api/users/", methods=["POST"])
def add_user():
    body = json.loads(request.data)
    name = body.get("name")
    email = body.get("email")
    age = body.get("age")
    if  not (name or email or age):
        return failure_response("The request is badly formatted.", 400)
    if not valid_email_address(email):
        return failure_response("Email is not valid", 400)
    if age < 21:
        return failure_response("Underage!", 400)
    new_user = User(
        name=name,
        email=email,
        age=age,
        parties = []
    )
    db.session.add(new_user)
    db.session.commit()
    return success_response(new_user.serialize(),
        201
    )

@app.route('/api/user/<int:user_id>/photo/', methods=['POST'])
def upload_photo(user_id):
    user = User.query.filter_by(id=user_id).first()
    if not user:
        return failure_response("User not found")
    pic = request.files['pic']
    if not pic:
        return failure_response('No pic uploaded!', 400)
    filename = secure_filename(pic.filename)
    mimetype = pic.mimetype
    if not filename or not mimetype:
        return failure_response('Bad upload!', 400)
    img = Img(img=pic.read(), name=filename, mimetype=mimetype, user_id = user_id)
    db.session.add(img)
    db.session.commit()
    return success_response('Img Uploaded!', 200)

@app.route('/api/user/<int:user_id>/photo/')
def get_user_img(user_id):
    user = User.query.filter_by(id=user_id).first()
    if not user:
        return failure_response(f"User with ID {user_id} does not exist!")
    image_id = user.serialize_img_id()["photo"][0]["id"]
    img = Img.query.filter_by(id=image_id).first()
    if not img:
        return failure_response('Img Not Found!', 404)
    return Response(img.img, mimetype=img.mimetype)

@app.route("/api/users/")
def get_all_users():
    return success_response(
        {"users":[user.serialize() for user in User.query.all()]}
    )

@app.route("/api/user/<int:user_id>/")
def get_user_by_id(user_id):
    user = User.query.filter_by(id=user_id).first()
    if not user:
        return failure_response(f"User with ID {user_id} does not exist!")
    return success_response(user.serialize())


@app.route("/api/party/<int:party_id>/attend/", methods=["POST"])
def attend_party(party_id):
    body = json.loads(request.data)
    id = body.get("user_id")
    if not id:
        return failure_response(f"The request is badly formatted.")
    user = User.query.filter_by(id=id).first()
    user_id = user.serialize()["id"]
    if not user:
        return failure_response(f"User with ID {user_id} does not exist!")
    party = Party.query.filter_by(id=party_id).first()
    if not party:
        failure_response(f"Party with ID {party_id} does not exist!")
    user.parties.append(party)
    party.users.append(user)
    db.session.commit()
    return success_response(
        party.serialize(),
        200
    )

@app.route("/api/party/<int:party_id>/attendees/")
def get_attendees(party_id):
    party = Party.query.filter_by(id=party_id).first()
    if not party:
        failure_response(f"Party with ID {party_id} does not exist!")
    attendees = party.serialize()["attendees"]
    return success_response(attendees, 200)

@app.route("/api/user/<int:user_id>/parties/")
def get_parties(user_id):
    user = User.query.filter_by(id=user_id).first()
    if not user:
        return failure_response(f"User with ID {user_id} does not exist!")
    parties = user.serialize()["parties"]
    return success_response(parties, 200)

if __name__ == "__main__":
    app.run(host='localhost', port=5000, debug=True)
