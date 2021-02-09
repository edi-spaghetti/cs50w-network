import json

from django.db.models import Model


def parse_filters(model, filter_):

    # validate filter is a list of strings
    if not isinstance(filter_, list):
        raise ValueError(f'Filter must be list: got {type(filter_)}')
    for i, f in enumerate(filter_):
        if not isinstance(f, str):
            raise ValueError(
                f'Filter items must be strings, got {type(f)} at index {i}'
            )

    filter_dict = dict()
    exclude_dict = dict()

    # TODO: convert api filter syntax into django filter syntax
    #       e.g. field==value -> filter_dict[field__exact] = value
    #       e.g. field!=value -> exclude_dict[field__exact] = value
    # REF: https://docs.djangoproject.com/en/dev/ref/models/querysets/#field-lookups

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
        value = Model.serializable_value(self, field_name)  # noqa
        try:
            json.dumps(value)
            return value
        except (TypeError, OverflowError):
            return self.serializable_value(f'{field_name}_serial')
