import datetime

from flask import Flask, jsonify, request, Response
from configuration import Configuration
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity, get_jwt
from models import *
from rolecheck import roleCheck

from sqlalchemy import select, func, case, and_, or_

from models import database

application = Flask(__name__)
application.config.from_object(Configuration)
jwt = JWTManager(application)


@application.route("/search?name=<PRODUCT_NAME>&category=<CATEGORY_NAME>", methods=['GET'])
@roleCheck(role="customer")
@jwt_required()
def search(name, category):
    categoryList = []
    productList = []

    product_name = request.args.get('name')
    category_name = request.args.get('category')

    # threads = Thread.query.join ( ThreadTag ).join ( Tag ).filter (
    #         or_ (
    #                 *[Tag.name == tag for tag in tags]
    #         )
    # threads = Thread.query.filter (
    #         and_ (
    #                 *[Thread.title.like ( f"%{word}%" ) for word in words]
    #         )

    categories = Category.query.filter(Category.name.ilike(f'%{category_name}%')).all()
    products = Product.query.filter(Product.name.ilike(f"%{product_name}")).all()

    for currCategory in categories:
        categoryList.append(currCategory.name)

    for currProduct in products:
        currProductCategoriesList = []
        for currProductCategory in currProduct.categories:
            currProductCategoriesList.append(currProductCategory.name)

        productList.append(jsonify({
            "categories": currProductCategoriesList,
            "id": currProduct.id,
            "name": currProduct.name,
            "price": currProduct.price
        }))

    return jsonify({
        "categories": categoryList,
        "products": productList
    })


@application.route("/order", methods=['POST'])
@roleCheck(role="customer")
@jwt_required()
def order():
    # products = request.json["requests"]
    products = request.json.get("requests", "")

    if not products:
        return jsonify({"message": "Field requests missing"}), 400

    identity = get_jwt_identity()
    # refreshClaims = get_jwt()
    # refreshClaims["forename"]

    database.session.begin()

    newOrder = Order(price=0, dateCreated=datetime.datetime.now(), status="cekanje", orderedBy=identity)
    database.session.add(newOrder)

    i = 0
    for prod in products:
        # try:
        #     prodId = prod["id"]
        # except:
        #     database.session.rollback()
        #     return jsonify({"message": f"“Product id is missing for request number {i}."}), 400

        # try:
        #     prodQuantity = prod["quantity"]
        # except:
        #     database.session.rollback()
        #     return jsonify({"message": f"Product quantity is missing for request number {i}."}), 400

        prodId = prod.get("id")
        if not prodId:
            database.session.rollback()
            return jsonify({"message": f"Product id is missing for request number {i}."}), 400

        prodQuantity = prod.get("quantity")
        if not prodQuantity:
            database.session.rollback()
            return jsonify({"message": f"Product quantity is missing for request number {i}."}), 400

        if type(prodId) != int and int(prodId) <= 0:
            database.session.rollback()
            return jsonify({"message": f"Invalid product id for request number {i}."}), 400
        prodId = int(prodId)

        if type(prodQuantity) != int and int(prodQuantity) <= 0:
            database.session.rollback()
            return jsonify({"message": f"Invalid product quantity for request number {i}."}), 400
        prodQuantity = int(prodQuantity)

        currProduct = Product.query.filter(Product.id == prodId).first()

        if not currProduct:
            database.session.rollback()
            return jsonify({"message": f"Invalid product for request number {i}."}), 400

        currOrderProduct = OrderProduct(productId=currProduct.id, orderId=newOrder.id, quantity=prodQuantity)
        database.session.add(currOrderProduct)

        i += 1

    newOrder.calculate_total_price()
    # database.session.add(newOrder)
    database.session.commit()
    return jsonify({"id": newOrder.id}), 200


@application.route("/status", methods=['GET'])
@roleCheck(role="customer")
@jwt_required()
def status():
    orderList = []
    identity = get_jwt_identity()

    allOrders = Order.query.filter(Order.orderedBy == identity).all()

    for currOrder in allOrders:
        productList = []
        categoryList = []
        for currProduct in currOrder.products:
            for currCategory in currProduct.categories:
                categoryList.append(currCategory.name)

            quantity = OrderProduct.query.filter(OrderProduct.productId == currProduct.id, OrderProduct.orderId == currOrder.id).first().quantity
            productList.append(jsonify(
                {
                    "categories": categoryList,
                    "name": currProduct.name,
                    "price": currProduct.price,
                    "quantity": quantity
                }
            ))

        orderList.append(jsonify(
            {
                "products": productList,
                "price": currOrder.price,
                "status": currOrder.status,
                "timestamp": currOrder.dateCreated
            }
        ))

    return jsonify({"orders": orderList}), 200


@application.route("/delivered", methods=['POST'])
@roleCheck(role="customer")
@jwt_required()
def delivered():
    orderId = request.get_json().get("id")

    if not orderId:
        return jsonify({"message": "Missing order id."}), 400

    try:
        orderId = int(orderId)

        if orderId <= 0:
            raise Exception

        currOrder = Order.query.filter(Order.id == orderId).first()

        if not currOrder or currOrder.status != "PENDING":
            raise Exception

    except:
        return jsonify({"message": "Invalid order id."}), 400

    currOrder.status = "COMPLETE"
    return Response(status=200)


if __name__ == "__main__":
    database.init_app(application)
    application.run(debug=True, host="0.0.0.0", port=5002)








