FROM python:3.9

WORKDIR /app

COPY backend/requirements.txt ./

RUN pip3 install -r requirements.txt --no-cache-dir

COPY backend/ ./

CMD ["gunicorn", "foodgram.wsgi:application", "--bind", "0:8000"]
