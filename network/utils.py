import re
import json

from django.db.models import Model
from django.db.models.base import ModelBase
from django.db.models.fields.related import RelatedField, ForeignObjectRel
from django.db.models.fields import IntegerField
from django.core.exceptions import FieldDoesNotExist


OPERATORS = {
    # TODO: refactor operators as class
    # op   db lookup   is_include
    '==': ('exact',    True),
    '!=': ('exact',    False),
}


def build_filter_regex(fields):
    """
    Build and compile a regex pattern used to parse filters from api
    :param fields:
    :return:
    """
    f = '|'.join(fields)
    o = '|'.join(OPERATORS.keys())
    reg = re.compile(f'({f})\s*({o})\s*(.+)')
    return reg


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


def parse_filters(model, filters):
    """
    Parses incoming filters that can be used filter to models either
    positively or negatively. Filters should come in as a list of strings of
    format `<field> <operator> <value>` e.g. `id == 1` or `id!=1` (note,
    whitespace between terms is optional).
    Fields will be sanitised, and must be valid for the model provided.
    Currently supported operators are:
        == -> positively filter field by value
        != -> negatively filter field by value
    Values will be converted to the appropriate data type for the field.
    Currently supported data types are:
        str (CharField)
        int (NumberField, PrimaryKey)
    :type model: :class:`Model`
    :param filters:
    :return: Dictionaries arranged into a format appropriate to pass as
             keywords to :meth:`Model.filter` and :meth:`Model.exclude`.
    :rtype: tuple[dict, dict]
    :raises: ValueError if any filter is cannot be parsed, whether through
             invalid fields or bad value conversion.
    """

    # validate model is correct type
    if not isinstance(model, (ModelBase, ModelExtension)):
        raise ValueError(f'expected extended model, got {type(model)}')

    # validate filter is a list of strings
    if not isinstance(filters, list):
        raise ValueError(f'filter must be list: got {type(filters)}')
    for i, f in enumerate(filters):
        if not isinstance(f, str):
            raise ValueError(
                f'Filter items must be strings, got {type(f)} at index {i}'
            )

    filter_dict = dict()
    exclude_dict = dict()

    # TODO: support for filtering on non-db fields
    fields = model.default_fields()
    reg = build_filter_regex(fields)

    for f in filters:
        try:
            field, operator, value = reg.search(f).groups()
        except AttributeError:
            # TODO: more useful feedback on parse filter failure
            raise ValueError(f'failed to parse filter: {f}')

        lookup, is_include = OPERATORS[operator]
        lookup_key = f'{field}__{lookup}'

        # TODO: data type manager
        db_field = getattr(model, field).field
        value = convert_filter_value_by_data_type(db_field, value)

        # TODO: warning if duplicate filters provided
        if is_include:
            filter_dict[lookup_key] = value
        else:
            exclude_dict[lookup_key] = value

    return filter_dict, exclude_dict


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
                    for sub_field, sub_request_fields in field.items():
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
                        linked_fields[sub_field] = sub_request_fields

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

        for field, sub_fields in linked_fields.items():
            value = getattr(self, field)
            is_multi_link = hasattr(value, 'all')
            if is_multi_link:
                values = [m.serialize_values(sub_fields) for m in value.all()]
            else:
                # we can assume this is a 1-1 or 1-many relation
                values = value.serialize_values(sub_fields)

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
                linked_model = field.related_model()
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
