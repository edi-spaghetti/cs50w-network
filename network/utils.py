import json

from django.db.models.fields.related import RelatedField, ForeignObjectRel
from django.db.models.manager import Manager
from django.db.models.fields import IntegerField
from django.core.exceptions import FieldDoesNotExist


OPERATORS = {
    # TODO: refactor operators as class
    # op   db lookup   is_include
    'is': ('exact',    True),
    'not': ('exact',    False),
    'in': ('in',       True),
}


def convert_filter_value_by_data_type(field, value):
    """
    Converts value passed into an api filter to an appropriate data type
    for that field type. Currently only supports strings and integers.
    :param field: Django model field type
    :param value: Value to convert
    :return: Convert value
    """

    is_int = isinstance(field, IntegerField)
    is_int_like = isinstance(field, RelatedField)
    if is_int or is_int_like:
        value = int(value)

    return value


def sanitize_update_request(request, multi_option):
    # TODO: assert request is list of dicts with at least one
    #       valid key, value pair, plus model name and id
    # TODO: convert request values to appropriate type
    return request, multi_option


def field_label():
    labels = set()

    def label(func):
        labels.add(func.__name__)
        return func

    label.all = labels
    return label


class ModelExtension(object):
    """
    Extension for :class:`Model` to provide additional functionality, such as
    managing extended field types and serializing additional data types.
    """

    SELECT_ALL = True
    SERIAL_EXTENSION = '__serial'
    summary = field_label()
    contextual = field_label()
    _context = None

    def set_context(self, context):
        self._context = context

    @classmethod
    def default_fields(cls):
        """
        Names of all fields defined as subclasses of :class:`models.Field` on
        the current model.
        :rtype: set
        """
        fields = set()
        for f in cls._meta.fields:
            fields.add(f.name)

        return fields

    @classmethod
    def summary_fields(cls):
        """
        Names of all fields added to current model as properties and grouped
        under the 'summary' label.
        :rtype: set
        """
        if hasattr(cls, 'summary'):
            return cls.summary.all
        else:
            return set()

    @classmethod
    def contextual_fields(cls):
        """
        Names of all fields added to the current model as properties,
        grouped under the 'contextual' label, and reliant on class context
        to derive their value.
        :rtype: set
        """
        if hasattr(cls, 'contextual'):
            return cls.contextual.all
        else:
            return set()

    def sanitize_context(self, context):
        """Pass-through to be overloaded by subclasses"""
        return context

    @classmethod
    def sanitize_return_fields(cls, request_fields):
        """
        Convert requested fields into iterable structures for retrieving
        fields directly linked to the current model, and fields linked
        to related models. Will recursively
        :param request_fields: Fields requested to return with the query.
                               Should be a list of str (for directly linked
                               fields) and/or dict (for fields on related
                               models).
        :type request_fields: list[str, dict]
        :raises: ValueError if request fields badly formatted.
        :return: list of current model fields, and dictionary of linked field
                 mappings
        """
        fields = list()
        linked_fields = dict()

        if request_fields is cls.SELECT_ALL:
            # convert special select all token to all available fields
            fields = cls.serializable_fields()
        elif isinstance(request_fields, list):
            for field in request_fields:

                # attempt to add direct field
                if isinstance(field, str):
                    if field in cls.serializable_fields():
                        fields.append(field)
                    else:
                        raise ValueError(
                            f'{field} is not a direct field of {cls}'
                        )

                # ensure keys of dict are valid linked fields on current model
                elif isinstance(field, dict):
                    for sub_field, options in field.items():
                        try:
                            sub_field_class = cls._meta.get_field(sub_field)
                            assert isinstance(
                                sub_field_class,
                                (RelatedField, ForeignObjectRel)
                            )
                        except (FieldDoesNotExist, AssertionError):
                            raise ValueError(
                                f'{sub_field} is not a linked field of {cls}'
                            )

                        # note, we don't need to evaluate the sub request
                        # fields just yet, because they will be resolved
                        # when serialize_values recurses into linked models
                        # any errors in lower levels will be revealed later
                        linked_fields[sub_field] = options

                # exit with error for badly formed request
                else:
                    raise ValueError(
                        f'expected inner items str or dict '
                        f'- got {type(field)}'
                    )
        elif request_fields is not None:
            raise ValueError(
                f'valid types are list[str, dict] or {cls.SELECT_ALL} '
                f'- got {type(request_fields)}'
            )

        return fields, linked_fields

    @classmethod
    def parse_filters(cls, filters):
        """
        Parses incoming filters that can be used filter to models either
        positively or negatively. Filters should come in as a list of dicts in
        the following format:
            [{<field>: (<operator>, <value>)}]
            e.g. [{'id': {'is', 1}}]
        Fields will be sanitised, and must be valid for the model provided.
        Currently supported operators are:
            == -> positively filter field by value
            != -> negatively filter field by value
        Values will be converted to the appropriate data type for the field.
        Currently supported data types are:
            str (CharField)
            int (NumberField, PrimaryKey)
        :param filters:
        :return: Dictionaries arranged into a format appropriate to pass as
                 keywords to :meth:`Model.filter` and :meth:`Model.exclude`.
        :rtype: tuple[dict, dict]
        :raises: ValueError if any filter is cannot be parsed, whether through
                 invalid fields or bad value conversion.
        """

        # sanitize filters param
        filters = filters or []

        # validate filter is a list of dicts
        if not isinstance(filters, list):
            raise ValueError(f'filter must be list: got {type(filters)}')
        for i, f in enumerate(filters):
            if not isinstance(f, dict):
                raise ValueError(
                    f'Filter items must be dicts, got {type(f)} at index {i}'
                )

        filter_dict = dict()
        exclude_dict = dict()

        # TODO: support for filtering on non-db fields
        fields = cls.default_fields()

        for f in filters:
            for field, operators in f.items():
                for operator, value in operators.items():
                    if field not in fields:
                        raise ValueError(f'invalid field - {field}')
                    if operator not in OPERATORS.keys():
                        raise ValueError(f'invalid operator - {operator}')

                    lookup, is_include = OPERATORS[operator]
                    lookup_key = f'{field}__{lookup}'

                    # TODO: data type manager
                    db_field = getattr(cls, field).field
                    if lookup == 'in':
                        if not isinstance(value, list):
                            raise ValueError(
                                f'expected list - got {type(value)} {value}'
                            )
                        for i, v in enumerate(value):
                            value[i] = convert_filter_value_by_data_type(
                                db_field, v
                            )
                    else:
                        value = convert_filter_value_by_data_type(
                            db_field, value
                        )

                    # TODO: warning if duplicate filters provided
                    if is_include:
                        filter_dict[lookup_key] = value
                    else:
                        exclude_dict[lookup_key] = value

        return filter_dict, exclude_dict

    @classmethod
    def order_by(cls, field, values):

        if not field:
            return values
        if not isinstance(field, str):
            raise ValueError(f'expected str - got {type(field)}')

        if field.startswith('-'):
            field_name = field[1:]
        else:
            field_name = field

        if field_name in cls.default_fields():
            values = values.order_by(field)
        # TODO: support ordering by summary and contextual fields
        else:
            raise ValueError(f'{field_name} - not a valid field')

        return values

    @classmethod
    def serializable_fields(cls):
        fields = cls.default_fields()
        fields = fields.union(cls.summary_fields())
        fields = fields.union(cls.contextual_fields())

        return fields

    def serialize_values(self, fields):
        """
        Collects requested field value as serializable value.
        If fields are not valid, they will be returned as None.
        :param fields: List of direct (as str) and linked (as dict) fields
                       Also accepts :attr:`ModelExtension.SELECT_ALL` as
                       short-hand for all direct fields on current model.
        :type fields: list[str, dict] or :attr:`ModelExtension.SELECT_ALL`
        :raises: ValueError if sanitization fails
        :return: Json serializable dictionary of field-value pairs
        """
        # add valid fields to dict
        serial_dict = dict()

        fields, linked_fields = self.sanitize_return_fields(fields)

        for field in fields:
            value = self.serializable_value(field)
            serial_dict[field] = value

        for field, options in linked_fields.items():
            value = getattr(self, field)
            is_multi_link = hasattr(value, 'all')
            if is_multi_link:

                model = self._meta.get_field(field).related_model

                # extract values from multi-link field, if any
                if isinstance(options, dict):
                    sub_fields = options.get('fields')
                    order = options.get('order')
                # assume list of fields if no options given
                elif isinstance(options, list):
                    sub_fields = options
                    order = None
                # bail out if input recognised
                elif options == model.SELECT_ALL:
                    sub_fields = options
                    order = None
                else:
                    raise ValueError(
                        f'multi-link field expects fields as list, '
                        f'options as dict, or {model.SELECT_ALL} '
                        f'- got {type(options)}'
                    )

                # collect and serialize related models, optionally ordering
                values = value.all()
                if order:
                    values = model.order_by(order, values)
                values = [m.serialize_values(sub_fields) for m in values]

            else:
                # we can assume this is a 1-1 or 1-many relation
                # single model links can't be sorted or filtered, so we can
                # also assume the options are just the requested fields
                values = value.serialize_values(options)

            serial_dict[field] = values

        return serial_dict

    def serialize(self, fields=None, context=None):

        # set the context to the requesting user
        old_context = self._context
        context = self.sanitize_context(context)
        self.set_context(context)

        values = self.serialize_values(fields)

        # set the context back so context doesn't change between requests
        self.set_context(old_context)

        return values

    def update(self, item, context=None, multi_option=None):
        """
        TODO
        :param item:
        :param context:
        :param multi_option:
        :return:
        """

        multi_option = multi_option or {}

        return_fields = list()
        for key, value in item.items():
            if key in ('model', 'id'):
                continue
            field = getattr(self, key)
            mode = multi_option.get(key) or 'set'
            if isinstance(field, Manager):
                if mode == 'add':
                    field.add(value)
                elif mode == 'remove':
                    field.remove(value)
                elif mode == 'set':
                    field.set([value])
                else:
                    raise ValueError(
                        f'multi-option can be add, remove or set '
                        f'- got {multi_option}'
                    )
                return_fields.append({key: ['id']})
            else:
                setattr(self, key, value)
                return_fields.append(key)
        self.save()
        serial_value = self.serialize(return_fields, context)
        serial_value['id'] = item['id']
        serial_value['model'] = item['model']

        return serial_value

    def serializable_value(self, field_name):
        """
        Collects and serialises field value.
        Accepts any field type (including contextual and summary types).
        :param field_name:
        :type field_name: str
        :return: Json serializable value, if field name can be resolved,
                 otherwise None.
        """
        # NOTE: by the time self gets used, it will be multiply inheriting from
        #       :class:`Model`, so this will not throw an error.

        # first validate input params
        if not isinstance(field_name, str):
            return

        # next, pull out the field on current model
        undotted = field_name.split('.')
        base_field_name = undotted[0]

        # now collect raw value
        try:
            # attempt to get field class
            field = self._meta.get_field(base_field_name)

            # if related field, recursively query down one level
            if isinstance(field, (RelatedField, ForeignObjectRel)):
                # if no linked field provided, default to 'id'
                relation_path = undotted[1:] or ['id']
                linked_model = getattr(self, base_field_name)
                linked_field = relation_path[0]
                dotted_path = '.'.join(relation_path)
                value = {
                    linked_field: linked_model.serializable_value(dotted_path)
                }
            else:
                value = getattr(self, field.attname)

        except FieldDoesNotExist:

            original_name = base_field_name.replace(self.SERIAL_EXTENSION, '')
            if original_name in self.serializable_fields():
                value = getattr(self, base_field_name)
            else:
                return

        # verify value is json serializable
        try:
            json.dumps(value)
            return value
        # otherwise attempt to run custom serialization
        except (TypeError, OverflowError):
            try:
                return self.serializable_value(
                    f'{base_field_name}{self.SERIAL_EXTENSION}'
                )
            except AttributeError:
                return
