FROM joyzoursky/python-chromedriver:3.8-alpine3.10

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

ENV MUSL_LOCPATH=/usr/local/share/i18n/locales/musl
RUN \
 apk add --update cmake make musl-dev gcc gettext-dev libintl xvfb git python3-dev linux-headers && \
 cd /tmp && git clone https://gitlab.com/rilian-la-te/musl-locales.git && \
 cd /tmp/musl-locales && cmake . && make && make install

# Set the lang, you can also specify it as as environment variable through docker-compose.yml
ENV LANG=ru_RU.UTF-8 LANGUAGE=ru_RU.UTF-8 PYTHONPATH=/opt/

RUN mkdir -p /opt/selenium_parsers/

COPY requirements.txt /opt/selenium_parsers/requirements.txt
WORKDIR /opt/selenium_parsers/

RUN \
 apk add --no-cache postgresql-libs && \
 apk add --no-cache --virtual .build-deps gcc musl-dev postgresql-dev && \
 pip install --upgrade pip && \
 pip install -r requirements.txt --no-cache-dir && \
 apk --purge del .build-deps

COPY . /opt/selenium_parsers/

ADD crontab /etc/cron.d/parsers
RUN chmod 0755 /etc/cron.d/parsers && touch /var/log/cron.log
RUN /usr/bin/crontab /etc/cron.d/parsers
CMD ["./entry.sh"]
