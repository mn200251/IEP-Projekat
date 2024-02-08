from flask_sqlalchemy import SQLAlchemy

database = SQLAlchemy()


# Order status
# CREATED
# PENDING
# COMPLETE


class ProductCategories(database.Model):
    __tablename__ = "productcategories"

    # id = database.Column(database.Integer, primary_key=True)
    categoryId = database.Column(database.Integer, database.ForeignKey("category.id"), primary_key=True)
    productName = database.Column(database.String(256), database.ForeignKey("product.name"), primary_key=True)


class OrderProduct(database.Model):
    __tablename = "orderproduct"

    orderId = database.Column(database.Integer, database.ForeignKey('order.id'), primary_key=True)
    productId = database.Column(database.Integer, database.ForeignKey('product.id'), primary_key=True)
    quantity = database.Column(database.Integer, nullable=False, default=1)


class Product(database.Model):
    __tablename__ = "product"

    id = database.Column(database.Integer, primary_key=True)
    name = database.Column(database.String(256), unique=True)
    price = database.Column(database.Float, nullable=False)

    categories = database.relationship("Category", secondary=ProductCategories.__table__, back_populates="products")
    orders = database.relationship("Order", secondary=OrderProduct.__table__, back_populates="products")


class Category(database.Model):
    __tablename__ = "category"

    id = database.Column(database.Integer, primary_key=True)
    name = database.Column(database.String(256), nullable=False)

    products = database.relationship("Product", secondary=ProductCategories.__table__, back_populates="categories")




class Order(database.Model):
    __tablename__ = "order"

    id = database.Column(database.Integer, primary_key=True)
    price = database.Column(database.Float, nullable=False)
    dateCreated = database.Column(database.DateTime, nullable=False)
    status = database.Column(database.String(256))

    products = database.relationship("Product", secondary=OrderProduct.__table__, back_populates="orders")

    orderedBy = database.Column(database.String(256), nullable=False)

    def calculate_total_price(self):
        self.price = 0
        for product in self.products:
            orderProduct = OrderProduct.query.filter_by(orderId=self.id, productId=product.id).first()
            self.price += orderProduct.quantity * product.price
