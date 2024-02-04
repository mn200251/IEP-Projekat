import datetime

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
    allOrders = Order.query.filter(Order.status == "PENDING").all()

    for order in allOrders:
        orderList.append(jsonify({
            "id": order.id,
            "email": order.orderedBy
        }))

    return jsonify({"orders": orderList}), 200


@application.route("/pick_up_order", methods=['POST'])
@roleCheck(role="courier")
@jwt_required()
def pick_up_order():
    orderId = request.get_json().get("id")

    if not orderId:
        return jsonify({"message": "Missing order id."}), 400

    try:
        orderId = int(orderId)

        if orderId <= 0:
            raise Exception

        currOrder = Order.query.filter(Order.id == orderId).first()

        if not currOrder or currOrder.status != "CREATED":
            raise Exception

    except:
        return jsonify({"message": "Invalid order id."}), 400

    currOrder.status = "PENDING"
    return Response(status=200)


if __name__ == "__main__":
    database.init_app(application)
    application.run(debug=True, host="0.0.0.0", port=5003)
