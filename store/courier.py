import datetime
import json

from flask import Flask, jsonify, request, Response
from configuration import Configuration
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity, get_jwt
from models import *
from rolecheck import roleCheck

from sqlalchemy import select, func, case

from models import database

application = Flask(__name__)
application.config.from_object(Configuration)
jwt = JWTManager(application)


@application.route("/orders_to_deliver", methods=['GET'])
@roleCheck(role="courier")
@jwt_required()
def orders_to_deliver():
    orderList = []
    allOrders = Order.query.filter(Order.status == "CREATED").all()

    for order in allOrders:
        orderList.append(jsonify({
            "id": order.id,
            "email": order.orderedBy
        }))

    # return jsonify({"orders": orderList}), 200
    return Response(json.dumps({"orders": orderList}), 200)


@application.route("/pick_up_order", methods=['POST'])
@roleCheck(role="courier")
def pick_up_order():
    access_token = request.headers.get('Authorization')
    if not access_token or not access_token.startswith('Bearer '):
        return jsonify({"msg": "Missing Authorization Header"}), 401

    try:
        requestObject = request.get_json()
        if "id" not in requestObject.keys():
            return Response(json.dumps({'message': 'Missing order id.'}), status=400)

        data = request.get_json()

        if not data or data is None:
            return Response(json.dumps({'message': 'Missing order id.'}), status=400)

        if 'id' not in data or data["id"] is None:
            return Response(json.dumps({'message': 'Missing order id.'}), status=400)

        orderId = data["id"]

        # return Response(json.dumps({'message': orderId}), status=400)

        if not orderId or orderId is None or orderId == "":
            return Response(json.dumps({'message': 'Missing order id.'}), status=400)

        if not isinstance(orderId, int) or orderId <= 0:
            return Response(json.dumps({'message': 'Invalid order id.'}), status=400)

        currOrder = Order.query.get(orderId)

        if not currOrder or currOrder.status != "CREATED":
            return Response(json.dumps({'message': 'Invalid order id.'}), status=400)

        currOrder.status = "PENDING"

        database.session.commit()

    except:
        return Response(json.dumps({'message': 'Missing order id.'}), status=400)

    return Response(status=200)


if __name__ == "__main__":
    database.init_app(application)
    application.run(debug=True, host="0.0.0.0", port=5003)
