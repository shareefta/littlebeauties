from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Sum
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.utils import timezone
from .models import Order, OrderProduct, Payment, ShippingAddress
from carts.models import CartItem
from store.models import Product
import datetime
from datetime import date
from django.contrib import messages
import uuid
from accounts.models import Address
from paypal.standard.forms import PayPalPaymentsForm
from django.urls import reverse
from accounts.forms import AddressForm
from carts.models import Coupons, UserCoupons
from django.http import FileResponse
import io
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib import colors, styles
from reportlab.lib.pagesizes import letter, A5
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet


# Create your views here.

@login_required(login_url='login_user')
def add_address_checkout(request):
    if request.method == 'POST':
        form = AddressForm(request.POST)
        if form.is_valid():
            # Get the current user
            current_user = request.user

            # Extract data from the form
            full_name = form.cleaned_data['full_name']
            phone_number = form.cleaned_data['phone_number']
            address_line_1 = form.cleaned_data['address_line_1']
            address_line_2 = form.cleaned_data['address_line_2']
            city = form.cleaned_data['city']
            state = form.cleaned_data['state']
            country = form.cleaned_data['country']
            zipcode = form.cleaned_data['zipcode']

            # Create and save the address with the current user
            address = Address.objects.create(
                user=current_user,
                full_name=full_name,
                phone_number=phone_number,
                address_line_1=address_line_1,
                address_line_2=address_line_2,
                city=city,
                state=state,
                country=country,
                zipcode=zipcode
            )

            messages.success(request, 'Address Added Successfully.')
            return redirect('checkout')
    else:
        form = AddressForm()

    context = {
        'form': form
    }
    return render(request, 'orders/add-address-checkout.html', context)


def place_order(request, quantity=0, sub_total=0):
    current_user = request.user
    cart_items = CartItem.objects.filter(user=current_user)
    cart_count = cart_items.count()
    wallet = current_user.wallet
    if cart_count <= 0:
        return redirect('store')

    user_addresses = Address.objects.filter(user=current_user)
    if not user_addresses:
        messages.error(request, "Please add at least one address before placing an order.")
        return redirect('orders:add_address_checkout')

    product_discount = 0
    for cart_item in cart_items:
        if cart_item.product.offer_percentage > 0:
            discount_price = (cart_item.product.offer_percentage * cart_item.product.price) / 100
            cart_item.product.offer_price = cart_item.product.price - discount_price
            sub_total += (cart_item.product.offer_price * cart_item.quantity)
            quantity += cart_item.quantity
            product_discount += discount_price * cart_item.quantity
        else:
            sub_total += (cart_item.product.price * cart_item.quantity)
            quantity += cart_item.quantity

    tax = (2 * sub_total) / 100
    grand_total = sub_total + tax

    order_address = None

    if request.method == 'POST':

        order_address_id = request.POST.get('selected_address', None)

        data = Order()
        data.user = current_user
        data.order_total = grand_total
        data.tax = tax
        data.ip = request.META.get('REMOTE_ADDR')
        data.save()

        if order_address_id:
            # Retrieve the address associated with the order
            order_address = Address.objects.get(id=order_address_id)
            data.address = order_address
            data.save()

        # #Generate Order Number:
        yr = int(date.today().strftime('%Y'))
        mt = int(date.today().strftime('%m'))
        dt = int(date.today().strftime('%d'))
        d = date(yr, mt, dt)
        current_date = d.strftime("%Y%m%d")
        order_number = current_date + str(data.id)
        data.order_number = order_number
        data.save()

        order = Order.objects.get(user=current_user, is_ordered=False, order_number=order_number)

        coupons = Coupons.objects.all()
        current_time = timezone.localtime(timezone.now())
        valid_coupons = [coupon for coupon in coupons if coupon.valid_from <= current_time <= coupon.valid_to]

        coupon_id = 0
        coupon_amount = 0
        code = ''

        for coupon in valid_coupons:
            if coupon.is_listed:
                if order.order_total >= coupon.minimum_amount and not coupon.is_used_by_user(request.user):
                    if coupon.discount > coupon_amount:
                        coupon_amount = coupon.discount
                        code = coupon.coupon_code
                        coupon_id = coupon.id

        context = {
            'order_address': order_address,
            'order': order,
            'cart_items': cart_items,
            'tax': tax,
            'sub_total': sub_total,
            'grand_total': grand_total,
            'product_discount': product_discount,
            'order_id': order.id,
            'wallet': wallet,
            'coupon_amount': coupon_amount,
            'code': code,
            'coupon_id': coupon_id,
        }
        return render(request, 'orders/place-order.html', context)
    else:
        return HttpResponse('Error!')

def apply_coupon(request, order_id, coupon_id):
    order = get_object_or_404(Order, id=order_id)
    coupon = get_object_or_404(Coupons, id=coupon_id)
    user = request.user
    updated_total = order.order_total - float(coupon.discount)
    order.order_total = updated_total
    order.coupon_discount = coupon.discount
    order.save()

    used_coupons = UserCoupons(user=request.user, coupon=coupon, is_used=True)
    used_coupons.save()
    coupon.user = user
    coupon.is_active = False
    coupon.save()

    cart_items = CartItem.objects.filter(user=user)
    wallet = user.wallet

    sub_total = 0
    product_discount = 0
    for cart_item in cart_items:
        if cart_item.product.offer_percentage > 0:
            discount_price = (cart_item.product.offer_percentage * cart_item.product.price) / 100
            cart_item.product.offer_price = cart_item.product.price - discount_price
            sub_total += (cart_item.product.offer_price * cart_item.quantity)
            product_discount += discount_price * cart_item.quantity
        else:
            sub_total += (cart_item.product.price * cart_item.quantity)

    context = {
        'order': order,
        'order_address': order.address,
        'cart_items': cart_items,
        'tax': order.tax,
        'sub_total': sub_total,
        'total': order.order_total + coupon.discount,
        'grand_total': order.order_total,
        'product_discount': product_discount,
        'order_id': order.id,
        'wallet': wallet,
        'coupon_discount': coupon.discount,
        'total_discount': product_discount + coupon.discount,
    }

    return render(request, 'orders/place-order.html', context)

def make_payments(request, order_id):
    current_user = request.user

    # Retrieve the order using the given order_id and user
    order = get_object_or_404(Order, id=order_id, user=current_user, is_ordered=False)

    if request.method == 'POST':
        if order and order.status == 'Pending':
            payment_method = request.POST.get('paymentMethod')

            # Perform different actions based on the selected payment method
            if payment_method == 'Wallet':
                # If payment method is Wallet, update the order status
                user = current_user
                if user.wallet >= order.order_total:
                    user.wallet -= order.order_total
                    user.save()

                    order.status = 'Order Confirmed'
                    order.is_ordered = True
                    order.save()

                    # Create a new Payment instance with a unique payment_id
                    payment_id = uuid.uuid4().hex
                    payment = Payment.objects.create(
                        user=current_user,
                        payment_id=payment_id,
                        amount_paid=order.order_total,
                        status='Completed'
                    )

                    order.payment = payment
                    order.save()

                    # Move cart item to OrderProduct Table:
                    cart_items = CartItem.objects.filter(user=request.user)

                    for item in cart_items:
                        if item.product.offer_percentage > 0:
                            orderproduct = OrderProduct()
                            orderproduct.order_id = order.id
                            orderproduct.payment = payment
                            orderproduct.user_id = request.user.id
                            orderproduct.product_id = item.product_id
                            orderproduct.quantity = item.quantity
                            orderproduct.tax = order.tax
                            orderproduct.ordered = True
                            discount_price = (item.product.offer_percentage * item.product.price) / 100
                            orderproduct.product_price = item.product.price - discount_price
                            orderproduct.product_discount = discount_price * item.quantity
                            orderproduct.save()
                        else:
                            orderproduct = OrderProduct()
                            orderproduct.order_id = order.id
                            orderproduct.payment = payment
                            orderproduct.user_id = request.user.id
                            orderproduct.product_id = item.product_id
                            orderproduct.quantity = item.quantity
                            orderproduct.product_price = item.product.price
                            orderproduct.tax = order.tax
                            orderproduct.ordered = True
                            orderproduct.save()

                        cart_item = CartItem.objects.get(id=item.id)
                        product_variant = cart_item.variant.all()
                        orderproduct = OrderProduct.objects.get(id=orderproduct.id)
                        orderproduct.variant.set(product_variant)
                        orderproduct.save()

                        # Reduce the stock of product sold:
                        product = Product.objects.get(id=item.product_id)
                        product.stock -= item.quantity
                        product.save()

                    # Clear Cart:
                    CartItem.objects.filter(user=request.user).delete()

                    messages.success(request, 'Order placed successfully.')
                    return redirect('orders:order_confirmation', order_id=order.id)
                else:
                    messages.error(request, 'Wallet balance insufficient')
                    return redirect('checkout')

            elif payment_method == 'CashOnDelivery':
                # If payment method is Cash On Delivery, update the order status
                order.status = 'Order Confirmed'
                order.is_ordered = True
                order.save()

                # Create a new Payment instance with a unique payment_id
                payment_id = uuid.uuid4().hex
                payment = Payment.objects.create(
                    user=current_user,
                    payment_id=payment_id,
                    amount_paid=order.order_total,
                    status='Completed'
                )

                order.payment = payment
                order.save()

                # Move cart item to OrderProduct Table:
                cart_items = CartItem.objects.filter(user=request.user)

                for item in cart_items:
                    if item.product.offer_percentage > 0:
                        orderproduct = OrderProduct()
                        orderproduct.order_id = order.id
                        orderproduct.payment = payment
                        orderproduct.user_id = request.user.id
                        orderproduct.product_id = item.product_id
                        orderproduct.quantity = item.quantity
                        orderproduct.tax = order.tax
                        orderproduct.ordered = True
                        discount_price = (item.product.offer_percentage * item.product.price) / 100
                        orderproduct.product_price = item.product.price - discount_price
                        orderproduct.product_discount = discount_price * item.quantity
                        orderproduct.save()
                    else:
                        orderproduct = OrderProduct()
                        orderproduct.order_id = order.id
                        orderproduct.payment = payment
                        orderproduct.user_id = request.user.id
                        orderproduct.product_id = item.product_id
                        orderproduct.quantity = item.quantity
                        orderproduct.product_price = item.product.price
                        orderproduct.tax = order.tax
                        orderproduct.ordered = True
                        orderproduct.save()

                    cart_item = CartItem.objects.get(id=item.id)
                    product_variant = cart_item.variant.all()
                    orderproduct = OrderProduct.objects.get(id=orderproduct.id)
                    orderproduct.variant.set(product_variant)
                    orderproduct.save()

                    # Reduce the stock of product sold:
                    product = Product.objects.get(id=item.product_id)
                    product.stock -= item.quantity
                    product.save()

                # Clear Cart:
                CartItem.objects.filter(user=request.user).delete()

                messages.success(request, 'Order placed successfully.')
                return redirect('orders:order_confirmation', order_id=order.id)

            elif payment_method == 'PayPal':
                host = request.get_host()

                paypal_checkout = {
                    'business': settings.PAYPAL_RECEIVER_EMAIL,
                    'amount': order.order_total,
                    'invoice': uuid.uuid4(),
                    'currency_code': 'USD',
                    'notify_url': f"http://{host}{reverse('paypal-ipn')}",
                    'return_url': f"http://{host}{reverse('orders:paypal_payment_success', kwargs={'order_id': order.id})}",
                    'cancel_url': f"http://{host}{reverse('orders:paypal_payment_failed', kwargs={'order_id': order.id})}",
                }

                paypal_payment = PayPalPaymentsForm(initial=paypal_checkout)
                context = {
                    'order': order,
                    'paypal': paypal_payment
                }

                return render(request, 'paypal/paypal-checkout.html', context)

            else:
                # Handle other payment methods or show an error message
                messages.error(request, 'Select a valid payment method.')
        else:
            # Handle the case where the order does not exist or is not in a suitable state for payment
            messages.error(request, 'Invalid order or order not in a valid state for payment.')
            return redirect('home')

    return render(request, 'orders/place-order.html', {'order': order})


def paypal_payment_success(request, order_id):
    current_user = request.user

    # Retrieve the order using the given order_id and user
    order = get_object_or_404(Order, id=order_id, user=current_user, is_ordered=False)

    # update the order status
    order.status = 'Order Confirmed'
    order.is_ordered = True
    order.save()

    # Create a new Payment instance with a unique payment_id
    payment_id = uuid.uuid4().hex
    payment = Payment.objects.create(
        user=current_user,
        payment_id=payment_id,
        amount_paid=order.order_total,
        status='Completed'
    )

    order.payment = payment
    order.save()

    # Move cart item to OrderProduct Table:
    cart_items = CartItem.objects.filter(user=request.user)

    for item in cart_items:
        if item.product.offer_percentage > 0:
            orderproduct = OrderProduct()
            orderproduct.order_id = order.id
            orderproduct.payment = payment
            orderproduct.user_id = request.user.id
            orderproduct.product_id = item.product_id
            orderproduct.quantity = item.quantity
            # orderproduct.tax = order.tax
            orderproduct.ordered = True
            discount_price = (item.product.offer_percentage * item.product.price) / 100
            orderproduct.product_price = item.product.price - discount_price
            orderproduct.product_discount = discount_price * item.quantity
            orderproduct.save()
        else:
            orderproduct = OrderProduct()
            orderproduct.order_id = order.id
            orderproduct.payment = payment
            orderproduct.user_id = request.user.id
            orderproduct.product_id = item.product_id
            orderproduct.quantity = item.quantity
            orderproduct.product_price = item.product.price
            # orderproduct.tax = order.tax
            orderproduct.ordered = True
            orderproduct.save()

        cart_item = CartItem.objects.get(id=item.id)
        product_variant = cart_item.variant.all()
        orderproduct = OrderProduct.objects.get(id=orderproduct.id)
        orderproduct.variant.set(product_variant)
        orderproduct.save()

        # Reduce the stock of product sold:
        product = Product.objects.get(id=item.product_id)
        product.stock -= item.quantity
        product.save()

    # Clear Cart:
    CartItem.objects.filter(user=request.user).delete()

    messages.success(request, 'Order placed successfully.')
    return redirect('orders:order_confirmation', order_id=order.id)

    # return render(request, 'paypal/paypal-payment-success.html', {'order': order})


def order_confirmation(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    #Transferring Address to Shipping Address Table:
    shipping_address = ShippingAddress()
    shipping_address.user = request.user
    shipping_address.order = order
    shipping_address.full_name = order.address.full_name
    shipping_address.phone_number = order.address.phone_number
    shipping_address.address_line_1 = order.address.address_line_1
    shipping_address.address_line_2 = order.address.address_line_2
    shipping_address.city = order.address.city
    shipping_address.state = order.address.state
    shipping_address.country = order.address.country
    shipping_address.zipcode = order.address.zipcode
    shipping_address.save()

    return render(request, 'orders/order-confirmation.html', {'order': order})


def paypal_payment_failed(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'paypal/paypal-payment-failed.html', {'order': order})


@login_required(login_url='login_admin')
def order_detail_admin(request, order_id):
    order_detail = OrderProduct.objects.filter(order__order_number=order_id)
    order = Order.objects.get(order_number=order_id)
    shipping_address = ShippingAddress.objects.get(order__order_number=order_id)

    total_product = []
    subtotal = 0
    total_product_discount = 0

    for item in order_detail:
        product_total = item.product_price * item.quantity
        subtotal += product_total
        total_product.append({'item': item, 'total': product_total})
        total_product_discount += item.product_discount

    context = {
        'order_detail': total_product,
        'order': order,
        'subtotal': subtotal,
        'total': subtotal + order.tax,
        'total_product_discount': total_product_discount,
        'total_discount': order.coupon_discount + total_product_discount,
        'shipping_address': shipping_address,
    }
    return render(request, 'admin/order-detail-admin.html', context)


from datetime import datetime, timedelta

@login_required(login_url='login_admin')
def sales_report(request):
    # Calculate the start and end of the current day
    current_date = datetime.now()
    start_of_day = current_date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + timedelta(days=1) - timedelta(microseconds=1)

    # Filter OrderProduct objects for the current day
    # orders = Order.objects.filter(created_at__range=[start_of_day, end_of_day]).order_by('-created_at')
    orders = ShippingAddress.objects.filter(order__created_at__range=[start_of_day, end_of_day]) \
        .order_by('-order__created_at')

    # Calculate the sum of order amount for the current day
    total_order_amount = orders.aggregate(total_order_amount=Sum('order__order_total'))[
                             'total_order_amount'] or 0

    # Calculate the sum of amount_paid for the current day
    total_amount_paid = orders.aggregate(total_amount_paid=Sum('order__payment__amount_paid'))['total_amount_paid'] or 0

    context = {
        'current_date': current_date,
        'orders': orders,
        'total_order_amount': total_order_amount,
        'total_amount_paid': total_amount_paid,
    }

    return render(request, 'sales-report/daily-sales-report.html', context)


@login_required(login_url='login_admin')
def weekly_sales_report(request):
    # Calculate the start and end of the current week
    current_date = datetime.now()
    start_of_week = current_date - timedelta(days=current_date.weekday())
    end_of_week = start_of_week + timedelta(days=6)

    # Filter OrderProduct objects for the week
    orders = ShippingAddress.objects.filter(order__created_at__range=[start_of_week, end_of_week]) \
        .order_by('-order__created_at')

    # Calculate the sum of order amount for the current week
    total_order_amount = orders.aggregate(total_order_amount=Sum('order__order_total'))[
                             'total_order_amount'] or 0

    # Calculate the sum of amount_paid for the current week
    total_amount_paid = orders.aggregate(total_amount_paid=Sum('order__payment__amount_paid'))['total_amount_paid'] or 0

    context = {
        'start_of_week': start_of_week,
        'end_of_week': end_of_week,
        'orders': orders,
        'total_order_amount': total_order_amount,
        'total_amount_paid': total_amount_paid,
    }

    return render(request, 'sales-report/weekly-sales-report.html', context)


@login_required(login_url='login_admin')
def monthly_sales_report(request):
    # Calculate the start and end of the current month
    current_date = datetime.now()
    start_of_month = current_date.replace(day=1)
    end_of_month = start_of_month + timedelta(days=32)
    end_of_month = end_of_month.replace(day=1) - timedelta(days=1)

    # Filter OrderProduct objects for the current month
    orders = ShippingAddress.objects.filter(order__created_at__range=[start_of_month, end_of_month]) \
        .order_by('-order__created_at')

    # Calculate the sum of order amount for the current month
    total_order_amount = orders.aggregate(total_order_amount=Sum('order__order_total'))[
                             'total_order_amount'] or 0

    # Calculate the sum of amount_paid for the current month
    total_amount_paid = orders.aggregate(total_amount_paid=Sum('order__payment__amount_paid'))['total_amount_paid'] or 0

    context = {
        'start_of_month': start_of_month,
        'end_of_month': end_of_month,
        'orders': orders,
        'total_order_amount': total_order_amount,
        'total_amount_paid': total_amount_paid,
    }

    return render(request, 'sales-report/monthly-sales-report.html', context)


@login_required(login_url='login_admin')
def yearly_sales_report(request):
    # Calculate the start and end of the current year
    current_date = datetime.now()
    start_of_year = current_date.replace(month=1, day=1)
    end_of_year = start_of_year.replace(year=start_of_year.year + 1) - timedelta(days=1)

    # Filter OrderProduct objects for the current year
    orders = ShippingAddress.objects.filter(order__created_at__range=[start_of_year, end_of_year]) \
        .order_by('-order__created_at')

    # Calculate the sum of order amount for the current year
    total_order_amount = orders.aggregate(total_order_amount=Sum('order__order_total'))[
                             'total_order_amount'] or 0

    # Calculate the sum of amount_paid for the current year
    total_amount_paid = orders.aggregate(total_amount_paid=Sum('order__payment__amount_paid'))['total_amount_paid'] or 0

    context = {
        'start_of_year': start_of_year,
        'end_of_year': end_of_year,
        'orders': orders,
        'total_order_amount': total_order_amount,
        'total_amount_paid': total_amount_paid,
    }

    return render(request, 'sales-report/yearly-sales-report.html', context)

@login_required(login_url='login_admin')
def custom_sales_report(request):
    if request.method == "POST":
        starting_date = request.POST['starting_date']
        ending_date = request.POST['ending_date']
        starting_date = datetime.strptime(starting_date, '%Y-%m-%d')
        ending_date = datetime.strptime(ending_date, '%Y-%m-%d')
        ending_date1 = ending_date
        ending_date = ending_date + timedelta(days=1)

        if starting_date <= ending_date:
            # Fetch orders within the selected date range:
            orders = ShippingAddress.objects.filter(order__created_at__range=[starting_date, ending_date]) \
                .order_by('-order__created_at')

            # Calculate the sum of order amount for selected range
            total_order_amount = orders.aggregate(total_order_amount=Sum('order__order_total'))[
                                     'total_order_amount'] or 0

            # Calculate the sum of amount_paid for selected range
            total_amount_paid = orders.aggregate(total_amount_paid=Sum('order__payment__amount_paid'))[
                                    'total_amount_paid'] or 0

            # Pass the dates to the PDF view using reverse
            pdf_url = reverse('orders:custom_report_pdf',
                              kwargs={'starting_date': starting_date.date(), 'ending_date': ending_date1.date()})
            context = {
                'starting_date': starting_date,
                'ending_date': ending_date1,
                'orders': orders,
                'total_order_amount': total_order_amount,
                'total_amount_paid': total_amount_paid,
                'pdf_url': pdf_url,
            }
            return render(request, 'sales-report/custom-sales-report.html', context)
    return render(request, 'sales-report/date-custom-report.html')

@login_required(login_url='login_admin')
def sales_report_pdf(request):
    buf = io.BytesIO()

    current_date = datetime.now()
    start_of_day = current_date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + timedelta(days=1) - timedelta(microseconds=1)

    # Filter ShippingAddress objects for the current day
    shipping_addresses = ShippingAddress.objects.filter(order__created_at__range=[start_of_day, end_of_day]) \
        .order_by('-order__created_at')

    # Create SimpleDocTemplate with title
    title = f"Sales Report - {current_date}"
    doc = SimpleDocTemplate(buf, pagesize=A5, rightMargin=15, leftMargin=15, topMargin=15, bottomMargin=15, title=title)

    # create a table
    data = []

    # Add table headers
    table_headers = ['Sl. No.', 'Order Number', 'Name', 'Amount Paid', 'Status']
    data.append(table_headers)

    # Add order information with serial numbers
    for index, shipping_address in enumerate(shipping_addresses, start=1):
        order = shipping_address.order
        order_info = [
            str(index),
            str(order.order_number),
            shipping_address.full_name[:26],  # Adjust width as needed
            f"{round(float(order.payment.amount_paid), 2)}",
            order.status
        ]
        data.append(order_info)

    # Create the table
    table = Table(data, colWidths=[.5 * inch, 1 * inch, 1.5 * inch, 1 * inch, 1.2 * inch], rowHeights=0.4 * inch)

    # Add style to the table
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ALIGN', (3, 1), (3, -1), 'RIGHT'),  # Align 'Amount Paid' column to the right
    ])
    table.setStyle(style)

    # Build the PDF
    doc.build([table])

    # Return the response
    buf.seek(0)
    return FileResponse(buf, as_attachment=True, filename='Daily Sales Report.pdf')

@login_required(login_url='login_admin')
def weekly_report_pdf(request):
    buf = io.BytesIO()
    # create SimpleDocTemplate
    doc = SimpleDocTemplate(buf, pagesize=A5, rightMargin=15, leftMargin=15, topMargin=15, bottomMargin=15)
    # create a table
    data = []

    current_date = datetime.now()
    start_of_week = current_date - timedelta(days=current_date.weekday())
    end_of_week = start_of_week + timedelta(days=6)

    # Filter ShippingAddress objects for the week
    shipping_addresses = ShippingAddress.objects.filter(order__created_at__range=[start_of_week, end_of_week]) \
        .order_by('-order__created_at')

    # Add table headers
    table_headers = ['Sl. No.', 'Order Number', 'Name', 'Amount Paid', 'Status']
    data.append(table_headers)

    # Add order information with serial numbers
    for index, shipping_address in enumerate(shipping_addresses, start=1):
        order = shipping_address.order
        order_info = [
            str(index),
            str(order.order_number),
            shipping_address.full_name[:26],  # Adjust width as needed
            f"{round(float(order.payment.amount_paid), 2)}",
            order.status
        ]
        data.append(order_info)

    # Create the table
    table = Table(data, colWidths=[.5 * inch, 1 * inch, 1.5 * inch, 1 * inch, 1.2 * inch], rowHeights=0.4 * inch)

    # Add style to the table
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ALIGN', (3, 1), (3, -1), 'RIGHT'),  # Align 'Amount Paid' column to the right
    ])
    table.setStyle(style)

    # Build the PDF
    doc.build([table])

    # Return the response
    buf.seek(0)
    return FileResponse(buf, as_attachment=True, filename='Weekly Sales Report.pdf')

@login_required(login_url='login_admin')
def monthly_report_pdf(request):
    buf = io.BytesIO()
    # create SimpleDocTemplate
    doc = SimpleDocTemplate(buf, pagesize=A5, rightMargin=15, leftMargin=15, topMargin=15, bottomMargin=15)
    # create a table
    data = []

    # Calculate the start and end of the month
    current_date = datetime.now()
    start_of_month = current_date.replace(month=1, day=1)
    end_of_month = start_of_month.replace(year=start_of_month.year + 1) - timedelta(days=1)

    # Filter ShippingAddress objects for the month
    shipping_addresses = ShippingAddress.objects.filter(order__created_at__range=[start_of_month, end_of_month]) \
        .order_by('-order__created_at')

    # Add table headers
    table_headers = ['Sl. No.', 'Order Number', 'Name', 'Amount Paid', 'Status']
    data.append(table_headers)

    # Add order information with serial numbers
    for index, shipping_address in enumerate(shipping_addresses, start=1):
        order = shipping_address.order
        order_info = [
            str(index),
            str(order.order_number),
            shipping_address.full_name[:26],  # Adjust width as needed
            f"{round(float(order.payment.amount_paid), 2)}",
            order.status
        ]
        data.append(order_info)

    # Create the table
    table = Table(data, colWidths=[.5 * inch, 1 * inch, 1.5 * inch, 1 * inch, 1.2 * inch], rowHeights=0.4 * inch)

    # Add style to the table
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ALIGN', (3, 1), (3, -1), 'RIGHT'),  # Align 'Amount Paid' column to the right
    ])
    table.setStyle(style)

    # Build the PDF
    doc.build([table])

    # Return the response
    buf.seek(0)
    return FileResponse(buf, as_attachment=True, filename='Monthly Sales Report.pdf')

@login_required(login_url='login_admin')
def yearly_report_pdf(request):
    buf = io.BytesIO()
    # create SimpleDocTemplate
    doc = SimpleDocTemplate(buf, pagesize=A5, rightMargin=15, leftMargin=15, topMargin=15, bottomMargin=15)
    # create a table
    data = []

    # Calculate the start and end of the year
    current_date = datetime.now()
    start_of_year = current_date.replace(month=1, day=1)
    end_of_year = start_of_year.replace(year=start_of_year.year + 1) - timedelta(days=1)

    # Filter ShippingAddress objects for the year
    shipping_addresses = ShippingAddress.objects.filter(order__created_at__range=[start_of_year, end_of_year]) \
        .order_by('-order__created_at')

    # Add table headers
    table_headers = ['Sl. No.', 'Order Number', 'Name', 'Amount Paid', 'Status']
    data.append(table_headers)

    # Add order information with serial numbers
    for index, shipping_address in enumerate(shipping_addresses, start=1):
        order = shipping_address.order
        order_info = [
            str(index),
            str(order.order_number),
            shipping_address.full_name[:26],  # Adjust width as needed
            f"{round(float(order.payment.amount_paid), 2)}",
            order.status
        ]
        data.append(order_info)

    # Create the table
    table = Table(data, colWidths=[.5 * inch, 1 * inch, 1.5 * inch, 1 * inch, 1.2 * inch], rowHeights=0.4 * inch)

    # Add style to the table
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ALIGN', (3, 1), (3, -1), 'RIGHT'),  # Align 'Amount Paid' column to the right
    ])
    table.setStyle(style)

    # Build the PDF
    doc.build([table])

    # Return the response
    buf.seek(0)
    return FileResponse(buf, as_attachment=True, filename='Yearly Sales Report.pdf')

@login_required(login_url='login_admin')
def custom_report_pdf(request, starting_date, ending_date):
    starting_date = datetime.strptime(starting_date, '%Y-%m-%d')
    ending_date = datetime.strptime(ending_date, '%Y-%m-%d') + timedelta(days=1)

    # Filter ShippingAddress objects for the selected range
    shipping_addresses = ShippingAddress.objects.filter(order__created_at__range=[starting_date, ending_date]) \
        .order_by('-order__created_at')


    buf = io.BytesIO()
    # create SimpleDocTemplate
    doc = SimpleDocTemplate(buf, pagesize=A5, rightMargin=15, leftMargin=15, topMargin=15, bottomMargin=15)
    # create a table
    data = []

    # # Main Heading
    # main_heading = f"Sales Report ({starting_date.strftime('%Y-%m-%d')} to {ending_date.strftime('%Y-%m-%d')})"
    # main_heading_style = styles.getSampleStyleSheet()['Heading1']
    # main_heading_paragraph = Paragraph(main_heading, main_heading_style)
    # data.append([main_heading_paragraph])

    # Add table headers
    table_headers = ['Sl. No.', 'Order Number', 'Name', 'Amount Paid', 'Status']
    data.append(table_headers)

    # Add order information with serial numbers
    for index, shipping_address in enumerate(shipping_addresses, start=1):
        order = shipping_address.order
        order_info = [
            str(index),
            str(order.order_number),
            shipping_address.full_name[:26],  # Adjust width as needed
            f"{round(float(order.payment.amount_paid), 2)}",
            order.status
        ]
        data.append(order_info)

    # Create the table
    table = Table(data, colWidths=[.5 * inch, 1 * inch, 1.5 * inch, 1 * inch, 1.2 * inch], rowHeights=0.4 * inch)

    # Add style to the table
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ALIGN', (3, 1), (3, -1), 'RIGHT'),  # Align 'Amount Paid' column to the right
    ])
    table.setStyle(style)

    # Build the PDF
    doc.build([table])
    # elements = [main_heading_paragraph, table]  # Include main heading and table in elements
    # doc.build(elements)

    # Return the response
    buf.seek(0)
    return FileResponse(buf, as_attachment=True, filename='Custom Sales Report.pdf')

