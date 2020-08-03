import datetime


class MongoField:
    @property
    def is_required(self):
        return self._is_required

    def __init__(self, **kwargs):
        self._is_required = False
        if kwargs.get('required'):
            self._is_required = True

    def cast_field(self, value):
        raise NotImplementedError


class MongoIntField(MongoField):
    def cast_field(self, value):
        return int(value)


class MongoFloatField(MongoField):
    def cast_field(self, value):
        return float(value)


class MongoStrField(MongoField):
    def cast_field(self, value):
        return str(value)


class MongoDateTimeField(MongoField):
    def cast_field(self, value):
        if isinstance(value, datetime.datetime):
            return value
        else:
            raise ValueError(
                f'MongoDateTimeField can not cast value - {value} '
                f'of type {type(value)}, allow only datetime type'
            )


class MongoModel:
    _data = {}

    def __new__(cls, *args, **kwargs):
        model_fields = []
        cls._data = {}
        for attr in dir(cls):
            if isinstance(getattr(cls, attr), MongoField):
                model_fields.append(attr)

        for field in model_fields:
            cls._data[field] = None
        return super().__new__(cls)

    def __init__(self, init_data=None):
        self._data = self._data.copy()
        init_data = init_data or {}
        for key, value in init_data.items():
            setattr(self, key, value)

    def __getattribute__(self, item):
        if item == '_data':
            return object.__getattribute__(self, item)
        if item.startswith('_attr__'):
            attr = item.split('_attr__')[-1]
            return object.__getattribute__(self, attr)
        data = self._data
        if item in data:
            return data[item]
        else:
            return object.__getattribute__(self, item)

    def __setattr__(self, key, value):
        if key == '_data':
            return object.__setattr__(self, key, value)
        if key not in self._data:
            raise AttributeError(f'{key} - attribute not found in model {self.__class__}')
        field_obj = getattr(self, f'_attr__{key}')
        self._data[key] = field_obj.cast_field(value)

    def get_data(self):
        return self._data

    def save(self, collection):
        for key, value in self._data.items():
            field = getattr(self, f'_attr__{key}')
            if field.is_required and value is None:
                raise AttributeError(f'Field {key} - is required')

        collection.insert_one(self._data)


class BaseClubModel(MongoModel):
    club_id = MongoStrField(required=True)
    club_link = MongoStrField()
    posts_count = MongoIntField()
    subscribers_count = MongoIntField()
    club_img = MongoStrField()
    club_display_name = MongoStrField()
    datetime = MongoDateTimeField()


class BasePostModel(MongoModel):
    club_id = MongoStrField(required=True)
    club_link = MongoStrField()
    content = MongoStrField()

    comments_count = MongoIntField()
    shares_count = MongoIntField()
    likes_count = MongoIntField()

    datetime = MongoDateTimeField()
    parse_datetime = MongoDateTimeField(required=True)


class FacebookPageData(BaseClubModel):
    page_likes = MongoIntField()
    posts_likes = MongoIntField()
    comments_count = MongoIntField()
    shares_count = MongoIntField()


class FacebookPostData(BasePostModel):
    post_id = MongoStrField()
    post_img = MongoStrField()
