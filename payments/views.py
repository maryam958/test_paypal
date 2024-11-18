from django.shortcuts import render, redirect
from django.conf import settings
from .models import Payment
import mollie.api.client

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt


# Initialize Mollie API client
mollie_client = mollie.api.client.Client()
mollie_client.set_api_key(settings.MOLLIE_API_KEY)



def create_payment(request):
    if request.method == 'POST':
        amount = request.POST.get('amount')
        description = request.POST.get('description')

        try:
            # Create a payment object in Mollie
            payment = mollie_client.payments.create({
                'amount': {
                    'currency': 'EGP',  # Ensure EUR is allowed in your Mollie profile
                    'value': f'{float(amount):.2f}'
                },
                'description': description,
                'redirectUrl': request.build_absolute_uri('/payment/status/'),
                'webhookUrl': request.build_absolute_uri('/payment/webhook/'),  # Webhook URL
                'method': 'paypal',  # Ensure PayPal is enabled in Mollie
            })

            # Save the payment in your database
            Payment.objects.create(
                payment_id=payment['id'],
                amount=amount,
                description=description,
                status=payment['status']
            )

            # Redirect the user to Mollie's checkout page
            return redirect(payment.get('checkoutUrl'))

        except mollie.api.error.Error as e:
            # Handle Mollie API errors
            return render(request, 'error.html', {'message': str(e)})

    return render(request, 'create_payment.html')


def payment_status(request):
    payment_id = request.GET.get('id')
    try:
        # Fetch the payment details from Mollie
        mollie_payment = mollie_client.payments.get(payment_id)
        payment = Payment.objects.get(payment_id=payment_id)

        # Update payment status in the database
        payment.status = mollie_payment['status']
        payment.save()

        return render(request, 'payment_status.html', {'payment': payment})

    except Payment.DoesNotExist:
        return render(request, 'error.html', {'message': 'Payment not found.'})
    except mollie.api.error.Error as e:
        return render(request, 'error.html', {'message': str(e)})




@csrf_exempt  # Disable CSRF for webhook since it's an external POST request
def payment_webhook(request):
    if request.method == 'POST':
        payment_id = request.POST.get('id')  # Mollie sends the payment ID in the POST data

        try:
            # Fetch the payment details from Mollie
            mollie_payment = mollie_client.payments.get(payment_id)
            
            # Update the payment record in your database
            payment = Payment.objects.get(payment_id=payment_id)
            payment.status = mollie_payment['status']
            payment.save()

            # Perform additional actions based on payment status
            if mollie_payment['status'] == 'paid':
                # For example, mark an order as complete
                print("Payment successful!")
            elif mollie_payment['status'] == 'failed':
                print("Payment failed!")

        except Payment.DoesNotExist:
            print(f"Payment with ID {payment_id} does not exist in the database.")
        except mollie.api.error.Error as e:
            print(f"Mollie API error: {str(e)}")

    return HttpResponse(status=200)
