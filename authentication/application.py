import json
import re

from flask import Flask, request, Response, jsonify
from configuration import Configuration
from models import database, User
from email.utils import parseaddr
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, create_refresh_token, get_jwt, \
    get_jwt_identity
from sqlalchemy import and_

application = Flask(__name__)
application.config.from_object(Configuration)


@application.route("/", methods=["GET"])
def index():
    return "Hello world"


def checkEmail(email):
    pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'
    if re.match(pattern, email):
        return True
    return False

@application.route("/register_customer", methods=["POST"])
def register_customer():
    email = request.json.get("email", "")
    password = request.json.get("password", "")
    forename = request.json.get("forename", "")
    surname = request.json.get("surname", "")

    emailEmpty = len(email) == 0
    passwordEmpty = len(password) == 0
    forenameEmpty = len(forename) == 0
    surnameEmpty = len(surname) == 0

    if forenameEmpty:
        return Response(json.dumps({"message": "Field forename is missing."}), status=400)
    if surnameEmpty:
        return Response(json.dumps({"message": "Field surname is missing."}), status=400)
    if emailEmpty:
        return Response(json.dumps({"message": "Field email is missing."}), status=400)
    if passwordEmpty:
        return Response(json.dumps({"message": "Field password is missing."}), status=400)


    # result = parseaddr(email)
    # if len(result[1]) == 0:
    #     return Response(json.dumps({"message": "Invalid email."}), status=400)

    result = checkEmail(email)
    if (not result):
        return Response(json.dumps({"message": "Invalid email."}), status=400)

    if len(password) < 8:
        return Response(json.dumps({"message": "Invalid password."}), status=400)

    # check if email already exists
    user = User.query.filter(User.email == email).first()

    if user:
        return Response(json.dumps({"message": "Email already exists."}), status=400)
    user = User(email=email, password=password, forename=forename, surname=surname, role="customer")
    database.session.add(user)
    database.session.commit()

    return Response(status=200)


@application.route("/register_courier", methods=["POST"])
def register_courier():
    email = request.json.get("email", "")
    password = request.json.get("password", "")
    forename = request.json.get("forename", "")
    surname = request.json.get("surname", "")

    emailEmpty = len(email) == 0
    passwordEmpty = len(password) == 0
    forenameEmpty = len(forename) == 0
    surnameEmpty = len(surname) == 0


    if forenameEmpty:
        return Response(json.dumps({"message": "Field forename is missing."}), status=400)
    if surnameEmpty:
        return Response(json.dumps({"message": "Field surname is missing."}), status=400)
    if emailEmpty:
        return Response(json.dumps({"message": "Field email is missing."}), status=400)
    if passwordEmpty:
        return Response(json.dumps({"message": "Field password is missing."}), status=400)


    # result = parseaddr(email)
    # if len(result[1]) == 0:
    #     return Response(json.dumps({"message": "Invalid email."}), status=400)

    result = checkEmail(email)
    if (not result):
        return Response(json.dumps({"message": "Invalid email."}), status=400)

    if len(password) < 8:
        return Response(json.dumps({"message": "Invalid password."}), status=400)

    # check if email already exists
    user = User.query.filter(User.email == email).first()

    if user:
        return Response(json.dumps({"message": "Email already exists."}), status=400)

    user = User(email=email, password=password, forename=forename, surname=surname, role="courier")
    database.session.add(user)
    database.session.commit()

    return Response(status=200)


jwt = JWTManager(application)


@application.route("/login", methods=["POST"])
def login():
    email = request.json.get("email", "")
    password = request.json.get("password", "")

    emailEmpty = len(email) == 0
    passwordEmpty = len(password) == 0


    if emailEmpty:
        return Response(json.dumps({"message": "Field email is missing."}), status=400)
    if passwordEmpty:
        return Response(json.dumps({"message": "Field password is missing."}), status=400)

    # result = parseaddr(email)
    # if len(result[1]) == 0:
    #     return Response(json.dumps({"message": "Invalid email."}), status=400)

    result = checkEmail(email)
    if (not result):
        return Response(json.dumps({"message": "Invalid email."}), status=400)

    user = User.query.filter(and_(User.email == email, User.password == password)).first()

    if not user:
        return Response(json.dumps({"message": "Invalid credentials."}), status=400)

    additionalClaims = {
        "forename": user.forename,
        "surname": user.surname,
        "roles": user.role
    }

    accessToken = create_access_token(identity=user.email, additional_claims=additionalClaims)
    # refreshToken = create_refresh_token(identity=user.email, additional_claims=additionalClaims)

    # return Response ( accessToken, status = 200 );
    return jsonify(accessToken=accessToken)


@application.route("/delete", methods=["POST"])
@jwt_required()
def delete():
    identity = get_jwt_identity()
    refreshClaims = get_jwt()

    # valjda je dobro trazenje usera
    user = User.query.filter(User.email == identity).first()

    if not user:
        return Response(json.dumps({"message": "Unknown user."}), status=400)

    database.session.delete(user)
    database.session.commit()

    return Response(status=200)


if __name__ == "__main__":
    database.init_app(application)
    application.run(debug=True, host="0.0.0.0", port=5000)
