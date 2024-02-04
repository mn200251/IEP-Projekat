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

    if emailEmpty:
        return Response("Field email is missing.", status=400)
    if passwordEmpty:
        return Response("Field password is missing.", status=400)
    if forenameEmpty:
        return Response("Field forename is missing.", status=400)
    if surnameEmpty:
        return Response("Field surname is missing.", status=400)

    result = parseaddr(email)
    if len(result[1]) == 0:
        return Response("“Invalid email.", status=400)

    if len(password) < 8:
        return Response("“Invalid password.", status=400)

    # check if email already exists
    user = User.query.filter(User.email == email).first()

    if user:
        return Response("Email already exists.", status=400)
    user = User(email=email, password=password, forename=forename, surname=surname, role="buyer")
    database.session.add(user)
    database.session.commit()

    return Response("Registration successful!", status=200)


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

    if emailEmpty:
        return Response("Field email is missing.", status=400)
    if passwordEmpty:
        return Response("Field password is missing.", status=400)
    if forenameEmpty:
        return Response("Field forename is missing.", status=400)
    if surnameEmpty:
        return Response("Field surname is missing.", status=400)

    result = parseaddr(email)
    if len(result[1]) == 0:
        return Response("“Invalid email.", status=400)

    if len(password) < 8:
        return Response("“Invalid password.", status=400)

    # check if email already exists
    user = User.query.filter(User.email == email).first()

    if user:
        return Response("Email already exists.", status=400)

    user = User(email=email, password=password, forename=forename, surname=surname, role="courier")
    database.session.add(user)
    database.session.commit()

    return Response("Registration successful!", status=200)


jwt = JWTManager(application)


@application.route("/login", methods=["POST"])
def login():
    email = request.json.get("email", "")
    password = request.json.get("password", "")

    emailEmpty = len(email) == 0
    passwordEmpty = len(password) == 0

    if emailEmpty:
        return Response("Field email is missing.", status=400)
    if passwordEmpty:
        return Response("Field password is missing.", status=400)

    result = parseaddr(email)
    if len(result[1]) == 0:
        return Response("“Invalid email.", status=400)

    user = User.query.filter(and_(User.email == email, User.password == password)).first()

    if not user:
        return Response("Invalid credentials!", status=400)

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
        return Response("Unknown user.", status=400)

    database.session.delete(user)
    database.session.commit()

    return Response(status=200)


if __name__ == "__main__":
    database.init_app(application)
    application.run(debug=True, host="0.0.0.0", port=5000)
