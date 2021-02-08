import json

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.http import JsonResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.apps import apps

from .models import User


def index(request):
    return render(request, 'network/index.html')


def login_view(request):
    if request.method == 'POST':

        # Attempt to sign user in
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)

        # Check if authentication successful
        if user is not None:
            login(request, user)
            return HttpResponseRedirect(reverse('index'))
        else:
            return render(request, 'network/login.html', {
                'message': 'Invalid username and/or password.'
            })
    else:
        return render(request, 'network/login.html')


def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse('index'))


def register(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']

        # Ensure password matches confirmation
        password = request.POST['password']
        confirmation = request.POST['confirmation']
        if password != confirmation:
            return render(request, 'network/register.html', {
                'message': 'Passwords must match.'
            })

        # Attempt to create new user
        try:
            user = User.objects.create_user(username, email, password)
            user.save()
        except IntegrityError:
            return render(request, 'network/register.html', {
                'message': 'Username already taken.'
            })
        login(request, user)
        return HttpResponseRedirect(reverse('index'))
    else:
        return render(request, 'network/register.html')


# API METHODS

def search(request):

    if request.method != 'POST':
        return JsonResponse({
            'error': f'Search must be POST - {request.method} not supported'
        })

    query = json.loads(request.body)

    model_name = query.get('model', '')
    try:
        model = apps.get_model('network', model_name)
    except (LookupError, ValueError):
        return JsonResponse({
            'error': f'Model of name {model_name} does not exist'
        }, status=400)

    # TODO: filters
    values = model.objects.all()

    # sort values by field in either asc or desc order
    order = query.get('order')
    if order:

        # get field name from order string
        order_field = order
        if order_field.startswith('-'):
            order_field = order_field[1:]

        # ensure we're using a valid field
        if order_field in [f.name for f in model._meta.fields]:
            values = values.order_by(order)
        else:
            return JsonResponse({
                'error': f'Cannot order by {order} - not a valid field'
            }, status=400)

    fields = query.get('fields', '')
    if fields != '*':
        fields = fields.split(',')
    json_values = [v.serialize(fields, request.user) for v in values]
    return JsonResponse(json_values, safe=False)


@login_required
def create(request):

    if request.method != 'POST':
        return JsonResponse({
            'error': f'Create method must be POST - got {request.method}'
        }, status=400)

    data = json.loads(request.body)
    model_name = data.get('model')
    try:
        Model = apps.get_model('network', model_name)
    except LookupError:
        return JsonResponse({
            'error': f'Model of name {model_name} does not exist'
        }, status=400)

    model = Model.create_from_post(user=request.user, **data)
    if model:
        model.save()
        return JsonResponse(model.serialize('*', request.user), status=200)
    else:
        return JsonResponse({
            # TODO: more informative response
            'error': f'Failed to create model'
        }, status=400)
