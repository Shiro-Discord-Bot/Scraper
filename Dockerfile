FROM python:3.8-slim

ARG RELEASE=unspecified
ENV SCRAPER_RELEASE=${RELEASE}

COPY src /src
COPY requirements.txt .

RUN pip install -r requirements.txt
RUN rm requirements.txt

WORKDIR /src

CMD ["python", "./scraper.py"]