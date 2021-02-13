import re
import json

from django.db.models import Model
from django.db.models.base import ModelBase
from django.db.models.fields.related import RelatedField
from django.db.models.fields import IntegerField


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

    SELECT_ALL = '*'
    summary = field_label()
    contextual = field_label()
    _context = None

    def set_context(self, context):
        self._context = context

    @classmethod
    def default_fields(cls):
        """
        Names of all fields defined as subclasses of :class:`models.Field`
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

    def sanitize_return_fields(self, fields):
        # TODO: refactor sanitisation to expect list of strings
        # if fields is None, this will set it to a null string
        fields = fields or ''
        if fields == self.SELECT_ALL:
            # convert special select all token to all available fields
            fields = self.serializable_fields()
        else:
            fields = fields.split(',')

        return fields

    def serializable_fields(self):
        fields = self.default_fields()
        fields = fields.union(self.summary_fields())
        fields = fields.union(self.contextual_fields())

        return fields

    def serialize_values(self, fields):
        """
        Collects requested field value as serializable value.
        If fields are not valid, they will be returned as None.
        :param fields: List of fields to serialize pull values from
        :type fields: list[str]
        :return: Json serializable dictionary of field-value pairs
        """
        # add valid fields to dict
        serial_dict = dict()

        for field in fields:
            try:
                value = self.serializable_value(field)
            except AttributeError:
                value = None

            serial_dict[field] = value

        return serial_dict

    def serialize(self, fields, context=None):

        # set the context to the requesting user
        old_context = self._context
        context = self.sanitize_context(context)
        self.set_context(context)

        fields = self.sanitize_return_fields(fields)
        values = self.serialize_values(fields)

        # set the context back so context doesn't change between requests
        self.set_context(old_context)

        return values

    def serializable_value(self, field_name):
        # NOTE: by the time self gets used, it will be multiply inheriting from
        #       :class:`Model`, so this will not throw an error.
        # TODO: fix serialization of linked fields
        value = Model.serializable_value(self, field_name)  # noqa
        try:
            json.dumps(value)
            return value
        except (TypeError, OverflowError):
            return self.serializable_value(f'{field_name}_serial')
