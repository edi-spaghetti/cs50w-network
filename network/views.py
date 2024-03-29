import json

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.http import JsonResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.apps import apps
from django.core.paginator import Paginator

from .models import User
from .utils import sanitize_update_request

MAX_RECORDS = 10


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

def whoami(request):

    if request.method != 'POST':
        return JsonResponse({
            'error': f'Search must be POST - {request.method} not supported'
        }, status=400)

    try:
        return JsonResponse(
            request.user.serialize(True, request.user),
            status=200
        )
    except AttributeError:
        # current user is anonymous, return dict with id
        # to keep data structure in React consistent
        return JsonResponse({'id': None}, status=200)


def search(request):

    if request.method != 'POST':
        return JsonResponse({
            'error': f'Search must be POST - {request.method} not supported'
        }, status=400)

    query = json.loads(request.body)
    # TODO: logging!!!
    print(f'Got query: {query}')

    model_name = query.get('model')
    try:
        model = apps.get_model('network', model_name)
    except (LookupError, ValueError, AttributeError):
        print('model error')
        return JsonResponse({
            'error': f'Model of name {model_name} does not exist'
        }, status=400)

    # create filters (if any)
    filters = query.get('filters')
    try:
        filters, excludes = model.parse_filters(filters)
    except ValueError as v:
        print('filters error')
        return JsonResponse({
            'error': f'Could not parse filters: {v}'
        }, status=400)

    # get values based on filters
    values = model.objects.filter(**filters).exclude(**excludes)

    # sort values by field in either asc or desc order
    order = query.get('order')
    try:
        values = model.order_by(order, values)
    except ValueError as v:
        print('order error')
        return JsonResponse({
            'error': f'Cannot order by {order}: {v}'
        }, status=400)

    limit = query.get('limit') or MAX_RECORDS
    try:
        limit = int(limit)
        assert 0 < limit < MAX_RECORDS + 1
    except (ValueError, TypeError, AssertionError):
        print('limit error')
        return JsonResponse({
            'error': f'Limit must be positive integer '
            f'between 1 and {MAX_RECORDS}- got {type(limit)} {limit}'
        }, status=400)

    # paginate values by limit
    paginator = Paginator(values, limit)
    page = query.get('page') or 1
    try:
        page = int(page)
        assert 0 < page < paginator.num_pages + 1
    except (ValueError, TypeError, AssertionError):
        print('page error')
        return JsonResponse({
            'error': f'Page must be a positive integer '
            f'up to {paginator.num_pages} - got {type(page)} {page}'
        }, status=400)
    current_page = paginator.page(page)
    values = current_page.object_list

    fields = query.get('fields')
    try:
        json_values = [v.serialize(fields, request.user) for v in values]
        # if limit is 1, return data as dict not array
        if limit == 1:
            json_values = json_values[0]
    except ValueError as v:
        print('serialize error')
        return JsonResponse({
            'error': f'Invalid requested fields: {v}'
        }, status=400)
    else:
        payload = {
            'data': json_values,
            'pageNum': page,
            'pageCount': paginator.num_pages,
            'hasPrevious': current_page.has_previous(),
            'hasNext': current_page.has_next(),
        }
        print(f'Returning results: {payload}')
        return JsonResponse(payload, safe=False)


@login_required
def update(request):
    if request.method != 'POST':
        return JsonResponse({
            'error': f'Update must be POST - {request.method} not supported'
        }, status=400)

    query = json.loads(request.body)

    data = query.get('data')
    multi_option = query.get('multiOption')
    try:
        data, multi_option = sanitize_update_request(data, multi_option)
    except ValueError as v:
        return JsonResponse({
            'error': f'Error parsing update request: {v}'
        })

    for item in data:
        model_class = apps.get_model('network', item['model'])
        model_instance = model_class.objects.get(id=item['id'])
        try:
            for field, value in item.items():
                if field not in ('model', 'id'):
                    assert model_instance.has_edit_permissions(
                        field, value, request.user
                    )
        except (PermissionError, AssertionError) as p:
            return JsonResponse({
                'error': f'Unauthorised request: {p}'
            }, status=403)

    result = list()
    for item in data:
        model_class = apps.get_model('network', item['model'])
        model_instance = model_class.objects.get(id=item['id'])
        serial_value = model_instance.update(item, request.user, multi_option)
        result.append(serial_value)

    if len(result) == 1:
        result = result[0]
    return JsonResponse(result, safe=False, status=200)


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
        return JsonResponse(
            model.serialize(model.SELECT_ALL, request.user),
            status=200)
    else:
        return JsonResponse({
            # TODO: more informative response
            'error': f'Failed to create model'
        }, status=400)
