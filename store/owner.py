from flask import Flask, jsonify, request, Response
from configuration import Configuration
from flask_jwt_extended import JWTManager, jwt_required
from models import *
from rolecheck import roleCheck

from sqlalchemy import select, func, case

from models import database

application = Flask(__name__)
application.config.from_object(Configuration)
jwt = JWTManager(application)


@application.route("/update", methods=['POST'])
@roleCheck(role="owner")
@jwt_required()
def update():
    # Check for Authorization header
    # if 'Authorization' not in request.headers:
    #     return jsonify({"msg": "Missing Authorization Header"}), 401

    # Check if the 'file' field is present in the request body
    if 'file' not in request.files:
        return jsonify({"message": "Field file missing."}), 400

    file = request.files['file']

    if not file:
        return jsonify({"message": "“Field file missing"}), 400

    # Start the transaction
    # database.session.begin()

    for line_number, line in enumerate(file.read().decode("utf-8").splitlines()):
        values = line.split(',')
        if len(values) != 3:
            print("UMRO!!!!\n\n\n")
            database.session.rollback()
            return jsonify({"message": f"Incorrect number of values on line {line_number}."}), 400

        category_names = values[0].split('|')
        product_name = values[1]
        product_price = float(values[2])

        if product_price <= 0:
            print("UMRO!!!!\n\n\n")
            database.session.rollback()
            return jsonify({"message": f"Incorrect price on line {line_number}."}), 400

        # Check if the product already exists
        existingProduct = Product.query.filter(Product.name == product_name).first()
        if existingProduct:
            print("UMRO!!!!\n\n\n")
            database.session.rollback()
            return jsonify({"message": f"Product {product_name} already exists."}), 400

        newProduct = Product(name=product_name, price=product_price)
        database.session.add(newProduct)

        # add every category for product
        for category in category_names:
            currCategory = Category.query.filter(name=category).first()

            # create new category if it doesn't previously exist
            if not currCategory:
                currCategory = Category(name=category)
                database.session.add(currCategory)
                database.session.commit()

            database.session.add(ProductCategories(categoryId=currCategory.id, productName=product_name))

    database.session.commit()
    return Response(status=200)


@application.route("/product_statistics", methods=['GET'])
@roleCheck(role="owner")  # owner
@jwt_required()
def product_statistics():
    content = []

    products = database.session.query(
        Product.name,
        func.sum(case([(Order.status == "COMPLETE", OrderProduct.quantity)], else_=0)).label("sold"),
        func.sum(case([(Order.status != "COMPLETE", OrderProduct.quantity)], else_=0)).label("waiting")
    ).join(OrderProduct.productId == Product.id).join(Order.id == OrderProduct.orderId) \
        .group_by(Product.name).all()

    for product in products:
        currJson = jsonify({"name": product.name,
                            "sold": product.sold,
                            "waiting": product.waiting
                            })

        content.append(currJson)

    return jsonify({"statistics": content}), 200


@application.route("/category_statistics", methods=['GET'])
@roleCheck(role="owner")  # owner
@jwt_required()
def category_statistics():
    content = []

    categories = (database.session.query(
        Category.name, func.sum(case([()]))
    ).join(Category.id == ProductCategories.categoryId).join(ProductCategories.productName == Product.name)\
                  .group_by(Category.name)\
                  .order_by(func.count(ProductCategories.productName).desc(), Category.name).all())

    for category in categories:
        currJson = jsonify({"name": category.name})

        content.append(currJson)

    return jsonify({"statistics": content}), 200


if __name__ == "__main__":
    database.init_app(application)
    application.run(debug=True, host="0.0.0.0", port=5001)
