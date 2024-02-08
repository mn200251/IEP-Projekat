import datetime
import json
from datetime import datetime

from flask import Flask, jsonify, request, Response
from configuration import Configuration
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity, get_jwt
from models import *
from rolecheck import roleCheck

from flask import Flask, request, Response, jsonify
from configuration import Configuration
from models import *
from flask_jwt_extended import JWTManager, get_jwt_identity
from sqlalchemy import and_, or_
import json

from sqlalchemy import select, func, case, and_, or_

from models import database

application = Flask(__name__)
application.config.from_object(Configuration)
jwt = JWTManager(application)


@application.route("/search", methods=['GET'])
@roleCheck(role="customer")
def search():
    try:
        product_name = request.args.get('name', "")
        category_name = request.args.get('category', "")

        categories = []
        products = []

        categories = Category.query.all() if not category_name \
            else Category.query.filter(Category.name.like("%" + category_name + "%")).all()

        categoryIds = [cat.id for cat in categories]

        products = (Product.query.join(ProductCategories).filter(
            Product.name.like("%" + product_name + "%"),
            ProductCategories.categoryId.in_(categoryIds), ).all()
                    ) if product_name and len(product_name) > 0 \
            else Product.query.join(ProductCategories).filter(ProductCategories.categoryId.in_(categoryIds)).all()

        # threads = Thread.query.join ( ThreadTag ).join ( Tag ).filter (
        #         or_ (
        #                 *[Tag.name == tag for tag in tags]
        #         )
        # threads = Thread.query.filter (
        #         and_ (
        #                 *[Thread.title.like ( f"%{word}%" ) for word in words]
        #         )

        # categories = Category.query.filter(Category.name.ilike(f'%{category_name}%')).all()
        # products = Product.query.filter(Product.name.ilike(f"%{product_name}")).all()

        filtered_category_ids = list(
            set([pc.id for prod in products for pc in prod.categories])
        )

        filtered_categories = [
            cat for cat in categories if cat.id in filtered_category_ids
        ]

        result_data = {
            "categories": [cat.name for cat in filtered_categories],
            "products": [
                {
                    "categories": [cat.name for cat in prod.categories],
                    "id": prod.id,
                    "name": prod.name,
                    "price": prod.price,
                }
                for prod in products
            ],
        }

        return Response(json.dumps(result_data), status=200)

    except Exception as error:
        return Response(json.dumps(str(error)), status=401)


@application.route("/order", methods=['POST'])
@roleCheck(role="customer")
def order():
    access_token = request.headers.get('Authorization')
    if not access_token or not access_token.startswith('Bearer '):
        return jsonify({"msg": "Missing Authorization Header"}), 401

    if "requests" not in request.json:
        return {"message": "Field requests is missing."}, 400

    reqeusts = request.json["requests"]

    identity = get_jwt_identity()
    # refreshClaims = get_jwt()
    # refreshClaims["forename"]

    for i, req in enumerate(reqeusts):
        if "id" not in req:
            return {"message": f"Product id is missing for request number {i}."}, 400
        if "quantity" not in req:
            return {"message": f"Product quantity is missing for request number {i}."}, 400

        productId = req["id"]
        if not isinstance(productId, int) or productId <= 0:
            return {"message": f"Invalid product id for request number {i}."}, 400

        quantity = req["quantity"]
        if not isinstance(quantity, int) or quantity <= 0:
            return {"message": f"Invalid product quantity for request number {i}."}, 400

        check = Product.query.filter(Product.id == productId).first()

        if not check:
            return {"message": f"Invalid product for request number {i}."}, 400

    newOrder = Order(price=0, dateCreated=datetime.utcnow(), status="CREATED", orderedBy=identity)
    # database.session.add(newOrder)
    # database.session.commit()

    for req in reqeusts:
        productId = req["id"]
        product = Product.query.get(productId)
        newOrder.products.append(product)

    database.session.add(newOrder)
    database.session.commit()

    for req in reqeusts:
        productId = req["id"]
        quantity = req["quantity"]

        product = Product.query.get(productId)
        OrderProduct.query.filter_by(
            productId=product.id, orderId=newOrder.id
        ).first().quantity = quantity

    database.session.commit()
    newOrder.calculate_total_price()
    database.session.commit()

    return jsonify({"id": newOrder.id}), 200


def format_order_response(all_orders):
    def format_product_response(product, order_id):
        order_product = (
            OrderProduct.query.filter_by(orderId=order_id, productId=product.id)
            .first()
        )
        return {
            "categories": [category.name for category in product.categories],
            "name": product.name,
            "price": float(product.price),
            "quantity": order_product.quantity,
        }

    def format_order(order):
        return {
            "products": [format_product_response(product, order.id) for product in order.products],
            "price": order.price,
            "status": order.status,
            "timestamp": order.dateCreated.isoformat(),
        }

    formatted_response = {"orders": [format_order(order) for order in all_orders]}
    return formatted_response


@application.route("/status", methods=['GET'])
@roleCheck(role="customer")
@jwt_required()
def status():
    access_token = request.headers.get('Authorization')
    if not access_token or not access_token.startswith('Bearer '):
        return jsonify({"msg": "Missing Authorization Header"}), 401

    orderList = []
    identity = get_jwt_identity()

    allOrders = Order.query.filter(Order.orderedBy == identity).all()

    response = format_order_response(allOrders)
    return jsonify(response), 200


@application.route("/delivered", methods=['POST'])
@roleCheck(role="customer")
def delivered():
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

        if not orderId or orderId is None:
            return Response(json.dumps({'message': 'Missing order id.'}), status=400)

        if not isinstance(orderId, int) or orderId <= 0:
            return Response(json.dumps({'message': 'Invalid order id.'}), status=400)

        currOrder = Order.query.get(orderId)

        if not currOrder or currOrder.status != "PENDING":
            return Response(json.dumps({'message': 'Invalid order id.'}), status=400)

        currOrder.status = "COMPLETE"

        database.session.commit()

    except:
        return Response(json.dumps({'message': 'Missing order id.'}), status=400)

    return Response(status=200)


if __name__ == "__main__":
    database.init_app(application)
    application.run(debug=True, host="0.0.0.0", port=5002)
