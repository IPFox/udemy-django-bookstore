from django.shortcuts import render, redirect, get_object_or_404
from django.conf.urls import url
from .models import Book, BookOrder, Cart, Review
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.utils import timezone
from django.http import JsonResponse
import paypalrestsdk
import stripe
from django.conf import settings
from .forms import ReviewForm


def index(request):
    return render(request, 'template.html')


def store(request):
    book = Book.objects.all()
    context = {
        'books': book,
    }
    return render(request, 'base.html', context)


def book_details(request, book_id):
    # book = Book.objects.get(pk=book_id)
    book = get_object_or_404(Book, id=book_id)
    context = {
        'book': book,
    }

    if request.user.is_authenticated():
        if request.method == "POST":
            form = ReviewForm(request.POST)
            if form.is_valid():
                new_review = Review.objects.create(
                    user=request.user,
                    book=context['book'],
                    text=form.cleaned_data.get('text')
                )
                new_review.save()
        else:
            if Review.objects.filter(user=request.user, book=context['book']).count() == 0:
                form = ReviewForm()
                context['form'] = form
        context['reviews'] = book.review_set.all()
    return render(request, 'store/detail.html', context)


# Shopping cart views


def add_to_cart(request, book_id):
    if request.user.is_authenticated():
        try:
            book = Book.objects.get(pk=book_id)
        except ObjectDoesNotExist:
            pass
        else:
            try:
                cart = Cart.objects.get(user=request.user, active=True)
            except ObjectDoesNotExist:
                cart = Cart.objects.create(user=request.user)
                cart.save()
            cart.add_to_cart(book_id)
        return redirect('cart')
    else:
        return redirect('index')


def remove_from_cart(request, book_id):
    if request.user.is_authenticated():
        try:
            book = Book.objects.get(pk=book_id)
        except ObjectDoesNotExist:
            pass
        else:
            cart = Cart.objects.get(user=request.user, active=True)
            cart.save()
            cart.remove_from_cart(book_id)
        return redirect('cart')
    else:
        return redirect('index')


def cart(request):
    if request.user.is_authenticated():
        cart = Cart.objects.filter(user=request.user, active=True)
        orders = BookOrder.objects.filter(cart=cart)
        total = 0
        count = 0
        for order in orders:
            total += (order.book.price * order.quantity)
            count += order.quantity
        context = {
            'cart': orders,
            'total': total,
            'count': count,
        }
        return render(request, 'store/cart.html', context)
    else:
        return redirect('index')

# Paypal & Stripe views


def checkout(request, processor):
    if request.user.is_authenticated():
        cart = Cart.objects.filter(user=request.user.id, active=True)
        orders = BookOrder.objects.filter(cart=cart)
        if processor == "paypal":
            redirect_url = checkout_paypal(request, cart, orders)
            return redirect(redirect_url)
        elif processor == "stripe":
            token = request.POST['stripeToken']
            status = checkout_stripe(cart, orders, token)
            if status:
                return redirect(reverse('process_order', args=['stripe']))
            else:
                return redirect('order_error', context={"message": "There was a problem processing your payment."})
    else:
        return redirect('index')


def checkout_paypal(request, cart, orders):
    # FIXME: Paypal account pending, otherwise should work.
    if request.user.is_authenticated():
        items = []
        total = 0
        for order in orders:
            total += (order.book.price + order.quantity)
            book = order.book
            item = {
                'name': book.title,
                'sku': book.id,
                'price': str(book.price),
                'currency': 'USD',
                'quantity': order.quantity
            }
            items.append(item)
        paypalrestsdk.configure(
            {
                "mode": "sandbox",
                "client_id": "*paste client id from restsdk add on*",
                "client_secret": "*paste secret key from restsdk add on*",
            })
        payment = paypalrestsdk.Payment(
            {
                "intent": "sale",
                "payer": {
                    "payment_method": "paypal"},
                "redirect_urls": {
                    "return_url": "http://localhost:8080/store/process/paypal",
                    "cancel_url": "http://localhost:8080/store"},
                "transactions": [{
                    "item_list": {
                        "items": items},
                    "amount": {
                        "total": str(total),
                        "currency": "USD"},
                    "description": "Mystery Books Order. "
                }]})
        if payment.create():
            cart_instance = cart.get()
            cart_instance.payment_id = payment.id
            cart_instance.save()
            for link in payment.links:
                if link.method == "REDIRECT":
                    redirect_url = str(link.href)
                    return redirect_url
                else:
                    return reverse('store/order_error')
        else:
            return redirect('index')


def checkout_stripe(cart, orders, token):
    # DONE: below secret needs to be read from the settings secret
    # FIXME: Stripe is not working, maybe issue with the account
    stripe.api_key = settings.STRIPE_API_KEY
    total = 0
    for order in orders:
        total += (order.book.price * order.quantity)
    status = True
    try:
        charge = stripe.Charge.create(
            amount=int(total * 100),
            currency="USD",
            source=token,
            metadata={
                'order_id': cart.get().id}
        )
        cart_instance = cart.get()
        cart_instance.payment_id = charge.id
        cart_instance.save()
    except stripe.error.CardError:
        status = False
    return status


def order_error(request):
    if request.user.is_authenticated():
        return render(request, 'store/order_error.html')
    else:
        return redirect('index')


def process_order(request, processor):
    if request.user.is_authenticated():
        if processor == "paypal":
            payment_id = request.GET.get('paymentId')
            cart = Cart.objects.filter(payment_id=payment_id)
            orders = BookOrder.objects.filter(cart=cart)
            total = 0
            for order in orders:
                total += (order.book.price * order.quantity)
                context = {
                    'cart': orders,
                    'total': total,
                }
            return render(request, 'store/process_order.html', context)
        elif processor == "stripe":
            return JsonResponse({'redirect_url': reverse('complete_order', args=['stripe'])})
    else:
        return redirect('index')


def complete_order(request, processor):
    if request.user.is_authenticated():
        cart = Cart.objects.get(user=request.user.id, active=True)
        if processor == "paypal":
            payment = paypalrestsdk.Payment.find(cart.payment_id)
            if payment.execute({"payer_id": payment.payer.payer_info.payer_id}):
                message = "Success! Your order has been completed, and is being processed. Payment id: %s" % \
                          (payment.id)
                cart.active = False
                cart.order_date = timezone.now()
                cart.save()
            else:
                message = "There was a problem with the transaction. Error: %s" % (payment.error.message)
            context = {
                'message': message,
            }
            return render(request, 'store/order_complete.html', context)
        elif processor == "stripe":
            cart.active = False
            cart.order_date = timezone.now()
            cart.save()
            message = "Success! Your order has been completed, and is being processed. Payment id: %s" % \
                      (cart.payment.id)
            context = {
                'message': message,
            }
            return render(request, 'store/order_complete.html', context)
    else:
        return redirect('index')
