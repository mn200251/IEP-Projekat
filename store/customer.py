import datetime
import json

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


@application.route("/searchFilip", methods=["GET"])
@roleCheck(role="customer")
def searchFilip():
    product_name = request.args.get('name')
    category_name = request.args.get('category')

    filter_conditions = []

    if product_name:
        filter_conditions.append(Product.name.contains(product_name))

    if category_name:

        subquery = database.session.query(Product.id).join(ProductCategories).join(Category).filter(
            Category.name.contains(category_name)).subquery()
        filter_conditions.append(Product.id.in_(subquery))

    final_filter = and_(*filter_conditions)
    products = database.session.query(Product).filter(final_filter).all()
    matching_categories = {category.name for product in products for category in product.categories}
    response = {
        "categories": list(matching_categories),
        "products": [
            {
                "categories": [category.name for category in product.categories],
                "id": product.id,
                "name": product.name,
                "price": product.price
            }
            for product in products
        ]
    }

    return jsonify(response), 200

@application.route("/searchAmela", methods=["GET"])
@roleCheck("customer")
def searchAmela():

    try:
        name = request.args.get("name", None)
        category = request.args.get("category", None)

        if category is None or len(category) == 0:
            searchCategories = Category.query.all()
        else:
            searchCategories = Category.query.filter(
                Category.name.like("%" + category + "%")
            ).all()

        category_ids = [category.id for category in searchCategories]

        if name is None or len(name) == 0:
            searchProducts = (
                Product.query.join(ProductCategories)
                .filter(ProductCategories.categoryId.in_(category_ids))
                .all()
            )
        else:
            searchProducts = (
                Product.query.join(ProductCategories)
                .filter(
                    Product.name.like("%" + name + "%"),
                    ProductCategories.categoryId.in_(category_ids),
                )
                .all()
            )

        filtered_category_ids = list(
            set([pc.id for prod in searchProducts for pc in prod.categories])
        )
        filtered_categories = [
            cat for cat in searchCategories if cat.id in filtered_category_ids
        ]

        resultObject = {
            "categories": [cat.name for cat in filtered_categories],
            "products": [
                {
                    "categories": [cat.name for cat in prod.categories],
                    "id": prod.id,
                    "name": prod.name,
                    "price": prod.price,
                }
                for prod in searchProducts
            ],
        }

        return Response(json.dumps(resultObject), status=200)

    except Exception as e:
        return Response(json.dumps(str(e)), status=401)


@application.route("/search", methods=['GET'])
@roleCheck(role="customer")
@jwt_required()
def search():
    access_token = request.headers.get('Authorization')
    if not access_token or not access_token.startswith('Bearer '):
        return jsonify({"msg": "Missing Authorization Header"}), 401

    categoryList = []
    productList = []

    try:
        product_name = request.args.get('name', "")
        category_name = request.args.get('category', "")

        categories = []
        products = []

        if category_name == "":
            categories = Category.query.all()
        else:
            categories = Category.query.filter(Category.name.like("%" + category_name + "%")).all()

        if product_name == "":
            products = Product.query.all()
        else:
            products = Product.query.filter(Product.name.like("%" + product_name + "%")).all()

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

        for currCategory in categories:
            categoryList.append(currCategory.name)

        for currProduct in products:
            currProductCategoriesList = []
            for currProductCategory in currProduct.categories:
                if currProductCategory.name in currProduct.categories:
                    currProductCategoriesList.append(currProductCategory.name)

            productList.append({
                "categories": currProductCategoriesList,
                "id": currProduct.id,
                "name": currProduct.name,
                "price": currProduct.price
            })

        return jsonify({
            "categories": categoryList,
            "products": productList
        })

    except:
        return Response(status=401)

@application.route("/order", methods=['POST'])
@roleCheck(role="customer")
@jwt_required()
def order():
    access_token = request.headers.get('Authorization')
    if not access_token or not access_token.startswith('Bearer '):
        return jsonify({"msg": "Missing Authorization Header"}), 401

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
    access_token = request.headers.get('Authorization')
    if not access_token or not access_token.startswith('Bearer '):
        return jsonify({"msg": "Missing Authorization Header"}), 401

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
    access_token = request.headers.get('Authorization')
    if not access_token or not access_token.startswith('Bearer '):
        return jsonify({"msg": "Missing Authorization Header"}), 401

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
