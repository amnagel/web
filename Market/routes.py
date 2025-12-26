from Market import app, db
from Market.models import Item, User, CartItem
from Market.forms import RegisterForm, LoginForm, PurchaseItemForm, SellItemForm
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user

@app.route("/")
def HomePage():
    return render_template('HOME.html')

@app.route("/market", methods=['GET', 'POST'])
@login_required
def MarketPage():
    if request.method == "POST":
        # только продажа (sell)
        sold_item_name = request.form.get('sold_item')
        if sold_item_name:
            item_obj = Item.query.filter_by(name=sold_item_name).first()
            if item_obj and current_user.can_sell(item_obj):
                item_obj.sell(current_user)
                db.session.commit()
                flash(f"Congratulations! You sold {item_obj.name} back to market!", category='success')
            else:
                flash(f"Something went wrong with selling {sold_item_name}!", category='danger')

        return redirect(url_for('MarketPage'))

    # GET-запрос — просто показываем товары
    items = Item.query.filter_by(owner=None)
    owned_items = Item.query.filter_by(owner=current_user.id)
    return render_template(
        'MARKET.html',
        title='Market',
        items=items,
        owned_items=owned_items,
        purchase_form=PurchaseItemForm(),
        sell_form=SellItemForm()
    )



@app.route("/add_to_cart/<int:item_id>", methods=['POST'])
@login_required
def add_to_cart(item_id):
    item = Item.query.get_or_404(item_id)

    # Нельзя добавить уже купленный товар
    if item.owner is not None:
        flash("Item is already owned by someone.", "danger")
        return redirect(url_for("MarketPage"))

    # Ищем уже существующую запись в корзине
    cart_item = CartItem.query.filter_by(user_id=current_user.id, item_id=item.id).first()
    if cart_item:
        cart_item.quantity += 1
    else:
        cart_item = CartItem(user_id=current_user.id, item_id=item.id, quantity=1)
        db.session.add(cart_item)

    db.session.commit()
    flash(f"{item.name} added to cart.", "success")
    return redirect(url_for("cart"))






@app.route("/register", methods=['GET', 'POST'])
def RegisterPage():
    form = RegisterForm()
    if form.validate_on_submit():
        create_user = User(username=form.username.data, email_address=form.email_address.data, password=form.password1.data)
        db.session.add(create_user)
        db.session.commit()
        login_user(create_user)
        flash(f'Account created successfully! You are now logged in as: {create_user.username}', category='success')
        return redirect(url_for('MarketPage'))
    
    if form.errors != {}:
        for error in form.errors.values():
            flash(f'There was an error with creating a user: {error}', category='danger')
    return render_template('REGISTER.html', title='Register', form=form)

@app.route("/login", methods=['GET', 'POST'])
def LoginPage():
    form = LoginForm()
    if form.validate_on_submit():
        attempted_user = User.query.filter_by(username=form.username.data).first()
        if attempted_user and attempted_user.password_check(password_attempt=form.password.data):
            login_user(attempted_user)
            flash(f'Success! You are logged in as: {attempted_user.username}', category='success')
            if attempted_user.username == 'admin':
                return redirect(url_for('AdminPage'))
            return redirect(url_for('MarketPage'))
        flash('Username and password are not match! Please try again', category='danger')
    return render_template('LOGIN.html', title='Login', form=form)

@app.route("/admin")
@login_required
def AdminPage():
    if current_user.username != 'admin':
        flash('Please login as admin to access the admin panel!', category='danger')
        return redirect(url_for('LoginPage'))
    return render_template(
        'ADMIN.html',
        title='Admin',
        users=User.query.all(),
        items=Item.query.all()
    )


@app.route("/admin/delete_item/<int:item_id>", methods=["POST"])
@login_required
def admin_delete_item(item_id):
    if current_user.username != "admin":
        flash("Access denied", category="danger")
        return redirect(url_for("LoginPage"))

    item = Item.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    flash("Item deleted", "success")
    return redirect(url_for("AdminPage"))


@app.route("/admin/delete_user/<int:user_id>", methods=["POST"])
@login_required
def admin_delete_user(user_id):
    if current_user.username != "admin":
        flash("Access denied", category="danger")
        return redirect(url_for("LoginPage"))

    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash("User deleted", "success")
    return redirect(url_for("AdminPage"))


@app.route("/admin/user/<int:user_id>/budget", methods=["POST"])
@login_required
def admin_update_user_budget(user_id):
    # доступ только админу
    if current_user.username != "admin":
        flash("Access denied", category="danger")
        return redirect(url_for("LoginPage"))

    user = User.query.get_or_404(user_id)

    new_budget_raw = request.form.get("budget")

    try:
        new_budget = int(new_budget_raw)
    except (TypeError, ValueError):
        flash("Budget must be an integer number.", "danger")
        return redirect(url_for("AdminPage"))

    if new_budget < 0:
        flash("Budget cannot be negative.", "danger")
        return redirect(url_for("AdminPage"))

    user.budget = new_budget
    db.session.commit()
    flash(f"Budget for {user.username} updated to {new_budget} $", "success")
    return redirect(url_for("AdminPage"))



@app.route("/admin/item/<int:item_id>/edit", methods=["GET", "POST"])
@login_required
def admin_update_item(item_id):
    if current_user.username != "admin":
        flash("Access denied", category="danger")
        return redirect(url_for("LoginPage"))

    item = Item.query.get_or_404(item_id)

    if request.method == "POST":
        item.name = request.form.get("name")
        item.price = int(request.form.get("price") or item.price)
        item.barcode = request.form.get("barcode")
        item.description = request.form.get("description")
        db.session.commit()
        flash("Item updated", category="success")
        return redirect(url_for("AdminPage"))

    # страница с формой редактирования
    return render_template("ADMIN_EDIT_ITEM.html", item=item)


@app.route("/admin/item/add", methods=["GET", "POST"])
@login_required
def admin_add_item():
    if current_user.username != "admin":
        flash("Access denied", category="danger")
        return redirect(url_for("LoginPage"))

    if request.method == "POST":
        name = request.form.get("name")
        price = request.form.get("price")
        barcode = request.form.get("barcode")
        description = request.form.get("description")

        if not name or not price or not barcode or not description:
            flash("All fields are required", "danger")
            return redirect(url_for("admin_add_item"))

        try:
            price = int(price)
        except ValueError:
            flash("Price must be a number", "danger")
            return redirect(url_for("admin_add_item"))

        # создаём и сохраняем товар
        item = Item(
            name=name,
            price=price,
            barcode=barcode,
            description=description,
            owner=None,
        )
        db.session.add(item)
        db.session.commit()
        flash("Item created", "success")
        return redirect(url_for("AdminPage"))

    return render_template("ADMIN_ADD_ITEM.html")


@app.route("/logout")
def LogoutPage():
    logout_user()
    flash("You have been logged out!", category='info')
    return redirect(url_for('HomePage'))


@app.route("/cart")
@login_required
def cart():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    total = current_user.cart_total()
    return render_template(
        "CART.html",
        cart_items=cart_items,
        total=total,
        purchase_form=PurchaseItemForm()  # чтобы был hidden_tag()
    )


@app.route("/cart/remove/<int:cart_item_id>", methods=['POST'])
@login_required
def cart_remove(cart_item_id):
    cart_item = CartItem.query.get_or_404(cart_item_id)
    if cart_item.user_id != current_user.id:
        flash("Access denied", "danger")
        return redirect(url_for("cart"))

    db.session.delete(cart_item)
    db.session.commit()
    flash("Item removed from cart.", "info")
    return redirect(url_for("cart"))



@app.route("/cart/update/<int:cart_item_id>", methods=['POST'])
@login_required
def cart_update(cart_item_id):
    cart_item = CartItem.query.get_or_404(cart_item_id)

    # защита: чужую корзину трогать нельзя
    if cart_item.user_id != current_user.id:
        flash("Access denied", "danger")
        return redirect(url_for("cart"))

    qty_raw = request.form.get("quantity")

    try:
        qty = int(qty_raw)
    except (TypeError, ValueError):
        flash("Quantity must be an integer number.", "danger")
        return redirect(url_for("cart"))

    if qty <= 0:
        # если поставили 0 или меньше — просто удаляем позицию
        db.session.delete(cart_item)
        flash("Item removed from cart.", "info")
    else:
        cart_item.quantity = qty
        flash("Quantity updated.", "success")

    db.session.commit()
    return redirect(url_for("cart"))




@app.route("/cart/checkout", methods=['GET', 'POST'])
@login_required
def cart_checkout():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    if not cart_items:
        flash("Cart is empty.", "warning")
        return redirect(url_for("cart"))

    total = current_user.cart_total()

    if request.method == "GET":
        return render_template(
            "CHECKOUT.html",
            cart_items=cart_items,
            total=total,
            purchase_form=PurchaseItemForm(),  # для CSRF
        )

    payment_method = request.form.get("payment_method")
    delivery_method = request.form.get("delivery_method")
    pickup_point = request.form.get("pickup_point") if delivery_method == "pickup" else None
    address = request.form.get("address") if delivery_method == "courier" else None

    # простая валидация
    if payment_method not in ("cash", "card"):
        flash("Choose payment method.", "danger")
        return redirect(url_for("cart_checkout"))

    if delivery_method not in ("pickup", "courier"):
        flash("Choose delivery method.", "danger")
        return redirect(url_for("cart_checkout"))

    if delivery_method == "pickup" and not pickup_point:
        flash("Choose pickup point.", "danger")
        return redirect(url_for("cart_checkout"))

    if delivery_method == "courier" and not address:
        flash("Enter delivery address.", "danger")
        return redirect(url_for("cart_checkout"))

    card_number = request.form.get("card_number") if payment_method == "card" else None
    card_expiry = request.form.get("card_expiry") if payment_method == "card" else None
    card_cvv = request.form.get("card_cvv") if payment_method == "card" else None


    if delivery_method == "pickup" and not pickup_point:
        flash("Choose pickup point.", "danger")
        return redirect(url_for("cart_checkout"))

    if delivery_method == "courier" and not address:
        flash("Enter delivery address.", "danger")
        return redirect(url_for("cart_checkout"))
    if payment_method == "card":
        # card number
        if not card_number:
            flash("Please enter card number.", "danger")
            return redirect(url_for("cart_checkout"))
        clean_num = card_number.replace(" ", "")
        if not clean_num.isdigit() or not (13 <= len(clean_num) <= 19):
            flash("Card number is invalid.", "danger")
            return redirect(url_for("cart_checkout"))

        # expiry date (MM/YY)
        if not card_expiry or "/" not in card_expiry:
            flash("Enter card expiry in MM/YY format.", "danger")
            return redirect(url_for("cart_checkout"))
        month, year = card_expiry.split("/", 1)
        if not (len(month) == 2 and month.isdigit() and 1 <= int(month) <= 12 and
                len(year) == 2 and year.isdigit()):
            flash("Card expiry date is invalid.", "danger")
            return redirect(url_for("cart_checkout"))

        # CVV
        if not card_cvv or not card_cvv.isdigit() or not (3 <= len(card_cvv) <= 4):
            flash("CVV is invalid.", "danger")
            return redirect(url_for("cart_checkout"))

    # Проверяем бюджет
    if current_user.budget < total:
        flash("Not enough budget to complete the purchase.", "danger")
        return redirect(url_for("cart_checkout"))

    # "Создаём заказ": покупаем все товары из корзины
    for ci in cart_items:
        if ci.item.owner is not None:
            flash(f"{ci.item.name} is no longer available.", "danger")
            continue
        ci.item.buy(current_user)

    current_user.clear_cart()
    db.session.commit()

    if delivery_method == "pickup":
        delivery_info = f"Самовывоз: {pickup_point}"
    else:
        delivery_info = f"Курьерская доставка по адресу: {address}"

    pay_info = "наличными" if payment_method == "cash" else "картой"

    flash(f"Заказ оформлен: оплата {pay_info}, {delivery_info}.", "success")
    return redirect(url_for("MarketPage"))


