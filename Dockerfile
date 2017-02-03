FROM tiangolo/uwsgi-nginx
MAINTAINER ubiq <Segmentation-fault@yandex.ua>

COPY ./adpt.wsgi ./
COPY ./top.tpl ./
COPY ./uwsgi.ini ./
COPY ./futaba.py ./futaba.py
COPY ./futabathread.py ./futabathread.py
COPY ./futababoard.py ./futababoard.py

RUN pip install bottle \
    && pip install beautifulsoup4 \
    && rm main.py \
    && ln -s futaba.py main.py

EXPOSE 80
WORKDIR /app
CMD ["/usr/bin/supervisord"]
