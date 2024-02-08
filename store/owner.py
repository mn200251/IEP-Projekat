import csv
import io
import json

from flask import Flask, jsonify, request, Response
from configuration import Configuration
from flask_jwt_extended import JWTManager, jwt_required
from models import *
from rolecheck import roleCheck

from sqlalchemy import select, func, case, desc

from models import database

application = Flask(__name__)
application.config.from_object(Configuration)
jwt = JWTManager(application)


@application.route("/update", methods=["POST"])
@roleCheck(role="owner")
def update():
    if not "file" in request.files:
        return jsonify({"message": "Field file is missing."}), 400
    productInfo = request.files["file"].stream.read().decode("utf-8")
    stream = io.StringIO(productInfo)
    reader = csv.reader(stream)
    for count, row in enumerate(reader):
        if len(row) != 3:
            return jsonify({"message": f"Incorrect number of values on line {count}."}), 400
        try:
            if float(row[-1]) <= 0:
                return jsonify({"message": f"Incorrect price on line {count}."}), 400
        except:
            return jsonify({"message": f"Incorrect price on line {count}."}), 400
        prodCheck = Product.query.filter(Product.name == row[1]).first()
        if prodCheck:
            return jsonify({"message": f"Product {row[1]} already exists."}), 400

    stream = io.StringIO(productInfo)
    reader = csv.reader(stream)
    for count, row in enumerate(reader):
        categories = row[0].split("|")
        prod = Product(name=row[1], price=float(row[-1]))
        database.session.add(prod)
        database.session.commit()

        for c in categories:
            exists = Category.query.filter(Category.name == c).first()
            if not exists:
                check = Category(name=c)
                database.session.add(check)
                database.session.commit()

            new_prc = ProductCategories(productName=prod.name, categoryId=(exists.id if exists else check.id))
            database.session.add(new_prc)

    database.session.commit()

    return Response(status=200)


@application.route('/update2', methods=['POST'])
@roleCheck(role="owner")
def update2():
    access_token = request.headers.get('Authorization')
    if not access_token or not access_token.startswith('Bearer '):
        return jsonify({"message": "Missing Authorization Header"}), 401

    if 'file' not in request.files:
        return Response(json.dumps({"message": "Field file is missing."}), status=400)

    file = request.files['file']
    file_list = list()
    try:
        lines = file.read().decode('utf-8').splitlines()
        for line_num, line in enumerate(lines):
            values = line.split(',')
            if len(values) != 3:
                return Response(json.dumps({"message": f"Incorrect number of values on line {line_num}."}), 400)

            categories_str, name, price_str = values
            try:
                price = float(price_str)
                if price <= 0:
                    return Response(json.dumps({"message": f"Incorrect price on line {line_num}."}), 400)
            except ValueError:
                return Response(json.dumps({"message": f"Incorrect price on line {line_num}."}), 400)

            # categories = categories_str.split('|')
            product = Product.query.filter(Product.name == name).first()
            if product:
                return Response(json.dumps({"message": f"Product {name} already exists."}), 400)
            file_list.append(values)

        for val in file_list:

            categories_str, name, price_str = val
            categories = categories_str.split('|')
            # product = Product.query.filter_by(name=name).first()
            # if product:
            #     return jsonResponse( f"Product {name} already exists.", 400)
            price = float(price_str)
            new_product = Product(name=name, price=price)
            for category_name in categories:
                category = Category.query.filter_by(name=category_name).first()
                if category is None:
                    category = Category(name=category_name)
                    database.session.add(category)
                new_product.categories.append(category)

            database.session.add(new_product)

        database.session.commit()
        return Response(status=200)

    except Exception as e:
        return Response(json.dumps({"message": str(e)}), 400)


@application.route("/updateOld", methods=['POST'])
@roleCheck(role="owner")
@jwt_required()
def updateOld():
    # Check for Authorization header
    # if 'Authorization' not in request.headers:
    #     return jsonify({"msg": "Missing Authorization Header"}), 401
    access_token = request.headers.get('Authorization')
    if not access_token or not access_token.startswith('Bearer '):
        return jsonify({"msg": "Missing Authorization Header"}), 401

    # Check if the 'file' field is present in the request body
    if 'file' not in request.files:
        return jsonify({"message": "Field file is missing."}), 400

    file = request.files['file']

    if not file:
        return jsonify({"message": "“Field file is missing"}), 400

    # Start the transaction
    # database.session.begin()

    try:
        for line_number, line in enumerate(file.read().decode("utf-8").splitlines()):
            values = line.split(',')
            if len(values) != 3:
                # print("UMRO!!!!\n\n\n")
                database.session.rollback()
                return jsonify({"message": f"Incorrect number of values on line {line_number}."}), 400

            category_names = values[0].split('|')
            product_name = values[1]

            try:
                product_price = float(values[2])
            except ValueError:
                database.session.rollback()
                return jsonify({"message": f"Incorrect price on line {line_number}."}), 400

            if product_price <= 0:
                # print("UMRO!!!!\n\n\n")
                database.session.rollback()
                return jsonify({"message": f"Incorrect price on line {line_number}."}), 400

            # Check if the product already exists
            existingProduct = Product.query.filter(Product.name == product_name).first()
            if existingProduct:
                # print("UMRO!!!!\n\n\n")
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
    except:
        return Response(status=400)


@application.route("/product_statistics", methods=['GET'])
@roleCheck(role="owner")  # owner
@jwt_required()
def product_statistics():
    access_token = request.headers.get('Authorization')
    if not access_token or not access_token.startswith('Bearer '):
        return jsonify({"msg": "Missing Authorization Header"}), 401

    content = []

    products = database.session.query(
        Product.name,
        func.sum(case([(Order.status == "COMPLETE", OrderProduct.quantity)], else_=0)).label("sold"),
        func.sum(case([(Order.status != "COMPLETE", OrderProduct.quantity)], else_=0)).label("waiting")
    ).join(OrderProduct, OrderProduct.productId == Product.id).join(Order, Order.id == OrderProduct.orderId) \
        .group_by(Product.name).all()

    for product in products:
        currJson = {"name": product.name,
                    "sold": int(product.sold or 0),
                    "waiting": int(product.waiting or 0)
                    }

        content.append(currJson)

    return Response(json.dumps({'statistics': content}), status=200)


@application.route("/category_statistics", methods=['GET'])
@roleCheck(role="owner")  # owner
@jwt_required()
def category_statistics():
    access_token = request.headers.get('Authorization')
    if not access_token or not access_token.startswith('Bearer '):
        return jsonify({"msg": "Missing Authorization Header"}), 401

    content = []

    categories = database.session.query(
        Category.name, func.sum(case([(Order.status == 'COMPLETE', OrderProduct.quantity)]), else_=0).label('product_count')
    ).outerjoin(ProductCategories) \
        .outerjoin(Product) \
        .outerjoin(OrderProduct) \
        .outerjoin(Order) \
        .group_by(Category.name) \
        .order_by(desc('product_count'), Category.name).all()

    for category in categories:
        content.append(category.name)

    return Response(json.dumps({'statistics': content}), status=200)


if __name__ == "__main__":
    database.init_app(application)
    application.run(debug=True, host="0.0.0.0", port=5001)
