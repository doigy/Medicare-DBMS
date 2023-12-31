from flask import Flask,render_template, request, session, redirect, url_for, send_file
from flask_session import Session
from werkzeug.utils import secure_filename
from flask_mysqldb import MySQL
from datetime import datetime, timedelta, date
from pygal.style import Style
from threading import Timer
from barcode.writer import ImageWriter
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor
from datetime import datetime
from barcode.codex import Code128
from barcode.ean import EAN8
import uuid, pygal, secrets, string, os, pathlib, webbrowser, bcrypt


app = Flask(__name__)
app.secret_key = str(uuid.uuid4().hex[:20])

# connecting to mysql db hosted on aws rds
app.config["SESSION_TYPE"] = "filesystem"
app.config['MYSQL_HOST'] = 'dbms-project.chenoax9owcu.eu-north-1.rds.amazonaws.com'
app.config['MYSQL_PORT'] = 3306
app.config['MYSQL_USER'] = 'admin'
app.config['MYSQL_PASSWORD'] = 'jaa722bpe711'
app.config['MYSQL_DB'] = 'sys'
mysql = MySQL(app)

# using hardcoded salt aka pepper to hash passwords entered
salt = b'$2b$12$mxoSXnFyH/St6P0Nq2APQe'

# generate cartid and customerid
cart_id = '1' + ''.join(secrets.choice(string.digits) for i in range(7))
customer_id = ''.join(secrets.choice(string.digits) for i in range(8))

# style for graph
custom_style = Style(
	background = '#EEEEEE',
	plot_background = '#EEEEEE',
	value_font_size = 1,
	label_font_size = 0.5,
	foreground = '#1A1A1A',
	foreground_strong = '#1A1A1A',
	foreground_subtle = '#1A1A1A',
	colors = ('#11c535', '#FF9E00'))


@app.route('/')
def Login():
	error = 'none'

	# already logged in redirect to home page
	if session.get('login_token'):
		login_token = session.get('login_token')
		return redirect(url_for('Home', login_token = login_token))

	# not logged in render login page
	login_token = ''
	session['login_token'] = login_token

	return render_template('Login.html', error = error)


@app.route('/', methods = ['GET', 'POST'])
def Login_post():
	# get user entered username and password
	username_entry = request.form['usernameentry']
	password_entry = request.form['passwordentry']
	error = 'none'

	# if username or password not entered throw error and render login page again
	if username_entry == '' or password_entry == '':
		error = 'missing input/s'

		login_token = ''
		session['login_token'] = login_token

		return render_template('Login.html', error = error)

	else:
		pass

	# creating a connection cursor
	cursor = mysql.connection.cursor()

	# employees database query check name and pass
	cursor.execute(''' SELECT EmployeeName FROM Employees ''')
	accounts_db_data = cursor.fetchall()

	# employee entry validation
	for accounts_data_username in accounts_db_data:
		for empname in accounts_data_username:
			if username_entry == empname:

				# get stored password hash from file
				password_file = open('bin/authenticate.bin', 'rb')
				password_stored_hash = password_file.read()
				password_file.close()

				# encode entered password
				password_entry = password_entry.encode()

				# hash entered password using salt
				password_entry_hash = bcrypt.hashpw(password_entry, salt)

				# if entred password hash and stored password hash equal
				if password_stored_hash == password_entry_hash:
					# get employee id
					cursor.execute(''' SELECT EmployeeID FROM Employees WHERE EmployeeName = %s ''', (empname,))
					emp_id_data = cursor.fetchall()
					for emp_id_tuple in emp_id_data:
						for eid in emp_id_tuple:
							emp_id = eid

					cursor.close()

					error = 'inputs verified'

					# generate login token
					login_token = str(uuid.uuid4().hex[:20])

					session['login_token'] = login_token
					session['emp_id'] = emp_id

					return redirect(url_for('Home', login_token = login_token))

				else:
					error = "invalid input/s"

			else:
				error = "invalid input/s"
	
	login_token = ''
	session['login_token'] = login_token

	cursor.close()

	return render_template('login.html', error = error)


@app.route('/logout')
def Logout():
	#LOGIN TOKEN VALIDATION
	login_token = session.get('login_token')
	if login_token == '':
		return redirect(f'http://localhost:5000/')

	login_token = ''
	session['login_token'] = login_token
	error = 'logged out'

	return redirect(url_for('Login', error = error))


@app.route('/home/<login_token>')
def Home(login_token):
	#LOGIN TOKEN VALIDATION
	login_token = session.get('login_token')
	if login_token == '':
		return redirect(f'http://localhost:5000/')

	error = 'none'
	dashboard_data = []
	sold_items = []
	record_months_graph = []
	gross_profits_graph = []
	most_selling_item_name = ''
	least_selling_item_name = ''
	sold_items = []
	sales_graph = []
	quantities = []
	refund_ids = []

	# creating a connection cursor
	cursor = mysql.connection.cursor()

	# calculating total number of items sold
	cursor.execute(''' SELECT Quantity FROM Cart ''')
	number_of_items_sold = cursor.fetchall()	
	total_items_sold = sum(list(map(sum, number_of_items_sold)))
	# calculating total number of items in inventory
	cursor.execute(''' SELECT Quantity FROM Inventory ''')
	number_of_items_bought = cursor.fetchall()
	total_items_bought = sum(list(map(sum, number_of_items_bought)))
	# calculate sell through percentage [sold/bought * 100]
	try:
		sell_through = round((total_items_sold / total_items_bought) * 100, 2)
	except ZeroDivisionError:
		sell_through = 0

	# append to dashboard data list
	dashboard_data.append(sell_through)

	# get total sale prices from cart
	cursor.execute(''' SELECT TotalSalePrice FROM Cart ''')
	sales = cursor.fetchall()	
	for sales_tuple in sales:
		for sales_value in sales_tuple:
			sales_graph.append(sales_value)
	# calculate average transaction value [total sales / number of sales]
	try:
		average_transaction = sum(sales_graph) / len(sales_graph)
	except ZeroDivisionError:
		average_transaction = 0
	# append to dashboard data list
	dashboard_data.append(average_transaction)

	# get quantities for cart
	cursor.execute(''' SELECT Quantity FROM Cart ''')
	sales_quantities = cursor.fetchall()	
	for sales_qty_tuple in sales_quantities:
		for sales_quantities_value in sales_qty_tuple:
			quantities.append(sales_quantities_value)
	# calculate average transaction quantity [total quantities / number of sales]
	try:
		average_transaction_qty = sum(quantities) / len(quantities)
	except ZeroDivisionError:
		average_transaction_qty = 0
	# append to dashboard data list
	dashboard_data.append(average_transaction_qty)

	# append to dashboard data list
	dashboard_data.append(total_items_bought)
	dashboard_data.append(total_items_sold)

	# inventory database query get item unit sale price
	cursor.execute(''' SELECT TotalSalePrice FROM Cart ''')
	total_sale_prices = cursor.fetchall()
	# item unit sale price from tuple to float
	total_sale_prices_value = sum(list(map(sum, total_sale_prices)))

	# append to dashboard data list
	dashboard_data.append(total_sale_prices_value)

	cursor.execute(''' SELECT DISTINCT CartID FROM Cart WHERE LEFT(CartID, 1) = 4 ''')
	refunds = cursor.fetchall()
	for refund_tuple in refunds:
		for refund in refund_tuple:
			refund_ids.append(refund)

	dashboard_data.append(refund_ids)

	# create line graph
	graph = pygal.Line(style = custom_style)
	graph.add('sales', sales_graph)
	graph_data = graph.render_data_uri()

	# inventory database query get item stock low id
	cursor.execute(''' SELECT ProductID, ProductName, Quantity FROM Inventory WHERE Quantity <= 5 ''')
	stock_low = cursor.fetchall()

	# cart database query get most selling and least selling item id
	cursor.execute('SELECT ProductID FROM Cart')
	sold_items_data = cursor.fetchall()
	for sold_items_tuple in sold_items_data:
		for sold_items_value in sold_items_tuple:
			sold_items.append(sold_items_value)
	sold_items_dict = {i:sold_items.count(i) for i in sold_items}
	try:
		most_selling_item_id = max(sold_items_dict)
		least_selling_item_id = min(sold_items_dict)
	except:
		most_selling_item_id = ''
		least_selling_item_id = ''
	# cart database query get most selling and least selling item name
	cursor.execute('SELECT ProductName FROM Inventory WHERE ProductID = %s', (most_selling_item_id,))
	most_selling_item_name_data = cursor.fetchall()
	for most_name_tuple in most_selling_item_name_data:
		for most_name in most_name_tuple:
			most_selling_item_name = most_name
	cursor.execute('SELECT ProductName FROM Inventory WHERE ProductID = %s', (least_selling_item_id,))
	least_selling_item_name_data = cursor.fetchall()
	for least_name_tuple in least_selling_item_name_data:
		for least_name in least_name_tuple:
			least_selling_item_name = least_name

	# display financial summaries for viewing
	financial_summaries = [f for f in os.listdir('financial-summaries') if os.path.isfile(os.path.join('financial-summaries', f)) and f.endswith('.pdf')]

	cursor.close()

	# get Closing time from ClosingTime file
	closing_time_file = open('bin/ClosingTime.bin', 'rb')
	closing_time = closing_time_file.read().decode()
	closing_time_file.close()

	session['cart_id'] = cart_id
	session['customer_id'] = customer_id
	session['dashboard_data'] = dashboard_data
	session['most_selling_item_id'] = most_selling_item_id
	session['least_selling_item_id'] = least_selling_item_id
	session['most_selling_item_name'] = most_selling_item_name
	session['least_selling_item_name'] = least_selling_item_name
	session.modified = True

	return render_template('Home.html', error = error, most_selling_item_id = most_selling_item_id, least_selling_item_id = least_selling_item_id, most_selling_item_name = most_selling_item_name, least_selling_item_name = least_selling_item_name, financial_summaries = financial_summaries, stock_low = stock_low, graph_data = graph_data, dashboard_data = dashboard_data, closing_time = closing_time, login_token = login_token)

@app.route('/home/<login_token>', methods = ['GET', 'POST'])
def Home_post(login_token):
	now = datetime.now()
	dashboard_data = session.get('dashboard_data')
	most_selling_item_id = session.get('most_selling_item_id')
	least_selling_item_id = session.get('least_selling_item_id')
	most_selling_item_name = session.get('most_selling_item_name')
	least_selling_item_name = session.get('least_selling_item_name')
	compiled_app_path = pathlib.Path(__file__).parent.resolve()

	button_pressed = request.form['buttonpressed']

	if 'create' in button_pressed:
		# cREATE SUMMARY PDF
		current_date = str(datetime.now().date())
		canvas = Canvas(f'financial-summaries/{now.strftime("%Y-%m-%d_%H-%M-%S")}.pdf', pagesize = A4)
		canvas.setFillColor(HexColor('#1A1A1A'))
		canvas.setFont('Helvetica', 20)
		canvas.drawString(130, 800, f'Medicare | {now.strftime("%Y/%m/%d")} Summary')
		canvas.setFillColor(HexColor('#1A1A1A'))
		canvas.setFont('Helvetica', 15)
		canvas.drawString(30, 700, f'Number of items bought')
		canvas.drawString(440, 700, f'{dashboard_data[3]}')
		canvas.drawString(30, 670, f'Sales')
		canvas.drawString(440, 670, f'{dashboard_data[5]}Rs')
		canvas.drawString(30, 640, f'Number of items sold')
		canvas.drawString(440, 640, f'{dashboard_data[4]}')
		canvas.drawString(30, 610, f'Sell through percentage')
		canvas.drawString(440, 610, f'{dashboard_data[0]}%')
		canvas.drawString(30, 580, f'Number of refunds given')
		canvas.drawString(440, 580, f'{len(dashboard_data[6])}')
		canvas.drawString(30, 550, f'Average transaction value')
		canvas.drawString(440, 550, f'{dashboard_data[1]}Rs')
		canvas.drawString(30, 520, f'Average transaction quantity')
		canvas.drawString(440, 520, f'{dashboard_data[2]}')
		canvas.drawString(30, 490, f'Most selling item {now.strftime("%Y/%m/%d")}')
		canvas.drawString(30, 460, f'{most_selling_item_id} | {most_selling_item_name}')
		canvas.drawString(30, 430, f'Least selling item {now.strftime("%Y/%m/%d")}')
		canvas.drawString(30, 400, f'{least_selling_item_id} | {least_selling_item_name}')
		canvas.save()

		# open summary pdf
		os.startfile(f'{compiled_app_path}\\financial-summaries\\{now.strftime("%Y-%m-%d_%H-%M-%S")}.pdf')

	elif 'open' in button_pressed:
		# open summary pdf
		os.startfile(f'{compiled_app_path}\\financial-summaries\\{button_pressed[4:]}')

	# display financial summaries for viewing
	financial_summaries = [f for f in os.listdir('financial-summaries') if os.path.isfile(os.path.join('financial-summaries', f)) and f.endswith('.pdf')]

	return redirect(f'http://localhost:5000/home/{login_token}')

@app.route('/recordsale/<login_token>')
def Record_sale(login_token):
	#LOGIN TOKEN VALIDATION
	login_token = session.get('login_token')
	session['login_token'] = login_token
	if login_token == '':
		return redirect(f'http://localhost:5000/')

	error = 'none'

	'''
	cart conditions determined by CartID first digit,
	1 - loaded
	2 - paused
	3 - checkedout
	4 - refunded
	'''

	# get cartid and customerid from session
	cart_id = session.get('cart_id')
	customer_id = session.get('customer_id')

	# get sales tax value from salestax file
	sales_tax_file = open('bin/SalesTax.bin', 'rb')
	sales_tax = float(sales_tax_file.read().decode())
	sales_tax_file.close()

	# creating a connection cursor
	cursor = mysql.connection.cursor()

	# carts database query get carts data
	cursor.execute(''' SELECT ProductID, Quantity, TotalSalePrice
		FROM Cart
		WHERE CartID IN (
			SELECT CartID
			FROM Cart
			WHERE LEFT(CartID, 1) = 1); ''')
	cart_loaded = cursor.fetchall()
	print(cart_loaded)
	if cart_loaded != ():
		cursor.execute(''' SELECT CartID FROM Cart WHERE LEFT(CartID, 1) = 1 ''')
		for cart_loaded_id in cursor.fetchall():
			for loaded_id_tuple in cart_loaded_id:
				loaded_id = str(loaded_id_tuple)
		cart_id = loaded_id
	# carts database query get carts on hold data
	cursor.execute(''' SELECT DISTINCT CartID, CustomerID FROM Cart ''')
	rest_carts = cursor.fetchall()

	# carts database connection closing
	cursor.close()

	session['login_token'] = login_token
	session['cart_id'] = cart_id
	session['customer_id'] = customer_id

	return render_template('RecordSale.html', login_token = login_token, customer_id = customer_id, cart_id = cart_id, sales_tax = sales_tax, cart_loaded = cart_loaded, rest_carts = rest_carts, error = error)


@app.route('/recordsale/<login_token>', methods = ['GET', 'POST'])
def Record_sale_post(login_token):
	#LOGIN TOKEN VALIDATION
	login_token = session.get('login_token')
	session['login_token'] = login_token
	if login_token == '':
		return redirect(f'http://localhost:5000/')

	cart_id = session.get('cart_id')
	customer_id = session.get('customer_id')
	current_year = int(datetime.now().year)
	current_month = int(datetime.now().month)
	current_day = int(datetime.now().day)
	error = 'none'

	# get sales tax value from salestax file
	sales_tax_file = open('bin/SalesTax.bin', 'rb')
	sales_tax = float(sales_tax_file.read().decode())
	sales_tax_file.close()

	button_pressed = request.form['cartmodify']

	# creating a connection cursor
	cursor = mysql.connection.cursor()

	if 'itemadd' in button_pressed:
		inventory_item_ids_list = []
		carts_item_ids_list = []

		try:
			# user entry
			item_id = int(request.form['itemid'])
			item_quantity = int(request.form['itemquantity'])
			customer_id = int(request.form['customerid'])

			# get number of customers
			cursor.execute('''SELECT CustomerID, COUNT(*) FROM Cart WHERE CustomerID = %s GROUP BY CustomerID ''', (customer_id,))
			row_count = cursor.rowcount

			if row_count == 0:
				# customer database query add new customer
				cursor.execute(''' INSERT INTO Customers VALUES(%s, %s, %s, %s) ''', (customer_id, '', '', ''))
				mysql.connection.commit()
		
		except Exception:
			# carts database query get carts data
			cursor.execute(''' SELECT ProductID, Quantity, TotalSalePrice
				FROM Cart
				WHERE CartID IN (
					SELECT CartID
					FROM Cart
					WHERE LEFT(CartID, 1) = 1); ''')
			cart_loaded = cursor.fetchall()
			if cart_loaded != ():
				cursor.execute(''' SELECT CartID FROM Cart WHERE LEFT(CartID, 1) = 1 ''')
				for cart_loaded_id in cursor.fetchall():
					for loaded_id_tuple in cart_loaded_id:
						loaded_id = str(loaded_id_tuple)
				cart_id = loaded_id
			# carts database query get carts on hold data
			cursor.execute(''' SELECT DISTINCT CartID, CustomerID FROM Cart ''')
			rest_carts = cursor.fetchall()

			# carts database connection closing
			cursor.close()

			error = 'missing or invalid input/s'

			session['cart_id'] = cart_id
			session['customer_id'] = customer_id

			return render_template('RecordSale.html', login_token = login_token, cart_id = cart_id, customer_id = customer_id, sales_tax = sales_tax, rest_carts = rest_carts, cart_loaded = cart_loaded, error = error)

		# inventory database query get item id for validation
		cursor.execute(''' SELECT ProductID FROM Inventory ''')
		item_ids = cursor.fetchall()

		# ids of existing items
		for item_id_tuple in item_ids:
			for item_id_val in item_id_tuple:
				inventory_item_ids_list.append(item_id_val)

		# check if item id is valid
		if item_id in inventory_item_ids_list:
			# inventory database query get item current stock
			cursor.execute(''' SELECT Quantity FROM Inventory WHERE ProductID = %s ''', (item_id,))
			current_item_stock = cursor.fetchall()
			for item_stock_tuple in current_item_stock:
				for item_stock_value in item_stock_tuple:
					current_item_stock = int(item_stock_value)

			# check if item in stock
			if item_quantity <= current_item_stock:
				# carts database query get recorded item ids
				cursor.execute(''' SELECT ProductID FROM Cart WHERE CartID = %s ''', (cart_id,))
				carts_item_ids = cursor.fetchall()
				for carts_item_id_tuple in carts_item_ids:
					for carts_item_id_value in carts_item_id_tuple:
						carts_item_ids_list.append(carts_item_id_value)		

				# check if item already in carts
				if item_id in carts_item_ids_list:
					# inventory database query get item sale price
					cursor.execute(''' SELECT UnitSalePrice FROM Inventory WHERE ProductID = %s ''', (item_id,))
					item_unitsaleprice = cursor.fetchall()
					# item unit sale price from tuple to float
					item_unitsaleprice_value = sum(list(map(sum, item_unitsaleprice)))
					# calculating item total sale price
					item_totalsaleprice_value = item_unitsaleprice_value * item_quantity

					# carts database query update values
					cursor.execute(''' UPDATE Cart SET Quantity = Quantity + %s, TotalSalePrice = TotalSalePrice + %s WHERE ProductID = %s AND CartID = %s ''', (item_quantity, item_totalsaleprice_value, item_id, cart_id))
					mysql.connection.commit()

					# carts database query get carts data
					cursor.execute(''' SELECT ProductID, Quantity, TotalSalePrice
						FROM Cart
						WHERE CartID IN (
							SELECT CartID
							FROM Cart
							WHERE LEFT(CartID, 1) = 1); ''')
					cart_loaded = cursor.fetchall()
					# carts database query get carts on hold data
					cursor.execute(''' SELECT DISTINCT CartID, CustomerID FROM Cart ''')
					rest_carts = cursor.fetchall()

					cursor.close()

					session['cart_id'] = cart_id
					session['customer_id'] = customer_id

					return render_template('RecordSale.html', login_token = login_token, customer_id = customer_id, cart_id = cart_id, sales_tax = sales_tax, cart_loaded = cart_loaded, rest_carts = rest_carts, error = error)

				# if item not in carts
				else:
					# inventory database query get item sale price and add to sale prices list
					cursor.execute(''' SELECT UnitSalePrice FROM Inventory WHERE ProductID = %s ''', (item_id,))
					item_unitsaleprice = cursor.fetchall()
					# item unit sale price from tuple to float
					item_unitsaleprice_value = sum(list(map(sum, item_unitsaleprice)))
					# calculating item total sale price
					item_totalsaleprice_value = item_unitsaleprice_value * item_quantity

					# carts database query add new item
					cursor.execute(''' INSERT INTO Cart VALUES(%s, %s, %s, %s, %s) ''', (cart_id, customer_id, item_id, item_quantity, item_totalsaleprice_value))
					mysql.connection.commit()

					# carts database query add new item
					cursor.execute(''' INSERT INTO CartInventory VALUES(%s, %s) ''', (cart_id, item_id))
					mysql.connection.commit()

					# carts database query get carts data
					cursor.execute(''' SELECT ProductID, Quantity, TotalSalePrice
						FROM Cart
						WHERE CartID IN (
							SELECT CartID
							FROM Cart
							WHERE LEFT(CartID, 1) = 1); ''')
					cart_loaded = cursor.fetchall()
					# carts database query get carts on hold data
					cursor.execute(''' SELECT DISTINCT CartID, CustomerID FROM Cart ''')
					rest_carts = cursor.fetchall()

					# carts database connection closing
					cursor.close()

					session['cart_id'] = cart_id
					session['customer_id'] = customer_id

					return render_template('RecordSale.html', login_token = login_token, customer_id = customer_id, cart_id = cart_id, sales_tax = sales_tax, cart_loaded = cart_loaded, rest_carts = rest_carts, error = error)

			# if item out of stock
			else:
				error = 'item out of stock'

				# carts database query get carts data
				cursor.execute(''' SELECT ProductID, Quantity, TotalSalePrice
					FROM Cart
					WHERE CartID IN (
						SELECT CartID
						FROM Cart
						WHERE LEFT(CartID, 1) = 1); ''')
				cart_loaded = cursor.fetchall()
				# carts database query get carts on hold data
				cursor.execute(''' SELECT DISTINCT CartID, CustomerID FROM Cart ''')
				rest_carts = cursor.fetchall()

				# carts database connection closing
				cursor.close()

				session['cart_id'] = cart_id
				session['customer_id'] = customer_id

				return render_template('RecordSale.html', login_token = login_token, customer_id = customer_id, cart_id = cart_id, sales_tax = sales_tax, cart_loaded = cart_loaded, rest_carts = rest_carts, error = error)	

		# if item id not valid
		else:
			cart_id = session.get("cart_id")
			error = 'item not in inventory'

			# carts database query get carts data
			cursor.execute(''' SELECT ProductID, Quantity, TotalSalePrice
				FROM Cart
				WHERE CartID IN (
					SELECT CartID
					FROM Cart
					WHERE LEFT(CartID, 1) = 1); ''')
			cart_loaded = cursor.fetchall()
			# carts database query get cartss on hold data
			cursor.execute(''' SELECT DISTINCT CartID, CustomerID FROM Cart ''')
			rest_carts = cursor.fetchall()

			# carts database connection closing
			cursor.close()

			session['cart_id'] = cart_id
			session['customer_id'] = customer_id

			return render_template('RecordSale.html', login_token = login_token, customer_id = customer_id, cart_id = cart_id, sales_tax = sales_tax, cart_loaded = cart_loaded, rest_carts = rest_carts, error = error)

	elif 'itemdelete' in button_pressed:
		customer_id = session.get('customer_id')
		item_delete_id = button_pressed[10:]
		cart_id = session.get("cart_id")

		# carts database query get item quantity
		cursor.execute(''' SELECT Quantity FROM Cart WHERE ProductID = %s AND CartID = %s ''', (item_delete_id, cart_id))
		carts_item_quantity = cursor.fetchall()
		# item unit sale price from tuple to float
		carts_item_quantity_value = sum(list(map(sum, carts_item_quantity)))

		# carts database query get item unitsaleprice
		cursor.execute('SELECT UnitSalePrice FROM Inventory WHERE ProductID = %s', (item_delete_id,))
		carts_item_unitsaleprice = cursor.fetchall()
		# item unit sale price from tuple to float
		carts_item_unitsaleprice_value = sum(list(map(sum, carts_item_unitsaleprice)))

		# if qty > 1 then decrement qty, decrement totalsaleprice
		if carts_item_quantity_value > 1:
			# carts database query update values
			cursor.execute('UPDATE Cart SET Quantity = Quantity - 1, TotalSalePrice = TotalSalePrice - %s WHERE ProductID = %s AND CartID = %s', (carts_item_unitsaleprice_value, item_delete_id, cart_id))
			mysql.connection.commit()

		else:
			cursor.execute(''' SET FOREIGN_KEY_CHECKS = 0 ''')
			
			# carts database query update values
			cursor.execute('DELETE FROM CartInventory WHERE ProductID = %s AND CartID = %s', (item_delete_id, cart_id))
			mysql.connection.commit()

			# carts database query update values
			cursor.execute('DELETE FROM Cart WHERE ProductID = %s AND CartID = %s', (item_delete_id, cart_id))
			mysql.connection.commit()

			cursor.execute(''' SET FOREIGN_KEY_CHECKS = 1 ''')

		error = 'modification successful'

		# carts database query get carts data
		cursor.execute(''' SELECT ProductID, Quantity, TotalSalePrice
			FROM Cart
			WHERE CartID IN (
				SELECT CartID
				FROM Cart
				WHERE LEFT(CartID, 1) = 1); ''')
		cart_loaded = cursor.fetchall()
		# carts database query get carts on hold data
		cursor.execute(''' SELECT DISTINCT CartID, CustomerID FROM Cart ''')
		rest_carts = cursor.fetchall()

		# carts database connection closing
		cursor.close()

		session['cart_id'] = cart_id
		session['customer_id'] = customer_id

		return render_template('RecordSale.html', login_token = login_token, customer_id = customer_id, cart_id = cart_id, sales_tax = sales_tax, cart_loaded = cart_loaded, rest_carts = rest_carts, error = error)

	elif 'loadcart' in button_pressed:
		cart_id = session.get("cart_id")
		customer_id = session.get("customer_id")
		carts_cart_id = button_pressed[8:16]
		carts_customer_id = button_pressed[16:]

		if carts_cart_id[0] == '2':
			cursor.execute(''' SET FOREIGN_KEY_CHECKS = 0 ''')

			update_cart_id = '1' + carts_cart_id[1:]

			cursor.execute("UPDATE CartInventory SET CartID = %s WHERE CartID = %s", (update_cart_id, carts_cart_id))
			mysql.connection.commit()

			# carts database query update item values
			cursor.execute("UPDATE Cart SET CartID = %s WHERE CartID = %s", (update_cart_id, carts_cart_id))
			mysql.connection.commit()

			cursor.execute(''' SET FOREIGN_KEY_CHECKS = 1 ''')

			# carts database query get carts data
			cursor.execute(''' SELECT ProductID, Quantity, TotalSalePrice
				FROM Cart
				WHERE CartID IN (
					SELECT CartID
					FROM Cart
					WHERE LEFT(CartID, 1) = 1); ''')
			cart_loaded = cursor.fetchall()
			# carts database query get carts on hold data
			cursor.execute(''' SELECT DISTINCT CartID, CustomerID FROM Cart ''')
			rest_carts = cursor.fetchall()

		else:
			# carts database query get carts data
			cursor.execute(''' SELECT ProductID, Quantity, TotalSalePrice FROM Cart WHERE CartID = %s ''', (carts_cart_id,))
			cart_loaded = cursor.fetchall()
			# carts database query get carts on hold data
			cursor.execute(''' SELECT DISTINCT CartID, CustomerID FROM Cart ''')
			rest_carts = cursor.fetchall()

		# carts database connection closing
		cursor.close()

		session['cart_id'] = cart_id
		session['customer_id'] = customer_id

		return render_template('RecordSale.html', login_token = login_token, customer_id = carts_customer_id, cart_id = carts_cart_id, sales_tax = sales_tax, cart_loaded = cart_loaded, rest_carts = rest_carts, error = error)
	
	elif button_pressed == 'cartssearch':
		# user query
		query = request.form['cartssearchquery']
		query = '%' + query + '%'

		# carts database query get carts data
		cursor.execute(''' SELECT ProductID, Quantity, TotalSalePrice
			FROM Cart
			WHERE CartID IN (
				SELECT CartID
				FROM Cart
				WHERE LEFT(CartID, 1) = 1); ''')
		cart_loaded = cursor.fetchall()

		print(query)

		# carts database query get carts on hold data
		cursor.execute(''' SELECT DISTINCT CartID, CustomerID FROM Cart WHERE CartID LIKE %s ''', (query,))
		search_carts = cursor.fetchall()

		print(search_carts)

		# carts database connection closing
		cursor.close()

		session['cart_id'] = cart_id
		session['customer_id'] = customer_id

		return render_template('RecordSale.html', login_token = login_token, customer_id = customer_id, cart_id = cart_id, sales_tax = sales_tax, cart_loaded = cart_loaded, rest_carts = search_carts, error = error)

	elif 'refund' in button_pressed:
		refund_cart_id = button_pressed[6:]
		refund_cart_quantities = []
		refund_cart_itemids = []

		# carts database query get cart item ids
		cursor.execute(''' SELECT ProductID FROM Cart WHERE CartID = %s ''', (refund_cart_id,))
		refund_cart_itemids_data = cursor.fetchall()
		for refund_cart_itemid_tuple in refund_cart_itemids_data:
			for refund_cart_itemid_value in refund_cart_itemid_tuple:
				refund_cart_itemids.append(refund_cart_itemid_value)

		# carts database query get cart item quantites
		cursor.execute(''' SELECT Quantity FROM Cart WHERE CartID = %s''', (refund_cart_id,))
		refund_cart_quantities_data = cursor.fetchall()
		for refund_cart_quantity_tuple in refund_cart_quantities_data:
			for refund_cart_quantity_value in refund_cart_quantity_tuple:
				refund_cart_quantities.append(refund_cart_quantity_value)

		# update inventory stock values
		for i in range(0, len(refund_cart_itemids)):
			# inventory database query update values
			cursor.execute("UPDATE Inventory SET Quantity = Quantity + %s WHERE ProductID = %s", (refund_cart_quantities[i], refund_cart_itemids[i]))
			mysql.connection.commit()

		# cart database query get total
		cursor.execute('SELECT TotalSalePrice FROM Cart WHERE CartID = %s', (refund_cart_id,))
		refund_cart_total = cursor.fetchall()
		# cart total value tuple to float
		refund_cart_total = sum(list(map(sum, refund_cart_total)))

		error = f'return {refund_cart_total}Rs to the customer'

		cursor.execute(''' SET FOREIGN_KEY_CHECKS = 0 ''')

		update_cart_id = int('4' + refund_cart_id[1:])
		refund_cart_id = int(refund_cart_id)

		cursor.execute("UPDATE CartInventory SET CartID = %s WHERE CartID = %s", (update_cart_id, refund_cart_id))
		mysql.connection.commit()

		# carts database query update item values
		cursor.execute("UPDATE Cart SET CartID = %s WHERE CartID = %s", (update_cart_id, refund_cart_id))
		mysql.connection.commit()

		cursor.execute(''' SET FOREIGN_KEY_CHECKS = 1 ''')

		# carts database query get carts data
		cursor.execute(''' SELECT ProductID, Quantity, TotalSalePrice
			FROM Cart
			WHERE CartID IN (
				SELECT CartID
				FROM Cart
				WHERE LEFT(CartID, 1) = 1); ''')
		cart_loaded = cursor.fetchall()
		# carts database query get carts on hold data
		cursor.execute(''' SELECT DISTINCT CartID, CustomerID FROM Cart ''')
		rest_carts = cursor.fetchall()

		# carts database connection closing
		cursor.close()

		new_cart_id = '1' + ''.join(secrets.choice(string.digits) for i in range(7))
		new_customer_id = ''.join(secrets.choice(string.digits) for i in range(8))

		session['cart_id'] = new_cart_id
		session['customer_id'] = new_customer_id

		return render_template('RecordSale.html', login_token = login_token, customer_id = new_customer_id, cart_id = new_cart_id, sales_tax = sales_tax, cart_loaded = cart_loaded, rest_carts = rest_carts, error = error)

	else:
		cart_id = session.get("cart_id")

		# carts database query get carts data
		cursor.execute(''' SELECT ProductID, Quantity, TotalSalePrice
			FROM Cart
			WHERE CartID IN (
				SELECT CartID
				FROM Cart
				WHERE LEFT(CartID, 1) = 1); ''')
		cart_loaded = cursor.fetchall()
		# carts database query get carts on hold data
		cursor.execute(''' SELECT DISTINCT CartID, CustomerID FROM Cart ''')
		rest_carts = cursor.fetchall()

		# carts database connection closing
		cursor.close()

		session['cart_id'] = cart_id
		session['customer_id'] = customer_id

	return render_template('RecordSale.html', login_token = login_token, customer_id = customer_id, cart_id = cart_id, sales_tax = sales_tax, cart_loaded = cart_loaded, rest_carts = rest_carts, error = error)


@app.route('/checkout/<login_token>', methods = ['GET', 'POST'])
def Checkout(login_token):
	#LOGIN TOKEN VALIDATION
	login_token = session.get('login_token')
	if login_token == '':
		session['login_token'] = login_token
		return redirect(f'http://localhost:5000/')

	cart_id = session.get('cart_id')
	customer_id = session.get('customer_id')
	current_year = int(datetime.now().year)
	current_month = int(datetime.now().month)
	current_day = int(datetime.now().day)
	sub_total = session.get('sub_total')
	number_of_items = session.get('number_of_items')
	final_total = session.get('final_total')
	error = 'none'

	# get sales tax value
	sales_tax_file = open('bin/SalesTax.bin', 'rb')
	sales_tax = float(sales_tax_file.read().decode())
	sales_tax_file.close()
	
	# creating a connection cursor
	cursor = mysql.connection.cursor()

	button_pressed = request.form['endofrecordsalebutton']

	if button_pressed == 'calculatetotal':
		itemoffers_carts_itemids = []
		itemoffers_carts_itemquantities = []
		item_offer_discount_value = 0
		checkout_offer_qty_discount_value = 0
		checkout_offer_subtotal_discount_value = 0

		# carts database query get item totalsaleprice
		cursor.execute(''' SELECT TotalSalePrice FROM Cart WHERE LEFT(CartID, 1) = 1 ''')
		carts_totalsaleprices = cursor.fetchall()
		# carts totalsaleprices sum from tuple to float
		sub_total = sum(list(map(sum, carts_totalsaleprices)))

		# carts database query get item quantites
		cursor.execute(''' SELECT Quantity FROM Cart WHERE LEFT(CartID, 1) = 1 ''')
		carts_quantities = cursor.fetchall()
		# carts totalsaleprices sum from tuple to float
		number_of_items = sum(list(map(sum, carts_quantities)))

		# carts database query get item ids
		cursor.execute(''' SELECT ProductID FROM Cart WHERE LEFT(CartID, 1) = 1 ''')
		carts_itemids = cursor.fetchall()
		for carts_itemid_tuple in carts_itemids:
			for carts_itemid_value in carts_itemid_tuple:
				itemoffers_carts_itemids.append(carts_itemid_value)

		# calculating final total
		final_total = sub_total + (sub_total * (sales_tax / 100))

		# carts database query get carts data
		cursor.execute(''' SELECT ProductID, Quantity, TotalSalePrice
			FROM Cart
			WHERE CartID IN (
				SELECT CartID
				FROM Cart
				WHERE LEFT(CartID, 1) = 1); ''')
		cart_loaded = cursor.fetchall()
		# carts database query get carts on hold data
		cursor.execute(''' SELECT DISTINCT CartID, CustomerID FROM Cart ''')
		rest_carts = cursor.fetchall()

		# carts database connection closing
		cursor.close()

		session['number_of_items'] = number_of_items
		session['cart_id'] = cart_id
		session['final_total'] = final_total
		session['sub_total'] = sub_total
		session['login_token'] = login_token
		session['customer_id'] = customer_id

		return render_template('RecordSale.html', login_token = login_token, cart_id = cart_id, customer_id = customer_id, sales_tax = sales_tax, sub_total = sub_total, final_total = final_total, number_of_items = number_of_items, rest_carts = rest_carts, cart_loaded = cart_loaded, error = error)

	elif button_pressed == 'holdcart':
		# carts database query get carts data
		cursor.execute(''' SELECT ProductID, Quantity, TotalSalePrice
			FROM Cart
			WHERE CartID IN (
				SELECT CartID
				FROM Cart
				WHERE LEFT(CartID, 1) = 1); ''')
		cart_loaded = cursor.fetchall()
		# carts database query get carts on hold data
		cursor.execute(''' SELECT DISTINCT CartID, CustomerID FROM Cart ''')
		rest_carts = cursor.fetchall()


		if cart_loaded == ():
			error = 'no cart loaded for holding'

			session['login_token'] = login_token
			session['cart_id'] = cart_id
			session['customer_id'] = customer_id

			# carts database connection closing
			cursor.close()

			return render_template('RecordSale.html', login_token = login_token, cart_id = cart_id, customer_id = customer_id, sales_tax = sales_tax, rest_carts = rest_carts, cart_loaded = cart_loaded, error = error)
		
		else:
			cursor.execute(''' SET FOREIGN_KEY_CHECKS = 0 ''')

			update_cart_id = '2' + cart_id[1:]
			print("UPDATED:", update_cart_id)

			cursor.execute("UPDATE CartInventory SET CartID = %s WHERE CartID = %s", (update_cart_id, cart_id))
			mysql.connection.commit()
			cursor.execute("UPDATE Cart SET CartID = %s WHERE CartID = %s", (update_cart_id, cart_id))
			mysql.connection.commit()

			cursor.execute(''' SET FOREIGN_KEY_CHECKS = 1 ''')

		# cREATING HOLDING TOKEN
		shop_address_file = open('bin/ShopAddress.bin', 'rb')
		shop_address = shop_address_file.read().decode()
		shop_address_file.close()

		shop_contact_file = open('bin/ShopContact.bin', 'rb')
		shop_contact = shop_contact_file.read().decode()
		shop_contact_file.close()

		shop_closingtime_file = open('bin/ClosingTime.bin', 'rb')
		shop_closingtime = shop_closingtime_file.read().decode()
		shop_closingtime_file.close()

		try:
			receipt_barcode = Code128(cart_id, writer = ImageWriter())
			receipt_barcode.save(f'static/receipt-barcodes/{cart_id}')
		except Exception:
			pass

		canvas = Canvas(f'holding-tokens/{cart_id}.pdf')
		canvas.setPageSize((226.771653543, 110))
		canvas.setFillColor(HexColor('#1A1A1A'))
		canvas.setFont('Helvetica', 11)
		canvas.drawString(5, 90, 'Medicare')
		receipt_barcode_image = f'static/receipt-barcodes/{cart_id}.png'
		canvas.drawImage(receipt_barcode_image, 140, 60, height = 48, width = 88)	
		canvas.setFont('Helvetica', 9)
		canvas.drawString(5, 80, f'{cart_id} | {current_year}-{current_month}-{current_day}')
		canvas.setFont('Helvetica', 5)
		canvas.drawString(5, 70, f'Address: {shop_address}')
		canvas.drawString(5, 60, f'Contact: {shop_contact}')
		canvas.setFont('Helvetica', 9)
		canvas.drawString(5, 40, f'HOLDING TOKEN')
		canvas.setFont('Helvetica', 7)
		canvas.drawString(5, 20, f'PLEASE DO NOT LOSE THIS TOKEN | {str(customer_id)}')
		canvas.drawString(5, 10, f'THIS TOKEN AND YOUR CART WILL EXPIRE AT {shop_closingtime}')
		canvas.save()

		compiled_app_path = pathlib.Path(__file__).parent.resolve()

		new_cart_id = '1' + ''.join(secrets.choice(string.digits) for i in range(7))
		new_customer_id = ''.join(secrets.choice(string.digits) for i in range(8))

		os.startfile(f'{compiled_app_path}\\holding-tokens\\{cart_id}.pdf')

		session['cart_id'] = new_cart_id
		session['login_token'] = login_token
		session['customer_id'] = new_customer_id
		session.modified = True

		return render_template('RecordSale.html', login_token = login_token, cart_id = new_cart_id, customer_id = new_customer_id, sales_tax = sales_tax, rest_carts = rest_carts, cart_loaded = cart_loaded, error = error)

	elif button_pressed == 'checkout':
		itemids_receipt_display = []
		itemnames_receipt_display = []
		itemquantities_receipt_display = []
		itemtotalsaleprices_receipt_display = []

		# carts database query get item ids
		cursor.execute(''' SELECT ProductID FROM Cart WHERE CartID = %s ''', (cart_id,))
		receipt_itemids_display = cursor.fetchall()
		for receipt_itemid_tuple in receipt_itemids_display:
			for receipt_itemid_value in receipt_itemid_tuple:
				itemids_receipt_display.append(receipt_itemid_value)

		receipt_itemnames_display = None
		# carts database query get item names
		for itemid in itemids_receipt_display:
			cursor.execute(''' SELECT ProductName FROM Inventory WHERE ProductID = %s ''', (itemid,))
			receipt_itemnames_display = cursor.fetchall()
			for receipt_itemname_tuple in receipt_itemnames_display:
				for receipt_itemname_value in receipt_itemname_tuple:
					itemnames_receipt_display.append(receipt_itemname_value)

		# carts database query get item quantities
		cursor.execute(''' SELECT Quantity FROM Cart WHERE CartID = %s ''', (cart_id,))
		receipt_itemquantities_display = cursor.fetchall()
		for receipt_itemquantity_tuple in receipt_itemquantities_display:
			for receipt_itemquantity_value in receipt_itemquantity_tuple:
				itemquantities_receipt_display.append(receipt_itemquantity_value)

		# carts database query get item totalsaleprices
		cursor.execute(''' SELECT TotalSalePrice FROM Cart WHERE CartID = %s ''', (cart_id,))
		receipt_itemtotalsaleprices_display = cursor.fetchall()
		for receipt_itemtotalsaleprice_tuple in receipt_itemtotalsaleprices_display:
			for receipt_itemtotalsaleprice_value in receipt_itemtotalsaleprice_tuple:
				itemtotalsaleprices_receipt_display.append(receipt_itemtotalsaleprice_value)

		height_num = 80

		try:
			amount_paid = float(request.form['amountpaid'])
		except Exception:
			# carts database query get carts data
			cursor.execute(''' SELECT ProductID, Quantity, TotalSalePrice
				FROM Cart
				WHERE CartID IN (
					SELECT CartID
					FROM Cart
					WHERE LEFT(CartID, 1) = 1); ''')
			cart_loaded = cursor.fetchall()
			# carts database query get carts on hold data
			cursor.execute(''' SELECT DISTINCT CartID, CustomerID FROM Cart ''')
			rest_carts = cursor.fetchall()

			# inventory database connection closing
			cursor.close()

			error = 'missing or invalid input/s'

			session['cart_id'] = cart_id
			session['customer_id'] = customer_id
			session['login_token'] = login_token
	
			return render_template('RecordSale.html', login_token = login_token, cart_id = cart_id, customer_id = customer_id, final_total = final_total, sub_total = sub_total, number_of_items = number_of_items, sales_tax = sales_tax, rest_carts = rest_carts, cart_loaded = cart_loaded, error = error)

		if amount_paid < final_total:
			# carts database query get carts data
			cursor.execute(''' SELECT ProductID, Quantity, TotalSalePrice
				FROM Cart
				WHERE CartID IN (
					SELECT CartID
					FROM Cart
					WHERE LEFT(CartID, 1) = 1); ''')
			cart_loaded = cursor.fetchall()
			# carts database query get carts on hold data
			cursor.execute(''' SELECT DISTINCT CartID, CustomerID FROM Cart ''')
			rest_carts = cursor.fetchall()

			# inventory database connection closing
			cursor.close()

			error = 'amount paid is less than final total'

			session['cart_id'] = cart_id
			session['customer_id'] = customer_id
			session['login_token'] = login_token

			return render_template('RecordSale.html', login_token = login_token, cart_id = cart_id, customer_id = customer_id, final_total = final_total, sub_total = sub_total, number_of_items = number_of_items, sales_tax = sales_tax, rest_carts = rest_carts, cart_loaded = cart_loaded, error = error)
		else:
			pass

		current_date = str(datetime.now().date())
		refund_valid_limit_file = open('bin/RefundValidLimit.bin', 'rb')
		refund_valid_limit = int(refund_valid_limit_file.read().decode())
		refund_valid_limit_file.close()
		sales_tax_file = open('bin/SalesTax.bin', 'rb')
		sales_tax = float(sales_tax_file.read().decode())
		sales_tax_file.close()

		try:
			receipt_barcode = Code128(str(cart_id), writer = ImageWriter())
			receipt_barcode.save(f'static/receipt-barcodes/{cart_id}')
		except Exception:
			pass

		shop_address_file = open('bin/ShopAddress.bin', 'rb')
		shop_address = shop_address_file.read().decode()
		shop_address_file.close()
		shop_contact_file = open('bin/ShopContact.bin', 'rb')
		shop_contact = shop_contact_file.read().decode()
		shop_contact_file.close()
		height = 220 + (len(itemids_receipt_display) * 20)
		
		canvas = Canvas(f'receipts/{cart_id}.pdf')
		canvas.setPageSize((226.771653543, height))
		canvas.setFillColor(HexColor('#1A1A1A'))
		canvas.setFont('Helvetica', 11)
		canvas.drawString(5, height - 15, 'Medicare')
		receipt_barcode_image = f'static/receipt-barcodes/{cart_id}.png'
		canvas.drawImage(receipt_barcode_image, 144, height - 49, height = 48, width = 88)	
		canvas.setFont('Helvetica', 9)
		canvas.drawString(5, height - 25, f'{cart_id} | {current_date}')
		canvas.setFont('Helvetica', 5)
		canvas.drawString(5, height - 35, f'Address: {shop_address}')
		canvas.drawString(5, height - 45, f'Contact: {shop_contact}')
		canvas.drawString(0, height - 55, '-----------------------------------------------------------------------------------------------------------------------------------------')
		canvas.drawString(10, height - 60, 'item id | name')
		canvas.setFont('Helvetica', 5)
		canvas.drawString(111, height - 60, 'quantity')
		canvas.drawString(189, height - 60, 'price')
		canvas.drawString(0, height - 65, '-----------------------------------------------------------------------------------------------------------------------------------------')
		
		for i in range(0, len(itemids_receipt_display)):
			canvas.drawString(10, height - (height_num - 10), f'{itemids_receipt_display[i]}')
			canvas.drawString(10, height - (height_num - 5), f'{itemnames_receipt_display[i]}')
			canvas.setFont('Helvetica', 5)
			canvas.drawString(120, height - (height_num - 10), f'{itemquantities_receipt_display[i]}')
			canvas.drawString(187, height - (height_num - 10), f'{itemtotalsaleprices_receipt_display[i]}Rs')
			height_num += 20

		canvas.setFont('Helvetica', 6)
		canvas.drawString(0, 120, '-----------------------------------------------------------------------------------------------------------------------------------------')
		canvas.drawString(70, 110, f'sub total')
		canvas.drawString(180, 110, f'{sub_total}Rs')
		canvas.drawString(170, 100, '-------------------------------')
		canvas.drawString(70, 90, f'total discount')
		canvas.drawString(180, 90, f'0Rs')
		canvas.drawString(170, 80, '--------------------------------')
		canvas.drawString(70, 70, f'final total + {sales_tax}% sales tax')
		canvas.drawString(180, 70, f'{final_total}Rs')
		canvas.drawString(170, 60, '--------------------------------')
		canvas.drawString(70, 50, f'amount paid')
		canvas.drawString(180, 50, f'{amount_paid}Rs')
		canvas.drawString(170, 40, '--------------------------------')
		canvas.drawString(5, 30, f'# of items: {number_of_items}')
		canvas.drawString(70, 30, f'change')
		canvas.drawString(180, 30, f'{round(amount_paid - final_total, 2)}Rs')
		canvas.drawString(0, 20, '-----------------------------------------------------------------------------------------------------------------------------------------')
		canvas.drawString(5, 12, 'THANKYOU FOR SHOPPING WITH US')
		canvas.drawString(5, 5, str(customer_id))
		canvas.setFont('Helvetica', 5)
		canvas.drawString(123, 5, f'valid for refund within {refund_valid_limit} days after purchase')

		canvas.save()

		# update inventory stock values
		for i in range(0, len(itemids_receipt_display)):
			# inventory database query update item values
			cursor.execute('UPDATE Inventory SET Quantity = Quantity - %s WHERE ProductID = %s', (itemquantities_receipt_display[i], itemids_receipt_display[i]))
			mysql.connection.commit()

			cursor.execute(''' SET FOREIGN_KEY_CHECKS = 0 ''')

			update_cart_id = '3' + cart_id[1:]
			print(update_cart_id)

			cursor.execute("UPDATE CartInventory SET CartID = %s WHERE CartID = %s", (update_cart_id, cart_id))
			mysql.connection.commit()

			# carts database query update item values
			cursor.execute("UPDATE Cart SET CartID = %s WHERE CartID = %s", (update_cart_id, cart_id))
			mysql.connection.commit()

			cursor.execute(''' SET FOREIGN_KEY_CHECKS = 1 ''')

		compiled_app_path = pathlib.Path(__file__).parent.resolve()

		# carts database query get carts data
		cursor.execute(''' SELECT ProductID, Quantity, TotalSalePrice
			FROM Cart
			WHERE CartID IN (
				SELECT CartID
				FROM Cart
				WHERE LEFT(CartID, 1) = 1); ''')
		cart_loaded = cursor.fetchall()
		# carts database query get carts on hold data
		cursor.execute(''' SELECT DISTINCT CartID, CustomerID FROM Cart ''')
		rest_carts = cursor.fetchall()

		# carts database connection closing
		cursor.close()

		new_cart_id = '1' + ''.join(secrets.choice(string.digits) for i in range(7))
		new_customer_id = ''.join(secrets.choice(string.digits) for i in range(8))

		os.startfile(f'{compiled_app_path}\\receipts\\{cart_id}.pdf')

		session['cart_id'] = new_cart_id	
		session['login_token'] = login_token
		session['customer_id'] = new_customer_id
		session.modified = True
	
		return render_template('RecordSale.html', login_token = login_token, cart_id = new_cart_id, customer_id = new_customer_id, sales_tax = sales_tax, rest_carts = rest_carts, cart_loaded = cart_loaded, error = error)

	elif button_pressed == 'resetcart':
		try:
			cursor.execute(''' SET FOREIGN_KEY_CHECKS = 0 ''')

			# carts database query reset carts
			cursor.execute("DELETE FROM CartInventory WHERE CartID = %s", (cart_id,))
			mysql.connection.commit()

			# carts database query reset carts
			cursor.execute("DELETE FROM Cart WHERE CartID = %s", (cart_id,))
			mysql.connection.commit()

			cursor.execute(''' SET FOREIGN_KEY_CHECKS = 1 ''')
		except Exception:
			pass

		# carts database query get carts data
		cursor.execute(''' SELECT ProductID, Quantity, TotalSalePrice
			FROM Cart
			WHERE CartID IN (
				SELECT CartID
				FROM Cart
				WHERE LEFT(CartID, 1) = 1); ''')
		cart_loaded = cursor.fetchall()
		# carts database query get carts on hold data
		cursor.execute(''' SELECT DISTINCT CartID, CustomerID FROM Cart ''')
		rest_carts = cursor.fetchall()

		# carts database connection closing
		cursor.close()

		# generating new receipt code
		new_cart_id = '1' + ''.join(secrets.choice(string.digits) for i in range(7))
		new_customer_id = ''.join(secrets.choice(string.digits) for i in range(8))

		session['cart_id'] = new_cart_id
		session['customer_id'] = new_customer_id
		session['login_token'] = login_token
		session.modified = True

		return render_template('RecordSale.html', login_token = login_token, cart_id = new_cart_id, customer_id = new_customer_id, sales_tax = sales_tax, rest_carts = rest_carts, cart_loaded = cart_loaded, error = error)

	else:
		pass

	# carts database query get carts data
	cursor.execute(''' SELECT ProductID, Quantity, TotalSalePrice
		FROM Cart
		WHERE CartID IN (
			SELECT CartID
			FROM Cart
			WHERE LEFT(CartID, 1) = 1); ''')
	cart_loaded = cursor.fetchall()
	# carts database query get carts on hold data
	cursor.execute(''' SELECT DISTINCT CartID, CustomerID FROM Cart ''')
	rest_carts = cursor.fetchall()

	# carts database connection closing
	cursor.close()

	session['login_token'] = login_token
	session['cart_id'] = cart_id
	session['customer_id'] = customer_id

	return render_template('RecordSale.html', login_token = login_token, cart_id = cart_id, customer_id = customer_id, sales_tax = sales_tax, rest_carts = rest_carts, cart_loaded = cart_loaded, error = error)


@app.route('/customers/<login_token>')
def Customers(login_token):
	#LOGIN TOKEN VALIDATION
	login_token = session.get('login_token')
	if login_token == '':
		session['login_token'] = login_token
		return redirect(f'http://localhost:5000/')

	new_id = ''.join(secrets.choice(string.digits) for i in range(8))
	customers_search_results = []
	session['login_token'] = login_token
	error = 'none'

	return render_template('Customers.html', login_token = login_token, new_id = new_id, customers_search_results = customers_search_results, error = error)


@app.route('/customers/search/<login_token>', methods = ['GET', 'POST'])
def Customers_search(login_token):
	#LOGIN TOKEN VALIDATION
	login_token = session.get('login_token')
	if login_token == '':
		session['login_token'] = login_token
		return redirect(f'http://localhost:5000/')

	new_id = ''.join(secrets.choice(string.digits) for i in range(8))
	customers_search_results = []
	customers_search_ids = []
	error = 'none'

	try:
		# user query
		query = request.form['query']
		query_filter = request.form['filter']
		
	except Exception:
		query = ''
		query_filter = ''

	# creating a connection cursor
	cursor = mysql.connection.cursor()

	if query == '' and query_filter == 'null':
		# customers database query
		cursor.execute(''' SELECT * FROM Customers ''')
		customers_search_results = cursor.fetchall()

	elif query_filter == 'id':
		query = '%' + query + '%'
		# customers database query
		cursor.execute(''' SELECT * FROM Customers WHERE CustomerID LIKE %s ''', (query,))
		customers_search_results = cursor.fetchall()

	elif query_filter == 'name':
		query = '%' + query + '%'
		# customers database query
		cursor.execute(''' SELECT * FROM Customers WHERE CustomerName LIKE %s ''', (query,))
		customers_search_results = cursor.fetchall()

	elif query_filter == 'contact':
		query = '%' + query + '%'
		# customers database query
		cursor.execute(''' SELECT * FROM Customers WHERE ContactNumber LIKE %s ''', (query,))
		customers_search_results = cursor.fetchall()

	elif query_filter == 'address':
		query = '%' + query + '%'
		# customers database query
		cursor.execute(''' SELECT * FROM Customers WHERE Address LIKE %s ''', (query,))
		customers_search_results = cursor.fetchall()

	else:
		cursor.execute(''' SELECT CustomerID FROM Customers ''')
		suppliers_search_ids = cursor.fetchall()

		session['login_token'] = login_token
		return render_template('Customers.html', login_token = login_token, new_id = new_id, customers_search_ids = customers_search_ids, customers_search_results = customers_search_results, error = error)

	cursor.execute(''' SELECT CustomerID FROM Customers ''')
	customers_search_ids = cursor.fetchall()

	cursor.close()

	session['login_token'] = login_token
	return render_template('Customers.html', login_token = login_token, customers_search_ids = customers_search_ids, new_id = new_id, customers_search_results = customers_search_results, error = error)


@app.route('/customers/mod/<login_token>', methods = ['GET', 'POST'])
def Customers_mod(login_token):
	#LOGIN TOKEN VALIDATION
	login_token = session.get('login_token')
	if login_token == '':
		session['login_token'] = login_token
		return redirect(f'http://localhost:5000/')

	new_id = ''.join(secrets.choice(string.digits) for i in range(8))
	customers_search_results = []
	error = 'none'

	# creating a connection cursor
	cursor = mysql.connection.cursor()

	# button pressed value
	button_pressed = request.form['customermodifyconfirm']

	if button_pressed == 'customeraddconfirm':
		try:
			# user entry
			customer_add_id = request.form.get('customeraddid', type = int)
			customer_add_name = request.form['customeraddname']
			customer_add_contact = request.form['customeraddcontact']
			customer_add_address = request.form['customeraddaddress']
		
		except Exception:
			error = 'missing or invalid input/s'

			return render_template('Customers.html', login_token = login_token, new_id = new_id, customers_search_results = customers_search_results, error = error)

		# check if user entries are empty
		if customer_add_id == '' or customer_add_name == '' or customer_add_contact == '':
			error = 'missing input/s'

			cursor.close()
			
			return render_template('Customers.html', login_token = login_token, new_id = new_id, customers_search_results = customers_search_results, error = error)
		
		else:
			pass

		# exception handling for customer add
		try:
			# suppliers database query add new customer
			cursor.execute(''' INSERT INTO Customers VALUES(%s, %s, %s, %s) ''', (customer_add_id, customer_add_name, customer_add_contact, customer_add_address))
			mysql.connection.commit()

			error = 'modification successful'

		except Exception:
			error = 'modification unsuccessful'

	elif 'delete' in button_pressed:
		# user entry
		customer_modify_delete_id = request.form['customermodifyconfirm']
		customer_modify_delete_id_new = customer_modify_delete_id[6:]

		# exception handling for customer delete
		try:
			# suppliers database query delete customer
			cursor.execute(''' DELETE FROM Customers WHERE CustomerID = %s ''', (customer_modify_delete_id_new,))
			mysql.connection.commit()

			error = 'modification successful'

		except Exception:
			error = 'modification unsuccessful'

	else:
		# user entry
		customer_modify_id = request.form['customermodifyconfirm']
		customer_modify_name = request.form['customermodifyname' + str(customer_modify_id)]
		customer_modify_contact = request.form['customermodifycontact' + str(customer_modify_id)]
		customer_modify_address = request.form['customermodifyaddress' + str(customer_modify_id)]

		try:
			# suppliers database query update values
			cursor.execute(''' UPDATE Customers SET CustomerName = %s, ContactNumber = %s, Address = %s WHERE CustomerID = %s ''', (customer_modify_name, customer_modify_contact, customer_modify_address, customer_modify_id))
			mysql.connection.commit()

			error = 'modification successful'

		except Exception as e:
			error = 'modification unsuccessful'
			print(e)

	cursor.close()
	
	return render_template('Customers.html', login_token = login_token, new_id = new_id, customers_search_results = customers_search_results, error = error)


@app.route('/suppliers/<login_token>')
def Suppliers(login_token):
	#LOGIN TOKEN VALIDATION
	login_token = session.get('login_token')
	if login_token == '':
		session['login_token'] = login_token
		return redirect(f'http://localhost:5000/')

	new_id = ''.join(secrets.choice(string.digits) for i in range(8))
	suppliers_search_results = []
	session['login_token'] = login_token
	error = 'none'

	return render_template('Suppliers.html', login_token = login_token, new_id = new_id, suppliers_search_results = suppliers_search_results, error = error)


@app.route('/suppliers/search/<login_token>', methods = ['GET', 'POST'])
def Suppliers_search(login_token):
	#LOGIN TOKEN VALIDATION
	login_token = session.get('login_token')
	if login_token == '':
		session['login_token'] = login_token
		return redirect(f'http://localhost:5000/')

	new_id = ''.join(secrets.choice(string.digits) for i in range(8))
	suppliers_search_results = []
	suppliers_search_ids = []
	error = 'none'

	try:
		# user query
		query = request.form['query']
		query_filter = request.form['filter']
		
	except Exception:
		query = ''
		query_filter = ''

	# creating a connection cursor
	cursor = mysql.connection.cursor()

	if query == '' and query_filter == 'null':
		# suppliers database query
		cursor.execute(''' SELECT * FROM Suppliers ''')
		suppliers_search_results = cursor.fetchall()

	elif query_filter == 'id':
		query = '%' + query + '%'
		# suppliers database query
		cursor.execute(''' SELECT * FROM Suppliers WHERE SupplierID LIKE %s ''', (query,))
		suppliers_search_results = cursor.fetchall()

	elif query_filter == 'name':
		query = '%' + query + '%'
		# suppliers database query
		cursor.execute(''' SELECT * FROM Suppliers WHERE SupplierName LIKE %s ''', (query,))
		suppliers_search_results = cursor.fetchall()

	elif query_filter == 'contact':
		query = '%' + query + '%'
		# suppliers database query
		cursor.execute(''' SELECT * FROM Suppliers WHERE ContactNumber LIKE %s ''', (query,))
		supppliers_search_results = cursor.fetchall()

	else:
		cursor.execute(''' SELECT SupplierID FROM Suppliers ''')
		suppliers_search_ids = cursor.fetchall()

		session['login_token'] = login_token
		return render_template('Suppliers.html', login_token = login_token, new_id = new_id, supppliers_search_ids = suppliers_search_ids, suppliers_search_results = suppliers_search_results, error = error)

	cursor.execute(''' SELECT SupplierID FROM Suppliers ''')
	suppliers_search_ids = cursor.fetchall()

	cursor.close()

	session['login_token'] = login_token
	return render_template('Suppliers.html', login_token = login_token, supppliers_search_ids = suppliers_search_ids, new_id = new_id, suppliers_search_results = suppliers_search_results, error = error)


@app.route('/suppliers/mod/<login_token>', methods = ['GET', 'POST'])
def Suppliers_mod(login_token):
	#LOGIN TOKEN VALIDATION
	login_token = session.get('login_token')
	if login_token == '':
		session['login_token'] = login_token
		return redirect(f'http://localhost:5000/')

	new_id = ''.join(secrets.choice(string.digits) for i in range(8))
	suppliers_search_results = []
	error = 'none'

	# creating a connection cursor
	cursor = mysql.connection.cursor()

	# button pressed value
	button_pressed = request.form['suppliermodifyconfirm']

	if button_pressed == 'supplieraddconfirm':
		try:
			# user entry
			supplier_add_image = request.files['supplieraddimage']
			supplier_add_id = request.form.get('supplieraddid', type = int)
			supplier_add_name = request.form['supplieraddname']
			supplier_add_contact = request.form['supplieraddcontact']
		
		except Exception:
			error = 'missing or invalid input/s'

			return render_template('Suppliers.html', login_token = login_token, new_id = new_id, suppliers_search_results = suppliers_search_results, error = error)

		# check if user entries are empty
		if supplier_add_id == '' or supplier_add_name == '' or supplier_add_contact == '':
			error = 'missing input/s'

			cursor.close()
			
			return render_template('Suppliers.html', login_token = login_token, new_id = new_id, suppliers_search_results = suppliers_search_results, error = error)
		
		else:
			pass

		# exception handling for supplier image save
		try:	
			# adding supplier to static directory
			supplier_add_image.save(os.path.join('static/supplier-images', secure_filename(supplier_add_image.filename)))

			# renaming file to entered id
			os.rename(f'static/supplier-images/{secure_filename(supplier_add_image.filename)}', f'static/supplier-images/{str(supplier_add_id)}.jpg')

		except FileNotFoundError:
			pass

		# exception handling for supplier add
		try:
			# suppliers database query add new supplier
			cursor.execute(''' INSERT INTO Suppliers VALUES(%s, %s, %s) ''', (supplier_add_id, supplier_add_name, supplier_add_contact))
			mysql.connection.commit()

			error = 'modification successful'

		except Exception:
			error = 'modification unsuccessful'

	elif 'delete' in button_pressed:
		# user entry
		supplier_modify_delete_id = request.form['suppliermodifyconfirm']
		supplier_modify_delete_id_new = supplier_modify_delete_id[6:]

		try:
			# delete supplier image
			os.remove(f'static/supplier-images/{supplier_modify_delete_id_new}.jpg')
			
		except Exception:
			pass

		# exception handling for supplier delete
		try:
			# suppliers database query delete supplier
			cursor.execute(''' DELETE FROM Suppliers WHERE SupplierID = %s ''', (supplier_modify_delete_id_new,))
			mysql.connection.commit()

			error = 'modification successful'

		except Exception:
			error = 'modification unsuccessful'

	else:
		# user entry
		supplier_modify_id = request.form['suppliermodifyconfirm']
		supplier_modify_name = request.form['suppliermodifyname' + str(supplier_modify_id)]
		supplier_modify_contact = request.form['suppliermodifycontact' + str(supplier_modify_id)]

		try:
			# suppliers database query update values
			cursor.execute(''' UPDATE Suppliers SET SupplierName = %s, ContactNumber  = %s WHERE SupplierID = %s ''', (supplier_modify_name, supplier_modify_contact, supplier_modify_id))
			mysql.connection.commit()

			error = 'modification successful'

		except Exception:
			error = 'modification unsuccessful'

	cursor.close()
	
	return render_template('Suppliers.html', login_token = login_token, new_id = new_id, suppliers_search_results = suppliers_search_results, error = error)


@app.route('/employees/<login_token>')
def Employees(login_token):
	#LOGIN TOKEN VALIDATION
	login_token = session.get('login_token')
	if login_token == '':
		session['login_token'] = login_token
		return redirect(f'http://localhost:5000/')

	new_id = ''.join(secrets.choice(string.digits) for i in range(8))
	employees_search_results = []
	session['login_token'] = login_token
	error = 'none'

	return render_template('Employees.html', login_token = login_token, new_id = new_id, employees_search_results = employees_search_results, error = error)


@app.route('/employees/search/<login_token>', methods = ['GET', 'POST'])
def Employees_search(login_token):
	#LOGIN TOKEN VALIDATION
	login_token = session.get('login_token')
	if login_token == '':
		session['login_token'] = login_token
		return redirect(f'http://localhost:5000/')

	new_id = ''.join(secrets.choice(string.digits) for i in range(8))
	employees_search_results = []
	employees_search_ids = []
	error = 'none'

	try:
		# user query
		query = request.form['query']
		query_filter = request.form['filter']
		
	except Exception:
		query = ''
		query_filter = ''

	# creating a connection cursor
	cursor = mysql.connection.cursor()

	if query == '' and query_filter == 'null':
		# employees database query
		cursor.execute(''' SELECT * FROM Employees ''')
		employees_search_results = cursor.fetchall()

	elif query_filter == 'id':
		query = '%' + query + '%'
		# employees database query
		cursor.execute(''' SELECT * FROM Employees WHERE EmployeeID LIKE %s ''', (query,))
		employees_search_results = cursor.fetchall()

	elif query_filter == 'name':
		query = '%' + query + '%'
		# employees database query
		cursor.execute(''' SELECT * FROM Employees WHERE EmployeeName LIKE %s ''', (query,))
		employees_search_results = cursor.fetchall()

	elif query_filter == 'position':
		query = '%' + query + '%'
		# employees database query
		cursor.execute(''' SELECT * FROM Employees WHERE Position LIKE %s ''', (query,))
		employees_search_results = cursor.fetchall()

	else:
		session['login_token'] = login_token
		return render_template('Employees.html', login_token = login_token, new_id = new_id, employees_search_results = employees_search_results, error = error)

	cursor.close()

	session['login_token'] = login_token
	return render_template('Employees.html', login_token = login_token, employees_search_ids = employees_search_ids, new_id = new_id, employees_search_results = employees_search_results, error = error)


@app.route('/employees/mod/<login_token>', methods = ['GET', 'POST'])
def Employees_mod(login_token):
	#LOGIN TOKEN VALIDATION
	login_token = session.get('login_token')
	if login_token == '':
		session['login_token'] = login_token
		return redirect(f'http://localhost:5000/')

	new_id = ''.join(secrets.choice(string.digits) for i in range(8))
	employees_search_results = []
	error = 'none'

	# creating a connection cursor
	cursor = mysql.connection.cursor()

	# button pressed value
	button_pressed = request.form['employeemodifyconfirm']

	if button_pressed == 'employeeaddconfirm':
		try:
			# user entry
			employee_add_image = request.files['employeeaddimage']
			employee_add_id = request.form.get('employeeaddid', type = int)
			employee_add_name = request.form['employeeaddname']
			employee_add_position = request.form['employeeaddposition']
		
		except Exception:
			error = 'missing or invalid input/s'

			return render_template('Employees.html', login_token = login_token, new_id = new_id, employees_search_results = employees_search_results, error = error)

		# check if user entries are empty
		if employee_add_id == '' or employee_add_name == '' or employee_add_position == '':
			error = 'missing input/s'

			cursor.close()
			
			return render_template('Employees.html', login_token = login_token, new_id = new_id, employees_search_results = employees_search_results, error = error)
		
		else:
			pass

		# exception handling for employee image save
		try:	
			employee_add_image.save(os.path.join('static/employee-images', secure_filename(employee_add_image.filename)))

			# renaming file to entered id
			os.rename(f'static/employee-images/{secure_filename(employee_add_image.filename)}', f'static/employee-images/{str(employee_add_id)}.jpg')

		except FileNotFoundError:
			pass

		# exception handling for employee add
		try:
			cursor.execute(''' INSERT INTO Employees VALUES(%s, %s, %s) ''', (employee_add_id, employee_add_name, employee_add_position))
			mysql.connection.commit()

			error = 'modification successful'

		except Exception:
			error = 'modification unsuccessful'

	elif 'delete' in button_pressed:
		# user entry
		employee_modify_delete_id = request.form['employeemodifyconfirm']
		employee_modify_delete_id_new = employee_modify_delete_id[6:]

		try:
			os.remove(f'static/employee-images/{employee_modify_delete_id_new}.jpg')
			
		except Exception:
			pass

		# exception handling for employee delete
		try:
			cursor.execute(''' DELETE FROM Employees WHERE EmployeeID = %s ''', (employee_modify_delete_id_new,))
			mysql.connection.commit()

			error = 'modification successful'

		except Exception:
			error = 'modification unsuccessful'

	else:
		# user entry
		employee_modify_id = request.form['employeemodifyconfirm']
		employee_modify_name = request.form['employeemodifyname' + str(employee_modify_id)]
		employee_modify_position = request.form['employeemodifyposition' + str(employee_modify_id)]

		try:
			# employees database query update values
			cursor.execute(''' UPDATE Employees SET EmployeeName = %s, Position = %s WHERE EmployeeID = %s ''', (employee_modify_name, employee_modify_position, employee_modify_id))
			mysql.connection.commit()

			error = 'modification successful'

		except Exception:
			error = 'modification unsuccessful'

	cursor.close()
	
	return render_template('Employees.html', login_token = login_token, new_id = new_id, employees_search_results = employees_search_results, error = error)


@app.route('/inventory/<login_token>')
def Inventory(login_token):
	#LOGIN TOKEN VALIDATION
	login_token = session.get('login_token')
	if login_token == '':
		session['login_token'] = login_token
		return redirect(f'http://localhost:5000/')

	new_id = int(''.join(secrets.choice(string.digits) for i in range(8)))
	inventory_search_results = []
	session['login_token'] = login_token
	error = 'none'

	# creating a connection cursor
	cursor = mysql.connection.cursor()

	cursor.execute(''' SELECT SupplierID FROM Suppliers ''')
	suppliers = cursor.fetchall()

	cursor.close()

	return render_template('Inventory.html', login_token = login_token, new_id = new_id, suppliers = suppliers, inventory_search_results = inventory_search_results, error = error)


@app.route('/inventory/search/<login_token>', methods = ['GET', 'POST'])
def Inventory_search(login_token):
	#LOGIN TOKEN VALIDATION
	login_token = session.get('login_token')
	if login_token == '':
		session['login_token'] = login_token
		return redirect(f'http://localhost:5000/')

	new_id = int(''.join(secrets.choice(string.digits) for i in range(8)))
	inventory_search_results = []
	inventory_search_ids = []
	error = 'none'

	try:
		# user query
		query = request.form['query']
		query_filter = request.form['filter']
		
	except Exception:
		query = ''
		query_filter = ''

	# creating a connection cursor
	cursor = mysql.connection.cursor()

	if query == '' and query_filter == 'null':
		# inventory database query
		cursor.execute(''' SELECT * FROM Inventory ''')
		inventory_search_results = cursor.fetchall()

	elif query_filter == 'id':
		query = '%' + query + '%'
		# inventory database query
		cursor.execute(''' SELECT * FROM Inventory WHERE ProductID LIKE %s ''', (query,))
		inventory_search_results = cursor.fetchall()

	elif query_filter == 'stock':
		query = '%' + query + '%'
		# inventory database query
		cursor.execute(''' SELECT * FROM Inventory WHERE Quantity LIKE %s ''', (query,))
		inventory_search_results = cursor.fetchall()

	elif query_filter == 'name':
		query = '%' + query + '%'
		# inventory database query
		cursor.execute(''' SELECT * FROM Inventory WHERE ProductName LIKE %s ''', (query,))
		inventory_search_results = cursor.fetchall()

	elif query_filter == 'expiry':
		query = '%' + query + '%'
		# inventory database query
		cursor.execute(''' SELECT * FROM Inventory WHERE ExpiryDate LIKE %s ''', (query,))
		inventory_search_results = cursor.fetchall()

	elif query_filter == 'supplier':
		query = '%' + query + '%'
		# inventory database query
		cursor.execute(''' SELECT * FROM Inventory WHERE SupplierID LIKE %s ''', (query,))
		inventory_search_results = cursor.fetchall()

	elif query_filter == 'price':
		query = '%' + query + '%'
		# inventory database query
		cursor.execute(''' SELECT * FROM Inventory WHERE UnitSalePrice LIKE %s ''', (query,))
		inventory_search_results = cursor.fetchall()

	else:
		cursor.execute(''' SELECT SupplierID FROM Suppliers ''')
		suppliers = cursor.fetchall()

		session['login_token'] = login_token
		return render_template('Inventory.html', login_token = login_token, new_id = new_id, suppliers = suppliers, inventory_search_results = inventory_search_results, error = error)

	cursor.execute(''' SELECT SupplierID FROM Suppliers ''')
	suppliers = cursor.fetchall()

	cursor.close()

	session['login_token'] = login_token
	return render_template('Inventory.html', login_token = login_token, new_id = new_id, suppliers = suppliers, inventory_search_results = inventory_search_results, error = error)


@app.route('/inventory/mod/<login_token>', methods = ['GET', 'POST'])
def Inventory_mod(login_token):
	#LOGIN TOKEN VALIDATION
	login_token = session.get('login_token')
	if login_token == '':
		session['login_token'] = login_token
		return redirect(f'http://localhost:5000/')

	new_id = ''.join(secrets.choice(string.digits) for i in range(8))
	inventory_search_results = []
	error = 'none'

	# creating a connection cursor
	cursor = mysql.connection.cursor()

	cursor.execute(''' SELECT SupplierID FROM Suppliers ''')
	suppliers = cursor.fetchall()

	# button pressed value
	button_pressed = request.form['itemmodifyconfirm']

	if button_pressed == 'itemaddconfirm':
		try:
			# user entry
			item_add_image = request.files['itemaddimage']
			item_add_id = request.form.get('itemaddid', type = int)
			item_add_name = request.form['itemaddname']
			item_add_stock = request.form['itemaddstock']
			item_add_unitsaleprice = request.form['itemaddunitsaleprice']
			item_add_expiry = request.form['itemaddexpiry']
			item_add_supplier = request.form['itemaddsupplier']
			emp_id = session.get('emp_id')
		
		except Exception as e:
			error = 'missing or invalid input/s'
			print(e)

			cursor.close()

			return render_template('Inventory.html', login_token = login_token, new_id = new_id, suppliers = suppliers, inventory_search_results = inventory_search_results, error = error)

		# check if user entries are empty
		if item_add_id == '' or item_add_name == '' or item_add_stock == '' or item_add_unitsaleprice == '' or item_add_expiry == '' or item_add_supplier == '':
			error = 'missing input/s'

			cursor.close()
			
			return render_template('Inventory.html', login_token = login_token, new_id = new_id, suppliers = suppliers, inventory_search_results = inventory_search_results, error = error)
		
		else:
			pass

		# exception handling for item image save
		try:	
			# adding image to static directory
			item_add_image.save(os.path.join('static/item-images', secure_filename(item_add_image.filename)))

			# renaming file to entered id
			os.rename(f'static/item-images/{secure_filename(item_add_image.filename)}', f'static/item-images/{str(item_add_id)}.jpg')

		except FileNotFoundError:
			pass

		# exception handling for item add
		try:
			cursor.execute(''' INSERT INTO Inventory(ProductID, ProductName, Quantity, UnitSalePrice, ExpiryDate, SupplierID) VALUES(%s, %s, %s, %s, %s, %s) ''', (item_add_id, item_add_name, item_add_stock, item_add_unitsaleprice, item_add_expiry, item_add_supplier))
			mysql.connection.commit()

			cursor.execute(''' INSERT INTO EmployeeInventory VALUES(%s, %s)''', (emp_id, item_add_id))
			mysql.connection.commit()

			try:
				item_add_barcode = EAN8(str(item_add_id), writer = ImageWriter())
				item_add_barcode.save(f'static/item-barcodes/{item_add_id}')
			except Exception as e:
				print(e)
				pass

			error = 'modification successful'

		except Exception as e:
			error = 'modification unsuccessful'
			print(e)

	elif 'delete' in button_pressed:
		# user entry
		item_modify_delete_id = request.form['itemmodifyconfirm']
		item_modify_delete_id_new = item_modify_delete_id[6:]

		try:
			# delete item image
			os.remove(f'static/item-images/{item_modify_delete_id_new}.jpg')
			
			# delete item barcode
			os.remove(f'static/item-barcodes/{item_modify_delete_id_new}.png')
		except Exception:
			pass

		# exception handling for item delete
		try:
			cursor.execute(''' SET FOREIGN_KEY_CHECKS = 0 ''')

			# inventory database query delete item
			cursor.execute(''' DELETE FROM EmployeeInventory WHERE ProductID = %s ''', (item_modify_delete_id_new,))
			mysql.connection.commit()

			# inventory database query delete item
			cursor.execute(''' DELETE FROM Inventory WHERE ProductID = %s ''', (item_modify_delete_id_new,))
			mysql.connection.commit()

			cursor.execute(''' SET FOREIGN_KEY_CHECKS = 1 ''')

			error = 'modification successful'

		except Exception as e:
			error = 'modification unsuccessful'
			print(e)

	elif 'recordbuy' in button_pressed:
		# user entry
		item_recordbuy_id = request.form['itemmodifyconfirm']
		item_recordbuy_id_new = item_recordbuy_id[9:]
		item_recordbuy_stockbought = request.form.get('itemmodifynewstockbought' + item_recordbuy_id_new, type = int)

		try:
			# inventory database query update values
			cursor.execute(''' UPDATE Inventory SET Quantity = Quantity + %s WHERE ProductID = %s ''', (item_recordbuy_stockbought, item_recordbuy_id_new))
			mysql.connection.commit()

			error = 'modification successful'

		except Exception:
			error = 'modification unsuccessful'

	elif 'recordstocklost' in button_pressed:
		# user entry
		recordloststock_id = request.form['itemmodifyconfirm']
		recordloststock_id_new = recordloststock_id[15:]
		stock_lost = request.form.get('stocklost' + recordloststock_id_new, type = int)

		try:
			# inventory database query update values
			cursor.execute(''' UPDATE Inventory SET Quantity = Quantity - %s WHERE ProductID = %s ''', (stock_lost, recordloststock_id_new))
			mysql.connection.commit()

			error = 'modification successful'
		
		except Exception as e:
			error = 'modification unsuccessful'
			print(e)

	else:
		# user entry
		item_modify_id = request.form['itemmodifyconfirm']
		item_modify_name = request.form['itemmodifyname' + str(item_modify_id)]
		item_modify_unitsaleprice = request.form['itemmodifyunitsaleprice' + str(item_modify_id)]
		item_modify_expiry = request.form['itemmodifyexpiry' + str(item_modify_id)]
		item_modify_supplier = request.form['itemmodifysupplier' + str(item_modify_id)]

		try:
			# inventory database query update values
			cursor.execute(''' UPDATE Inventory SET ProductName = %s, UnitSalePrice = %s, ExpiryDate = %s, SupplierID = %s WHERE ProductID = %s ''', (item_modify_name, item_modify_unitsaleprice, item_modify_expiry, item_modify_supplier, item_modify_id))
			mysql.connection.commit()

			error = 'modification successful'

		except Exception as e:
			error = 'modification unsuccessful'
			print(e)

	cursor.close()
	
	return render_template('Inventory.html', login_token = login_token, new_id = new_id, suppliers = suppliers, inventory_search_results = inventory_search_results, error = error)


@app.route('/settings/<login_token>')
def Settings(login_token):
	#LOGIN TOKEN VALIDATION
	login_token = session.get('login_token')
	if login_token == '':
		session['login_token'] = login_token
		return redirect(f'http://localhost:5000/')

	closingtime_file_read = open('bin/ClosingTime.bin', 'rb')
	current_closingtime = closingtime_file_read.read().decode()
	closingtime_file_read.close()

	sales_tax_file = open('bin/SalesTax.bin', 'rb')
	sales_tax = float(sales_tax_file.read().decode())
	sales_tax_file.close()

	refund_valid_limit_file = open('bin/RefundValidLimit.bin', 'rb')
	refund_valid_limit = refund_valid_limit_file.read().decode()
	refund_valid_limit_file.close()

	shop_address_file = open('bin/ShopAddress.bin', 'rb')
	shop_address = shop_address_file.read().decode()
	shop_address_file.close()

	shop_contact_file = open('bin/ShopContact.bin', 'rb')
	shop_contact = shop_contact_file.read().decode()
	shop_contact_file.close()

	error = 'none'

	session['current_closingtime'] = current_closingtime
	session['refund_valid_limit'] = refund_valid_limit
	session['shop_address'] = shop_address
	session['shop_contact'] = shop_contact
	session['sales_tax'] = sales_tax
	session['login_token'] = login_token
	session.modified = True

	return render_template('Settings.html', login_token = login_token, error = error, shop_contact = shop_contact, shop_address = shop_address, refund_valid_limit = refund_valid_limit, sales_tax = sales_tax, current_closingtime = current_closingtime)


@app.route('/settings/<login_token>', methods = ['GET', 'POST'])
def Settings_post(login_token):
	current_closingtime = session.get('current_closingtime')
	refund_valid_limit = session.get('refund_valid_limit')
	accounts_data = session.get('accounts_data')
	shop_address = session.get('shop_address')
	shop_contact = session.get('shop_contact')
	shop_name = session.get('shop_name')
	sales_tax = session.get('sales_tax')
	button_pressed = request.form['button']
	error = 'none'

	if button_pressed == 'changeclosingtime':
		try:
			try:
				closing_time = request.form['closingtime']
			except Exception:
				error = 'missing or invalid input/s'

				return render_template('Settings.html', login_token = login_token, error = error, shop_name = shop_name, shop_contact = shop_contact, shop_address = shop_address, refund_valid_limit = refund_valid_limit, sales_tax = sales_tax, current_closingtime = current_closingtime)

			closingtime_file_write = open('bin/ClosingTime.bin', 'wb+')
			closingtime_file_write.write(closing_time.encode())
			closingtime_file_write.close()

			current_time = datetime.strptime(str(datetime.now().time()), '%H:%M:%S.%f')

			# closing time string to datetime object
			closing_time_obj_dt = datetime.strptime(closing_time, '%H:%M:%S')

			if closing_time_obj_dt > current_time:
				closing_time_obj_td = closing_time_obj_dt - current_time

			else:
				closing_time_obj_td = current_time - closing_time_obj_dt

			# calculating total number of seconds to wait
			interval = closing_time_obj_td.total_seconds()

			# converting interval seconds to hours
			interval_display = timedelta(seconds = interval)

			print(f'TIME TILL CLOSING: {interval_display}')

			error = 'modification successful'

		except Exception:
			error = 'modification unsuccessful'

		return render_template('Settings.html', login_token = login_token, error = error, shop_name = shop_name, shop_contact = shop_contact, shop_address = shop_address, refund_valid_limit = refund_valid_limit, sales_tax = sales_tax, current_closingtime = current_closingtime)

	# changing sales tax value
	elif button_pressed == 'changesalestax':
		try:
			try:
				sales_tax_new = request.form['salestax']
			except Exception:
				error = 'missing or invalid input/s'

				return render_template('Settings.html', login_token = login_token, error = error, shop_name = shop_name, shop_contact = shop_contact, shop_address = shop_address, refund_valid_limit = refund_valid_limit, sales_tax = sales_tax, current_closingtime = current_closingtime)

			# updating sales tax value
			sales_tax_file = open('bin/SalesTax.bin', 'wb+')
			sales_tax_file.write(sales_tax_new.encode())
			sales_tax_file.close()

			error = 'modification successful'
		
		except Exception:
			error = 'modification unsuccessful'

		return render_template('Settings.html', login_token = login_token, error = error, shop_name = shop_name, shop_contact = shop_contact, shop_address = shop_address, refund_valid_limit = refund_valid_limit, sales_tax = sales_tax, current_closingtime = current_closingtime)

	# change refund validity limit
	elif button_pressed == 'changerefundvalidlimit':
		try:
			try:
				refund_valid_limit_new = request.form['refundvalidlimit']
			except Exception:
				error = 'missing or invalid input/s'

				return render_template('Settings.html', login_token = login_token, error = error, shop_name = shop_name, shop_contact = shop_contact, shop_address = shop_address, refund_valid_limit = refund_valid_limit, sales_tax = sales_tax, current_closingtime = current_closingtime)

			refund_valid_limit_file = open('bin/RefundValidLimit.bin', 'wb+')
			refund_valid_limit_file.write(refund_valid_limit_new.encode())
			refund_valid_limit_file.close()

			error = 'modification successful'
		except Exception:
			error = 'modification unsuccessful'
		
		return render_template('Settings.html', login_token = login_token, error = error, shop_name = shop_name, shop_contact = shop_contact, shop_address = shop_address, refund_valid_limit = refund_valid_limit, sales_tax = sales_tax, current_closingtime = current_closingtime)

	# change shop address details
	elif button_pressed == 'changeshopaddress':
		try:
			try:
				shop_address_new = request.form['shopaddress']
			except Exception:
				error = 'missing or invalid input/s'

				return render_template('Settings.html', login_token = login_token, error = error, shop_name = shop_name, shop_contact = shop_contact, shop_address = shop_address, refund_valid_limit = refund_valid_limit, sales_tax = sales_tax, current_closingtime = current_closingtime)

			shop_address_file = open('bin/ShopAddress.bin', 'wb+')
			shop_address_file.write(shop_address_new.encode())
			shop_address_file.close()

			error = 'modification successful'
		except Exception:
			error = 'modification unsuccessful'

		return render_template('Settings.html', login_token = login_token, error = error, shop_name = shop_name, shop_contact = shop_contact, shop_address = shop_address, refund_valid_limit = refund_valid_limit, sales_tax = sales_tax, current_closingtime = current_closingtime)

	# change shop contact details
	elif button_pressed == 'changeshopcontact':
		try:
			try:
				shop_contact_new = request.form['shopcontact']
			except Exception:
				error = 'missing or invalid input/s'

				return render_template('Settings.html', login_token = login_token, error = error, shop_name = shop_name, shop_contact = shop_contact, shop_address = shop_address, refund_valid_limit = refund_valid_limit, sales_tax = sales_tax, current_closingtime = current_closingtime)

			shop_contact_file = open('bin/ShopContact.bin', 'wb+')
			shop_contact_file.write(shop_contact_new.encode())
			shop_contact_file.close()

			error = 'modification successful'
		except Exception:
			error = 'modification unsuccessful'
		
		return render_template('Settings.html', login_token = login_token, error = error, shop_name = shop_name, shop_contact = shop_contact, shop_address = shop_address, refund_valid_limit = refund_valid_limit, sales_tax = sales_tax, current_closingtime = current_closingtime)

	# factory reset databases
	elif button_pressed == 'cleardatabases':
		# creating a connection cursor
		cursor = mysql.connection.cursor()

		cursor.execute(''' SET FOREIGN_KEY_CHECKS = 0 ''')

		# employeeInventory database query reset
		cursor.execute(''' DELETE FROM EmployeeInventory ''')

		# cartInventory database query reset
		cursor.execute(''' DELETE FROM CartInventory ''')

		# inventory database query reset
		cursor.execute(''' DELETE FROM Inventory ''')

		# cart database query reset
		cursor.execute(''' DELETE FROM Cart ''')

		# suppliers database query reset
		cursor.execute(''' DELETE FROM Suppliers ''')

		# customers database query reset
		cursor.execute(''' DELETE FROM Customers ''')
		
		mysql.connection.commit()

		cursor.execute(''' SET FOREIGN_KEY_CHECKS = 1 ''')

		# database connection closing
		cursor.close()


		error  = 'databases cleared' 

		return render_template('Settings.html', login_token = login_token, error = error, shop_name = shop_name, shop_contact = shop_contact, shop_address = shop_address, refund_valid_limit = refund_valid_limit, sales_tax = sales_tax, current_closingtime = current_closingtime)

	elif button_pressed == 'clearreceipts':
		try:
			for f in os.listdir('receipts'):
				os.remove(os.path.join('receipts', f))

			error = 'receipts cleared'
		except Exception:
			error = 'receipts not cleared'

		return render_template('Settings.html', login_token = login_token, error = error, shop_name = shop_name, shop_contact = shop_contact, shop_address = shop_address, refund_valid_limit = refund_valid_limit, sales_tax = sales_tax, current_closingtime = current_closingtime)

	# delete all financial summaries
	elif button_pressed == 'clearfinancialsummaries':
		try:
			for f in os.listdir('financial-summaries'):
				os.remove(os.path.join('financial-summaries', f))

			error = 'financial summaries cleared'
		except Exception:
			error = 'financial summaries not cleared'

		return render_template('Settings.html', login_token = login_token, error = error, shop_name = shop_name, shop_contact = shop_contact, shop_address = shop_address, refund_valid_limit = refund_valid_limit, sales_tax = sales_tax, current_closingtime = current_closingtime)

	# delete all holding tokens
	elif button_pressed == 'clearholdingtokens':
		try:
			for f in os.listdir('holding-tokens'):
				os.remove(os.path.join('holding-tokens', f))

			error = 'holding tokens cleared'
		except Exception:
			error = 'holding tokens not cleared'

		return render_template('Settings.html', login_token = login_token, error = error, shop_name = shop_name, shop_contact = shop_contact, shop_address = shop_address, refund_valid_limit = refund_valid_limit, sales_tax = sales_tax, current_closingtime = current_closingtime)

	elif button_pressed == 'generatetestreceipt':
		height_num = 80
		current_date = str(datetime.now().date())
		refund_valid_limit_file = open('bin/RefundValidLimit.bin', 'rb')
		refund_valid_limit = refund_valid_limit_file.read().decode()
		refund_valid_limit_file.close()
		sales_tax_file = open('bin/SalesTax.bin', 'rb')
		sales_tax = sales_tax_file.read().decode()
		sales_tax_file.close()

		try:
			receipt_barcode = Code128(str(cart_id), writer = ImageWriter())
			receipt_barcode.save(f'static/receipt-barcodes/test')
		except Exception:
			pass

		shop_address_file = open('bin/ShopAddress.bin', 'rb')
		shop_address = shop_address_file.read().decode()
		shop_address_file.close()
		shop_contact_file = open('bin/ShopContact.bin', 'rb')
		shop_contact = shop_contact_file.read().decode()
		shop_contact_file.close()
		itemids_receipt_display = [1, 2, 3, 4, 5]
		itemnames_receipt_display = ["name1", "name2", "name3", "name4" , "name5"]
		itemquantities_receipt_display = [2, 2, 2, 2, 2]
		itemtotalsaleprices_receipt_display = [100.0, 100.0, 100.0, 100.0, 100.0]
		height = 220 + (len(itemids_receipt_display) * 20)

		canvas = Canvas(f'receipts/test.pdf')
		canvas.setPageSize((226.771653543, height))
		canvas.setFillColor(HexColor('#1A1A1A'))
		canvas.setFont('Helvetica', 11)
		canvas.drawString(5, height - 15, 'Medicare')
		receipt_barcode_image = f'static/receipt-barcodes/test.png'
		canvas.drawImage(receipt_barcode_image, 144, height - 49, height = 48, width = 88)	
		canvas.setFont('Helvetica', 9)
		canvas.drawString(5, height - 25, f'test | {current_date}')
		canvas.setFont('Helvetica', 5)
		canvas.drawString(5, height - 35, f'Address: {shop_address}')
		canvas.drawString(5, height - 45, f'Contact: {shop_contact}')
		canvas.drawString(0, height - 55, '-----------------------------------------------------------------------------------------------------------------------------------------')
		canvas.drawString(10, height - 60, 'item id | name')
		canvas.setFont('Helvetica', 5)
		canvas.drawString(111, height - 60, 'quantity')
		canvas.drawString(189, height - 60, 'price')
		canvas.drawString(0, height - 65, '-----------------------------------------------------------------------------------------------------------------------------------------')

		for i in range(0, len(itemids_receipt_display)):
			canvas.drawString(10, height - (height_num - 10), f'{itemids_receipt_display[i]}')
			canvas.setFont('Helvetica', 5)
			canvas.drawString(10, height - (height_num - 5), f'{itemnames_receipt_display[i]}')
			canvas.drawString(120, height - (height_num - 10), f'{itemquantities_receipt_display[i]}')
			canvas.drawString(185, height - (height_num - 10), f'{itemtotalsaleprices_receipt_display[i]}Rs')
			height_num += 20

		canvas.setFont('Helvetica', 6)
		canvas.drawString(0, 120, '-----------------------------------------------------------------------------------------------------------------------------------------')
		canvas.drawString(70, 110, f'sub total')
		canvas.drawString(180, 110, f'xxxxxxRs')
		canvas.drawString(170, 100, '-------------------------------')
		canvas.drawString(70, 90, f'total discount')
		canvas.drawString(180, 90, f'xxx%Rs')
		canvas.drawString(170, 80, '--------------------------------')
		canvas.drawString(70, 70, f'final total + {sales_tax}% sales tax')
		canvas.drawString(180, 70, f'xxxxxxRs')
		canvas.drawString(170, 60, '--------------------------------')
		canvas.drawString(70, 50, f'amount paid')
		canvas.drawString(180, 50, f'xxxxxxRs')
		canvas.drawString(170, 40, '--------------------------------')
		canvas.drawString(5, 30, f'# of items: xxxxxx')
		canvas.drawString(70, 30, f'change')
		canvas.drawString(180, 30, f'xxxxxxRs')
		canvas.drawString(0, 20, '-----------------------------------------------------------------------------------------------------------------------------------------')
		canvas.drawString(5, 12, 'THANKYOU FOR SHOPPING WITH US')
		canvas.drawString(5, 5, '12345678')
		canvas.setFont('Helvetica', 5)
		canvas.drawString(123, 5, f'valid for refund within {refund_valid_limit} days after purchase')

		canvas.save()

		compiled_app_path = pathlib.Path(__file__).parent.resolve()

		os.startfile(f'{compiled_app_path}\\receipts\\test.pdf')
		
	else:
		pass

	return render_template('Settings.html', login_token = login_token, error = error, shop_contact = shop_contact, shop_address = shop_address, refund_valid_limit = refund_valid_limit, sales_tax = sales_tax, current_closingtime = current_closingtime)

def Open_browser():
	# open browser tab
	webbrowser.open(f'http://localhost:5000/')

if __name__ == '__main__':
	Timer(0.1, Open_browser).start()
	app.run(host = 'localhost', port = 5000, debug = False)